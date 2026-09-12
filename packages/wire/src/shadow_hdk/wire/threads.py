"""The thread, crossed (D67): the host's controls of Phase 25 for a host in any language.

The wire's other shape (`run`/`resume`) inverts the ports — the host keeps judge, components and
sink, the runtime calls back. This shape holds the ports **runtime-side**: the process serving the
wire hands in a `ThreadHost` that composes them (the shipped adapters, a store, a provider), and
the host across the wire drives threads by method — `thread/start`, `turn/start`, and the rest —
the way a TypeScript product would. Events, items and activity cross as notifications tagged with
the thread id; the turn's record comes back as the result.

The wire package cannot import an adapter (the stands-alone rule), so the composition is not
here: `ThreadHost` is a port, and `shadow_hdk.serve` implements it.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Protocol

from shadow_hdk.kernel import EffectProfile, Event, Lease, ThreadRecord
from shadow_hdk.kernel.activity import Activity
from shadow_hdk.kernel.contracts import dump
from shadow_hdk.runtime.items import Fold, as_json
from shadow_hdk.runtime.threads import Thread
from shadow_hdk.wire.protocol import (
    ACTIVITY,
    APPROVAL_REQUEST,
    APPROVALS_ANSWER,
    APPROVALS_PENDING,
    BATTERIES_LIST,
    EVENT,
    FILES_LIST,
    FILES_READ,
    INPUT_REQUEST,
    ITEM,
    MODES_LIST,
    REQUEST_WITHDRAWN,
    RULES_LIST,
    RUN_CANCEL,
    SKILLS_LIST,
    STORE_DELETE,
    STORE_GET,
    STORE_LIST,
    STORE_PUT,
    STORE_VERSION,
    THREAD_ARCHIVE,
    THREAD_CLOSE,
    THREAD_FORK,
    THREAD_LIST,
    THREAD_REMAINING,
    THREAD_RESUME,
    THREAD_ROLLBACK,
    THREAD_SET_MODE,
    THREAD_SET_OPTION,
    THREAD_START,
    TOOLS_LIST,
    TURN_INTERRUPT,
    TURN_START,
    TURN_STEER,
)


class ThreadHost(Protocol):
    """What the process serving the wire composes and hands in: how to open and resume a thread,
    and the handles a host across the wire answers through."""

    approvals: Any
    store: Any
    rules: Any
    modes: Any
    skills: Any

    async def open(
        self, *, root: str, mode: str, want: str | None, name: str, observer: Any
    ) -> Thread: ...

    async def resume(self, thread_id: str, *, observer: Any) -> Thread: ...

    async def list(self) -> Any: ...


class ActivityToWire:
    """The observer a thread's ports carry: events are on the turn's own iterator; activity goes
    to the peer as a notification, tagged with the thread."""

    def __init__(self, peer: Any, thread_id: str) -> None:
        self._peer = peer
        self._thread_id = thread_id

    async def on(self, event: Event) -> None:
        return None

    async def on_activity(self, activity: Activity) -> None:
        await self._peer.notify(
            ACTIVITY,
            {"thread_id": self._thread_id, "activity": json.loads(dump(activity, Activity))},
        )


class ThreadMethods:
    """The thread methods, served on a peer over a `ThreadHost`."""

    def __init__(self, peer: Any, host: ThreadHost | None, clock: Any) -> None:
        self._peer = peer
        self._host = host
        self._clock = clock
        self.threads: dict[str, Thread] = {}
        for method, handler in (
            (THREAD_START, self._start),
            (THREAD_RESUME, self._resume),
            (THREAD_CLOSE, self._close),
            (THREAD_LIST, self._list),
            (THREAD_FORK, self._fork),
            (THREAD_ROLLBACK, self._rollback),
            (THREAD_ARCHIVE, self._archive),
            (THREAD_SET_MODE, self._set_mode),
            (THREAD_SET_OPTION, self._set_option),
            (THREAD_REMAINING, self._remaining),
            (TURN_START, self._turn),
            (TURN_STEER, self._steer),
            (TURN_INTERRUPT, self._interrupt),
            (APPROVALS_PENDING, self._pending),
            (APPROVALS_ANSWER, self._answer),
            (RUN_CANCEL, self._cancel),
            (STORE_PUT, self._store_put),
            (STORE_GET, self._store_get),
            (STORE_DELETE, self._store_delete),
            (STORE_LIST, self._store_list),
            (STORE_VERSION, self._store_version),
            (MODES_LIST, self._modes_list),
            (RULES_LIST, self._rules_list),
            (FILES_LIST, self._files_list),
            (FILES_READ, self._files_read),
            (BATTERIES_LIST, self._batteries_list),
            (TOOLS_LIST, self._tools_list),
            (SKILLS_LIST, self._skills_list),
        ):
            peer.serves(method, handler)
        self._relays: list[asyncio.Task[None]] = []

    # ------------------------------------------------------------------ lookups

    def _host_or_raise(self) -> ThreadHost:
        if self._host is None:
            raise RuntimeError(
                "no thread host: the process serving this wire handed in none, so threads "
                "cannot be opened here — `run`/`resume` with host-side ports still work"
            )
        return self._host

    def _thread(self, params: dict[str, Any]) -> Thread:
        thread_id = str(params.get("thread_id", ""))
        found = self.threads.get(thread_id)
        if found is None:
            raise KeyError(f"no thread {thread_id!r} is open on this wire")
        return found

    # ------------------------------------------------------------------ the thread

    async def _start(self, params: dict[str, Any]) -> dict[str, Any]:
        host = self._host_or_raise()
        self._relaying(host)
        thread_id_hint = str(params.get("thread_id", "") or "")
        # The observer needs an id before the thread exists; it is re-tagged with the thread's
        # own once the thread has minted it, so any placeholder will do here.
        thread_id = thread_id_hint or f"opening-{uuid.uuid4().hex[:8]}"
        thread = await host.open(
            root=str(params.get("root", "") or ""),
            mode=str(params.get("mode", "") or ""),
            want=params.get("provider") or None,
            name=str(params.get("name", "") or "tools"),
            observer=ActivityToWire(self._peer, thread_id),
        )
        # The thread minted its own id; keep ours in step with it by re-tagging the observer.
        observer = thread._ports.observer  # noqa: SLF001 — the wire's own observer, re-tagged
        if isinstance(observer, ActivityToWire):
            observer._thread_id = thread.id  # noqa: SLF001
        self.threads[thread.id] = thread
        return {
            "thread_id": thread.id,
            "root": thread.record.root,
            "provider": thread.record.provider,
            "mode": thread.record.mode,
            "modes": await self._modes(host),
        }

    async def _resume(self, params: dict[str, Any]) -> dict[str, Any]:
        host = self._host_or_raise()
        self._relaying(host)
        thread_id = str(params.get("thread_id", ""))
        thread = await host.resume(thread_id, observer=ActivityToWire(self._peer, thread_id))
        self.threads[thread.id] = thread
        return {
            "thread_id": thread.id,
            "root": thread.record.root,
            "provider": thread.record.provider,
            "mode": thread.record.mode,
            "modes": await self._modes(host),
            "turns": [_turn_json(t) for t in thread.record.turns],
        }

    async def _close(self, params: dict[str, Any]) -> dict[str, Any]:
        thread = self._thread(params)
        await thread.close()
        del self.threads[thread.id]
        return {"closed": thread.id}

    async def close_all(self) -> None:
        """What this wire opened, closed with it: a session that ends — the page reloaded, the
        pipe closed — must not leave a provider process and an offered socket behind. Measured:
        without this every reload of the studio kept the previous provider alive."""
        for relay in self._relays:
            relay.cancel()
        self._relays = []
        for thread in list(self.threads.values()):
            try:
                await thread.close()
            except Exception:  # noqa: BLE001 — one thread's trouble must not keep the rest open
                continue
        self.threads.clear()

    async def _list(self, _params: dict[str, Any]) -> dict[str, Any]:
        host = self._host_or_raise()
        return {"threads": [_thread_json(t) for t in await host.list()]}

    async def _fork(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"thread": _thread_json(await self._thread(params).fork())}

    async def _rollback(self, params: dict[str, Any]) -> dict[str, Any]:
        rolled = await self._thread(params).rollback(to_turn=int(params.get("to_turn", 0)))
        return {"thread": _thread_json(rolled)}

    async def _archive(self, params: dict[str, Any]) -> dict[str, Any]:
        host = self._host_or_raise()
        thread_id = str(params.get("thread_id", ""))
        store = getattr(host, "threads", None)
        archive = getattr(store, "archive", None)
        if archive is None:
            raise RuntimeError("this thread host's store cannot archive")
        await archive(thread_id)
        return {"archived": thread_id}

    async def _set_mode(self, params: dict[str, Any]) -> dict[str, Any]:
        changed = await self._thread(params).set_mode(str(params.get("mode", "")))
        return {"events": [json.loads(dump(e, Event)) for e in changed]}

    async def _set_option(self, params: dict[str, Any]) -> dict[str, Any]:
        await self._thread(params).set_option(str(params.get("key", "")), params.get("value"))
        return {"ok": True}

    async def _remaining(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"lease": json.loads(dump(self._thread(params).remaining(), Lease))}

    # ------------------------------------------------------------------ the turn

    async def _turn(self, params: dict[str, Any]) -> dict[str, Any]:
        thread = self._thread(params)
        text = str(params.get("text", ""))
        fold = Fold()
        count = 0
        # **One fold, both sides of the wire** (D46) — the same one `run` uses.
        async for event in thread.turn(text):
            count += 1
            await self._peer.notify(
                EVENT, {"thread_id": thread.id, "event": json.loads(dump(event, Event))}
            )
            fold.feed(event)
            for done in fold.closed_now:
                await self._peer.notify(ITEM, {"thread_id": thread.id, "item": as_json(done)})
        return {"events": count, "turn": _turn_json(thread.record.turns[-1])}

    async def _steer(self, params: dict[str, Any]) -> dict[str, Any]:
        taken = await self._thread(params).steer(str(params.get("text", "")))
        return {"taken": "now" if taken else "next"}

    async def _interrupt(self, params: dict[str, Any]) -> dict[str, Any]:
        thread = self._thread(params)
        was = thread.turning
        await thread.interrupt()
        return {"interrupted": was}

    # ------------------------------------------------------------------ the handles

    def _relaying(self, host: ThreadHost) -> None:
        """Push each request as it becomes pending, and each withdrawal — once per wire."""
        if self._relays or getattr(host, "approvals", None) is None:
            return
        self._relays = [
            asyncio.create_task(self._relay_requests(host)),
            asyncio.create_task(self._relay_withdrawals(host)),
        ]

    def _thread_of_run(self, run_id: str) -> str:
        for thread in self.threads.values():
            turns = thread.record.turns
            if turns and turns[-1].run_id == run_id:
                return thread.id
        return ""

    async def _relay_requests(self, host: ThreadHost) -> None:
        while True:
            pending = await host.approvals.next()
            await self._peer.notify(
                INPUT_REQUEST if pending.kind == "input" else APPROVAL_REQUEST,
                {
                    "thread_id": self._thread_of_run(pending.run_id),
                    "request": _request_json(pending),
                },
            )

    async def _relay_withdrawals(self, host: ThreadHost) -> None:
        while True:
            gone = await host.approvals.next_withdrawn()
            await self._peer.notify(
                REQUEST_WITHDRAWN,
                {"thread_id": self._thread_of_run(gone.run_id), "handle": gone.handle},
            )

    async def _pending(self, _params: dict[str, Any]) -> dict[str, Any]:
        host = self._host_or_raise()
        return {"requests": [_request_json(p) for p in host.approvals.pending()]}

    async def _answer(self, params: dict[str, Any]) -> dict[str, Any]:
        """The host's answer, as JSON: `{"kind": "approve"}`, `{"kind": "deny", "reason"}`,
        `{"kind": "approve_and_add_rule", "rule": {...}}` — or `{"text": "..."}` for an input
        request. The runtime's `accept_answer` reads these shapes (D65)."""
        host = self._host_or_raise()
        answer = params.get("answer")
        if isinstance(answer, dict) and "text" in answer and "kind" not in answer:
            answer = str(answer["text"])
        done = host.approvals.answer(str(params.get("handle", "")), answer)
        return {"answered": bool(done)}

    async def _cancel(self, params: dict[str, Any]) -> dict[str, Any]:
        thread = self._thread(params)
        was = thread.turning
        await thread.interrupt()
        return {"cancelled": was}

    # ------------------------------------------------------------------ the store

    def _store_or_raise(self) -> Any:
        host = self._host_or_raise()
        store = getattr(host, "store", None)
        if store is None:
            raise RuntimeError("no store: the process serving this wire handed in none")
        return store

    async def _store_put(self, params: dict[str, Any]) -> dict[str, Any]:
        await self._store_or_raise().put(
            str(params["collection"]), str(params["key"]), params.get("row")
        )
        return {"ok": True}

    async def _store_get(self, params: dict[str, Any]) -> dict[str, Any]:
        row = await self._store_or_raise().get(str(params["collection"]), str(params["key"]))
        return {"row": row}

    async def _store_delete(self, params: dict[str, Any]) -> dict[str, Any]:
        await self._store_or_raise().delete(str(params["collection"]), str(params["key"]))
        return {"ok": True}

    async def _store_list(self, params: dict[str, Any]) -> dict[str, Any]:
        rows = await self._store_or_raise().list(str(params["collection"]))
        return {"rows": [[key, row] for key, row in rows]}

    async def _store_version(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"version": await self._store_or_raise().version(str(params["collection"]))}

    async def _modes_list(self, _params: dict[str, Any]) -> dict[str, Any]:
        return {"modes": await self._modes(self._host_or_raise())}

    async def _rules_list(self, _params: dict[str, Any]) -> dict[str, Any]:
        from shadow_hdk.kernel import ActRule

        host = self._host_or_raise()
        registry = getattr(host, "rules", None)
        if registry is None:
            return {"rules": []}
        all_now = getattr(registry, "all_now", None)
        rules = await all_now() if all_now is not None else registry.all()
        return {"rules": [json.loads(dump(r, ActRule)) for r in rules]}

    # ------------------------------------------------------------------ the workspace (D69)

    async def _files_list(self, params: dict[str, Any]) -> dict[str, Any]:
        root = Path(self._thread(params).record.root).resolve()
        found: list[dict[str, Any]] = []
        for path in sorted(root.rglob("*")):
            parts = path.relative_to(root).parts
            if any(part.startswith(".") or part == "__pycache__" for part in parts):
                continue
            if path.is_file():
                stat = path.stat()
                found.append(
                    {
                        "path": str(path.relative_to(root)),
                        "bytes": stat.st_size,
                        "mtime": stat.st_mtime,
                    }
                )
        return {"files": found}

    async def _files_read(self, params: dict[str, Any]) -> dict[str, Any]:
        root = Path(self._thread(params).record.root).resolve()
        relative = str(params.get("path", ""))
        target = (root / relative).resolve()
        # `..` is not a dotfile — it is the traversal the root check below refuses on its own.
        hidden = any(part.startswith(".") and part != ".." for part in Path(relative).parts)
        if not target.is_relative_to(root) or hidden or not target.is_file():
            raise FileNotFoundError(f"{relative!r} is not in the workspace")
        try:
            return {"content": target.read_text(encoding="utf-8")[:200_000]}
        except UnicodeDecodeError:
            return {"content": f"(binary, {target.stat().st_size} bytes)"}

    async def _batteries_list(self, _params: dict[str, Any]) -> dict[str, Any]:
        host = self._host_or_raise()
        listing = getattr(host, "battery_listing", None)
        return {"batteries": await listing() if listing is not None else []}

    # ------------------------------------------------------------------ the registries (Phase 28)

    async def _tools_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """What the thread's agent is offered now, with effects and the mode's judgement — the
        harness's own answer (`Thread.tools`), so a page shows the registry rather than guessing."""
        from shadow_hdk.kernel import Registration

        offered = await self._thread(params).tools()
        return {
            "tools": [
                {
                    "id": o.registration.id,
                    "name": o.registration.component.interface.name,
                    "description": o.registration.component.interface.description,
                    "effects": json.loads(dump(o.registration.component.effects, EffectProfile)),
                    "judgement": o.judgement,
                    "source": o.source,
                    "registration": json.loads(dump(o.registration, Registration)),
                }
                for o in offered
            ]
        }

    async def _skills_list(self, _params: dict[str, Any]) -> dict[str, Any]:
        host = self._host_or_raise()
        registry = getattr(host, "skills", None)
        if registry is None:
            return {"skills": []}
        return {
            "skills": [
                {
                    "name": s.name,
                    "description": s.description,
                    "needs": sorted(s.needs),
                    "source": s.source,
                }
                for s in await registry.all()
            ]
        }

    async def _modes(self, host: ThreadHost) -> list[dict[str, Any]]:
        registry = getattr(host, "modes", None)
        if registry is None:
            return []
        return [
            {"id": m.id, "name": m.name, "description": m.description, "source": m.source}
            for m in await registry.all()
        ]


def _request_json(pending: Any) -> dict[str, Any]:
    return {
        "handle": pending.handle,
        "run_id": pending.run_id,
        "step": pending.step,
        "question": pending.question,
        "component": pending.component,
        "inputs": pending.inputs,
        "kind": pending.kind,
    }


def _turn_json(turn: Any) -> dict[str, Any]:
    return {
        "id": turn.id,
        "run_id": turn.run_id,
        "prompt": turn.prompt,
        "at": turn.at,
        "outcome": turn.outcome,
        "text": turn.text,
    }


def _thread_json(record: ThreadRecord) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(dump(record, ThreadRecord))
    return loaded


__all__ = ["ActivityToWire", "ThreadHost", "ThreadMethods"]
