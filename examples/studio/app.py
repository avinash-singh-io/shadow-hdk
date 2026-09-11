"""The studio's server: one conversation, the record streamed to whoever is watching."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, StreamingResponse
from starlette.routing import Route

from examples.coder.session import NoProvider, a_conversation
from shadow_hdk.kernel import Allow, Event, Refuse
from shadow_hdk.kernel.contracts import dump
from shadow_hdk.runtime import Questions
from shadow_hdk.runtime.environment import Mode
from shadow_hdk.runtime.steps import Fold, as_json

PAGE = (Path(__file__).parent / "page.html").read_text(encoding="utf-8")


@dataclass
class Studio:
    """What the server holds between requests: the conversation, the record, the watchers."""

    root: Path
    mode: Mode = "workspace-write"
    want: str | None = None
    questions: Questions = field(default_factory=Questions)
    record: list[dict[str, Any]] = field(default_factory=list)
    """Every event of the run, as JSON, in order — the page catches up from here."""
    watchers: list[asyncio.Queue[dict[str, Any]]] = field(default_factory=list)
    fold: Fold = field(default_factory=Fold)
    talk: Any = None
    provider: str = ""
    busy: bool = False
    _conversation: Any = None

    # ------------------------------------------------------------------ the record

    def on_event(self, event: Event) -> None:
        line = self.keep({"kind": "event", "event": json.loads(dump(event, Event))})
        self._tell(line)
        # **One fold, the runtime's** (D46): the page could fold the events itself, and a client in
        # another language would; this one is handed the runtime's steps so the two never differ.
        self.fold.feed(event)
        for step in self.fold.closed_now:
            self._tell({"kind": "step", "step": as_json(step)})

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
        self._conversation = a_conversation(
            self.root,
            want=self.want,
            mode=self.mode,
            on_event=self.on_event,
            questions=self.questions,
        )
        self.talk = await self._conversation.__aenter__()
        self.provider = getattr(self.talk, "provider", "") or "the provider signed in here"
        asyncio.create_task(self._relay_questions())

    async def close(self) -> None:
        if self._conversation is not None:
            await self._conversation.__aexit__(None, None, None)

    async def _relay_questions(self) -> None:
        """A question the policy raises reaches the page as its own line, with the handle the page
        answers by. The `Asked` event is already on the record; this is the *pending* half."""
        while True:
            pending = await self.questions.next()
            self.note(
                "question",
                handle=pending.handle,
                run_id=pending.run_id,
                step=pending.step,
                question=pending.question,
            )

    async def say(self, text: str) -> dict[str, Any]:
        if self.busy:
            return {"error": "the provider is still on the previous turn"}
        self.busy = True
        self.note("you", text=text)
        try:
            done = await self.talk.turn(text)
        finally:
            self.busy = False
        answer = {"text": done.text, "failed": bool(done.failed), "reasoning": done.reasoning}
        self.note("agent", **answer)
        return answer

    def answer(self, handle: str, allow: bool, reason: str = "") -> bool:
        judgement = Allow() if allow else Refuse(reason or "the person said no")
        answered = self.questions.answer(handle, judgement)
        if answered:
            self.note("answered", handle=handle, allow=allow, reason=reason)
        return answered

    # ------------------------------------------------------------------ the workspace

    def files(self) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for path in sorted(self.root.rglob("*")):
            if any(part.startswith(".") for part in path.relative_to(self.root).parts):
                continue
            if path.is_file():
                found.append(
                    {"path": str(path.relative_to(self.root)), "bytes": path.stat().st_size}
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


def build_app(studio: Studio) -> Starlette:
    async def page(_request: Request) -> HTMLResponse:
        return HTMLResponse(PAGE)

    async def status(_request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "root": str(studio.root),
                "mode": studio.mode,
                "provider": studio.provider,
                "busy": studio.busy,
                "pending": [
                    {"handle": p.handle, "question": p.question, "step": p.step}
                    for p in studio.questions.pending()
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
                    if int(line.get("i", caught_up)) < caught_up:
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

    async def answer(request: Request) -> JSONResponse:
        body = await request.json()
        done = studio.answer(
            str(body.get("handle", "")), bool(body.get("allow")), str(body.get("reason", ""))
        )
        return JSONResponse({"ok": done})

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
            Route("/files", files),
            Route("/file", file),
        ]
    )


__all__ = ["NoProvider", "Studio", "build_app"]
