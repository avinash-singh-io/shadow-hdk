"""The studio's server: one conversation, the record streamed to whoever is watching."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.modes import ActRules, store_rules
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, StreamingResponse
from starlette.routing import Route

from shadow_hdk.kernel import ActRule, Event
from shadow_hdk.kernel.contracts import dump
from shadow_hdk.providers import NoProvider
from shadow_hdk.runtime import Approvals, Approve, ApproveAndAddRule, Deny
from shadow_hdk.runtime.environment import Mode
from shadow_hdk.runtime.items import Fold, as_json
from shadow_hdk.runtime.store import InMemoryStore
from shadow_hdk.serve import a_thread, modes_for

PAGE = Path(__file__).parent / "page.html"


@dataclass
class Studio:
    """What the server holds between requests: the conversation, the record, the watchers."""

    root: Path
    mode: Mode = "workspace-write"
    want: str | None = None
    approvals: Approvals = field(default_factory=Approvals)
    store: Any = None
    """Where live data lives (D66): modes, rules, skills, switches. `None` is in memory."""
    rules: ActRules = field(default_factory=ActRules)
    """The person's "approve and don't ask again" rules (D65): read by governance at the next
    judgement; written through to the store, so they outlive the process."""
    modes: Any = None
    record: list[dict[str, Any]] = field(default_factory=list)
    """Every event of the run, as JSON, in order — the page catches up from here."""
    watchers: list[asyncio.Queue[dict[str, Any]]] = field(default_factory=list)
    fold: Fold = field(default_factory=Fold)
    thread: Any = None
    provider: str = ""
    busy: bool = False
    _conversation: Any = None

    # ------------------------------------------------------------------ the record

    def on_activity(self, activity: Any) -> None:
        """What is happening (D63): a delta of thinking or text, a chunk a command printed. Live
        to whoever is watching — and **not kept on the record the page replays**, because it is
        not the record."""
        self._tell(
            {
                "kind": "delta",
                "run_id": activity.run_id,
                "step": activity.step,
                "delta": activity.kind,
                "text": activity.text,
                "i": -1,
            }
        )

    def on_event(self, event: Event) -> None:
        line = self.keep({"kind": "event", "event": json.loads(dump(event, Event))})
        self._tell(line)
        # **One fold, the runtime's** (D46): the page could fold the events itself, and a client in
        # another language would; this one is handed the runtime's steps so the two never differ.
        self.fold.feed(event)
        for item in self.fold.closed_now:
            # Kept, not only told: a page that reloads replays the record and needs the items
            # closed the way they closed — without this every part stayed "running" on reload.
            self._tell(self.keep({"kind": "item", "item": as_json(item)}))

    def _tell(self, line: dict[str, Any]) -> None:
        for queue in list(self.watchers):
            queue.put_nowait(line)

    def note(self, kind: str, **fields: Any) -> None:
        self._tell(self.keep({"kind": kind, **fields}))

    def keep(self, line: dict[str, Any]) -> dict[str, Any]:
        """Append to the record with its index, so a watcher that catches up and then follows can
        tell a replayed line from a live one and never shows one twice."""
        line["i"] = len(self.record)
        self.record.append(line)
        return line

    # ------------------------------------------------------------------ the conversation

    async def open(self) -> None:
        if self.store is None:
            self.store = InMemoryStore()
        self.rules = ActRules(sources=(store_rules(self.store),))
        self.modes = modes_for(self.store, files=self.root / ".harness" / "modes")
        self._conversation = a_thread(
            self.root,
            want=self.want,
            mode=self.mode,
            approvals=self.approvals,
            observer=_Watching(self.on_activity),
            rules=self.rules,
            store=self.store,
        )
        self.thread = await self._conversation.__aenter__()
        self.provider = self.thread.record.provider or "the provider signed in here"
        asyncio.create_task(self._relay_questions())
        asyncio.create_task(self._relay_withdrawals())

    async def close(self) -> None:
        if self._conversation is not None:
            await self._conversation.__aexit__(None, None, None)

    async def _relay_questions(self) -> None:
        """A question the policy raises reaches the page as its own line, with the handle the page
        answers by. The `Asked` event is already on the record; this is the *pending* half."""
        while True:
            pending = await self.approvals.next()
            self.note(
                "question",
                handle=pending.handle,
                run_id=pending.run_id,
                step=pending.step,
                question=pending.question,
                component=pending.component,
                inputs=pending.inputs,
                request=pending.kind,
            )

    async def _relay_withdrawals(self) -> None:
        """A question the asker stopped waiting for — the page takes its buttons away."""
        while True:
            gone = await self.approvals.next_withdrawn()
            self.note("withdrawn", handle=gone.handle)

    async def say(self, text: str) -> dict[str, Any]:
        if self.busy:
            return {"error": "the provider is still on the previous turn"}
        self.busy = True
        self.note("you", text=text)
        try:
            async for event in self.thread.turn(text):
                self.on_event(event)
        finally:
            self.busy = False
        turn = self.thread.record.turns[-1]
        usage = _usage_of_turn(self.record, turn.run_id)
        answer = {
            "text": turn.text,
            "failed": turn.outcome != "completed",
            "reasoning": "",
            "usage": usage,
        }
        self.note("agent", **answer)
        return answer

    async def mode_list(self) -> list[dict[str, str]]:
        """What the host offers, for the selector — read live from the registry (D66)."""
        if self.modes is None:
            return []
        return [
            {"id": m.id, "name": m.name, "description": m.description, "source": m.source}
            for m in await self.modes.all()
        ]

    # ------------------------------------------------------------------ live data (D66)

    async def create_mode(self, document: dict[str, Any]) -> tuple[bool, str]:
        """A mode created at runtime through the store: judged from at the next step, offered in
        the selector at the next read. Validated by the same function a file goes through."""
        from shadow_hdk.adapters.modes import mode_from_document

        try:
            made = mode_from_document(document, source="store")
        except ValueError as wrong:
            return False, str(wrong)
        await self.store.put("modes", made.id, document)
        self.note("mode_created", mode=made.id)
        return True, made.id

    async def create_rule(self, document: dict[str, Any]) -> tuple[bool, str]:
        try:
            rule = ActRule(
                component=str(document["component"]),
                inputs=dict(document.get("inputs", {}) or {}),
                decision=document.get("decision", "allow"),
                mode=str(document.get("mode", "") or ""),
                note=str(document.get("note", "") or ""),
            )
        except (KeyError, TypeError, ValueError) as wrong:
            return False, f"a rule needs a component and inputs: {wrong}"
        await self.rules.add_now(rule)
        self.note("rule_created", component=rule.component)
        return True, rule.component

    async def rule_list(self) -> list[dict[str, Any]]:
        return [json.loads(dump(r, ActRule)) for r in await self.rules.all_now()]

    @property
    def current_mode(self) -> str:
        return self.thread.record.mode if self.thread is not None else self.mode

    async def change_mode(self, mode_id: str) -> bool:
        if self.thread is None:
            return False
        try:
            changed = await self.thread.set_mode(mode_id)
        except KeyError:
            return False
        for event in changed:
            self.on_event(event)  # `ModeChanged` is on the record, between turns too (D64)
        self.note("mode", mode=mode_id)
        return True

    def answer(
        self,
        handle: str,
        allow: bool,
        reason: str = "",
        *,
        add_rule: bool = False,
        text: str | None = None,
    ) -> bool:
        """The person's answer: approve, deny, approve-and-add-rule (D65) — or, for an input
        request, their text."""
        pending = next((p for p in self.approvals.pending() if p.handle == handle), None)
        if text is not None:
            answered = self.approvals.answer(handle, text)
            if answered:
                self.note("answered", handle=handle, allow=True, reason="", text=text)
            return answered
        judgement: Any
        if allow and add_rule and pending is not None and pending.component:
            judgement = ApproveAndAddRule(_rule_for(pending.component, pending.inputs))
        else:
            judgement = Approve() if allow else Deny(reason or "the person said no")
        answered = self.approvals.answer(handle, judgement)
        if answered:
            self.note("answered", handle=handle, allow=allow, reason=reason, rule=add_rule)
        return answered

    # ------------------------------------------------------------------ the workspace

    def files(self) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for path in sorted(self.root.rglob("*")):
            parts = path.relative_to(self.root).parts
            if any(part.startswith(".") or part == "__pycache__" for part in parts):
                continue
            if path.is_file():
                stat = path.stat()
                found.append(
                    {
                        "path": str(path.relative_to(self.root)),
                        "bytes": stat.st_size,
                        "mtime": stat.st_mtime,
                    }
                )
        return found

    def read(self, relative: str) -> str | None:
        target = (self.root / relative).resolve()
        if not str(target).startswith(str(self.root.resolve())) or not target.is_file():
            return None
        try:
            return target.read_text(encoding="utf-8")[:200_000]
        except UnicodeDecodeError:
            return f"(binary, {target.stat().st_size} bytes)"


class _Watching:
    """The studio's observer: events come from the turn's own iterator; activity comes here."""

    def __init__(self, on_activity: Any) -> None:
        self._on_activity = on_activity

    async def on(self, event: Event) -> None:
        return None

    async def on_activity(self, activity: Any) -> None:
        self._on_activity(activity)


def _rule_for(component: str, inputs: Any) -> ActRule:
    """What "don't ask again" means here — the studio's vocabulary, not the harness's (principle
    8). A write or a read to a *path* is the same act whatever the content; a command is the
    exact command. Measured: a rule on every input asked again for the same file with different
    text, which is not what a person meant by the button."""
    given = inputs if isinstance(inputs, dict) else {}
    if "path" in given:
        return ActRule(component=component, inputs={"path": given["path"]})
    return ActRule(component=component, inputs=dict(given))


def _usage_of_turn(record: list[dict[str, Any]], run_id: str) -> dict[str, Any] | None:
    """The turn's cost, read off the record's `usage` events for that run."""
    for line in reversed(record):
        event = line.get("event") if line.get("kind") == "event" else None
        if event and event.get("kind") == "usage" and event.get("run_id") == run_id:
            usage: dict[str, Any] | None = event.get("usage")
            return usage
    return None


def build_app(studio: Studio) -> Starlette:
    async def page(_request: Request) -> HTMLResponse:
        # Read on each request: the page is the part of this example a person iterates on while
        # the conversation behind it stays open.
        return HTMLResponse(PAGE.read_text(encoding="utf-8"))

    async def status(_request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "root": str(studio.root),
                "mode": studio.current_mode,
                "modes": await studio.mode_list(),
                "provider": studio.provider,
                "busy": studio.busy,
                "pending": [
                    {"handle": p.handle, "question": p.question, "step": p.step}
                    for p in studio.approvals.pending()
                ],
            }
        )

    async def stream(_request: Request) -> StreamingResponse:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def lines() -> AsyncIterator[bytes]:
            # Watch first, then catch up: a line that lands between the two is in the queue and
            # not in the replayed slice, and one in both is skipped by its index.
            studio.watchers.append(queue)
            caught_up = len(studio.record)
            try:
                for line in studio.record[:caught_up]:
                    yield f"data: {json.dumps(line)}\n\n".encode()
                while True:
                    try:
                        line = await asyncio.wait_for(queue.get(), 15)
                    except TimeoutError:
                        yield b": keep-alive\n\n"
                        continue
                    if line.get("kind") != "delta" and int(line.get("i", caught_up)) < caught_up:
                        continue
                    yield f"data: {json.dumps(line)}\n\n".encode()
            finally:
                studio.watchers.remove(queue)

        return StreamingResponse(lines(), media_type="text/event-stream")

    async def say(request: Request) -> JSONResponse:
        body = await request.json()
        text = str(body.get("text", "")).strip()
        if not text:
            return JSONResponse({"error": "say something"}, status_code=400)
        asyncio.create_task(studio.say(text))
        return JSONResponse({"ok": True})

    async def set_mode(request: Request) -> JSONResponse:
        body = await request.json()
        done = await studio.change_mode(str(body.get("mode", "")))
        return JSONResponse({"ok": done})

    async def answer(request: Request) -> JSONResponse:
        body = await request.json()
        done = studio.answer(
            str(body.get("handle", "")),
            bool(body.get("allow")),
            str(body.get("reason", "")),
            add_rule=bool(body.get("add_rule")),
            text=body.get("text"),
        )
        return JSONResponse({"ok": done})

    async def create_mode(request: Request) -> JSONResponse:
        ok, said = await studio.create_mode(await request.json())
        return JSONResponse({"ok": ok, "detail": said}, status_code=200 if ok else 400)

    async def create_rule(request: Request) -> JSONResponse:
        ok, said = await studio.create_rule(await request.json())
        return JSONResponse({"ok": ok, "detail": said}, status_code=200 if ok else 400)

    async def rules(_request: Request) -> JSONResponse:
        return JSONResponse({"rules": await studio.rule_list()})

    async def files(_request: Request) -> JSONResponse:
        return JSONResponse({"files": studio.files()})

    async def file(request: Request) -> JSONResponse:
        content = studio.read(request.query_params.get("path", ""))
        if content is None:
            return JSONResponse({"error": "no such file in the workspace"}, status_code=404)
        return JSONResponse({"content": content})

    return Starlette(
        routes=[
            Route("/", page),
            Route("/status", status),
            Route("/stream", stream),
            Route("/say", say, methods=["POST"]),
            Route("/answer", answer, methods=["POST"]),
            Route("/mode", set_mode, methods=["POST"]),
            Route("/admin/modes", create_mode, methods=["POST"]),
            Route("/admin/rules", create_rule, methods=["POST"]),
            Route("/admin/rules", rules),
            Route("/files", files),
            Route("/file", file),
        ]
    )


__all__ = ["NoProvider", "Studio", "build_app"]
