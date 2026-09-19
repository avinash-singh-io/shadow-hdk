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
from typing import Any, Protocol, cast

from shadow_hdk.kernel import (
    Compatibility,
    Composition,
    EffectProfile,
    EnvironmentCapabilities,
    Event,
    ExecutionSelection,
    Lease,
    PlanLimits,
    ProviderCapabilities,
    Spent,
    ThreadRecord,
)
from shadow_hdk.kernel.activity import Activity
from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.runtime.items import Fold, as_json
from shadow_hdk.runtime.threads import OnQuestion, Thread, When
from shadow_hdk.wire.protocol import (
    ACTIVITY,
    ADMIN_SESSIONS,
    ADMIN_THREADS,
    APPROVAL_REQUEST,
    APPROVALS_ANSWER,
    APPROVALS_PENDING,
    BATTERIES_LIST,
    CAPABILITIES_CHECK,
    EVENT,
    FILES_LIST,
    FILES_READ,
    INPUT_REQUEST,
    ITEM,
    MODES_LIST,
    PROVIDERS_LIST,
    REQUEST_WITHDRAWN,
    RULES_LIST,
    RUN_CANCEL,
    SKILLS_LIST,
    STORE_DELETE,
    STORE_GET,
    STORE_LIST,
    STORE_PUT,
    STORE_VERSION,
    THREAD_ADD_ROOT,
    THREAD_AMEND,
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
        self,
        *,
        root: str,
        mode: str,
        want: str | None,
        name: str,
        observer: Any,
        roots: Any = None,
        principal: str = "",
        attributes: Any = None,
        budget: Any = None,
        requirements: Any = None,
        plan_limits: Any = None,
        peer_components: Any = (),
    ) -> Thread: ...

    async def resume(
        self,
        thread_id: str,
        *,
        observer: Any,
        plan_limits: Any = None,
        peer_components: Any = (),
        attributes: Any = None,
    ) -> Thread: ...

    async def list(self) -> Any: ...

    async def checkpointer(self) -> Any: ...


async def host_checkpointer(host: Any) -> Any:
    """The host's checkpointer, when it has one (D80): a session runs on it, so a run parked in
    one session is there for the next — a page reloaded, a process restarted. `None` from a host
    without one gives the session a checkpointer of its own, for as long as the session lives."""
    ask = getattr(host, "checkpointer", None)
    return await ask() if ask is not None else None


class SoleSession:
    """What a runtime over a pipe or a loopback knows of its sessions (D86): itself. The HTTP
    app hands in its own view of every session it serves."""

    def __init__(self, runtime: Any, *, clock: Any = None) -> None:
        self._runtime = runtime
        self._opened_at = clock.now() if clock is not None else _now()

    async def sessions(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "this",
                "opened_at": self._opened_at,
                "threads": sorted(self._runtime.threads.threads),
            }
        ]


def _now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


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

    def __init__(
        self,
        peer: Any,
        host: ThreadHost | None,
        clock: Any,
        *,
        admin: Any = None,
        holder: Any = None,
        session: str = "this",
    ) -> None:
        self._peer = peer
        self._host = host
        self._clock = clock
        self._admin = admin
        self._holder = holder
        """Who keeps the live run for a host-side component's callbacks (`context.propose` and
        the rest) — the `RuntimeSide`, as for `run`."""
        self._session = session
        """This connection's id, the transport's own (D77): the name a gone host is given."""
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
            (THREAD_ADD_ROOT, self._add_root),
            (THREAD_AMEND, self._amend),
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
            (PROVIDERS_LIST, self._providers_list),
            (CAPABILITIES_CHECK, self._capabilities_check),
            (TOOLS_LIST, self._tools_list),
            (SKILLS_LIST, self._skills_list),
            (ADMIN_SESSIONS, self._admin_sessions),
            (ADMIN_THREADS, self._admin_threads),
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
            roots=params.get("roots") or None,
            # Passed only when given (D82), so a host written before identity was on the thread
            # is still called the way it always was.
            **({"principal": str(params["principal"])} if params.get("principal") else {}),
            **({"attributes": params["attributes"]} if params.get("attributes") else {}),
            **({"budget": params["budget"]} if params.get("budget") is not None else {}),
            **(
                {"requirements": params["requirements"]}
                if params.get("requirements") is not None
                else {}
            ),
            **(
                {"plan_limits": params["plan_limits"]}
                if params.get("plan_limits") is not None
                else {}
            ),
            **self._peer_components(params),
        )
        # The thread minted its own id; keep ours in step with it by re-tagging the observer.
        observer = thread.ports.observer  # the wire's own observer, re-tagged
        if isinstance(observer, ActivityToWire):
            observer._thread_id = thread.id  # noqa: SLF001
        self.threads[thread.id] = thread
        result = {
            "thread_id": thread.id,
            **_workspace_json(thread),
            "provider": thread.record.provider,
            "mode": thread.record.mode,
            "plan_limits": _plan_limits_json(thread.plan_limits),
            "modes": await self._modes(host, thread),
            **_identity_json(thread),
        }
        result["capabilities"] = _selection_json(_selection_of(host, thread.id))
        return result

    async def _resume(self, params: dict[str, Any]) -> dict[str, Any]:
        host = self._host_or_raise()
        self._relaying(host)
        thread_id = str(params.get("thread_id", ""))
        take_over = getattr(self._admin, "take_over", None)
        if take_over is not None:
            # A page reloaded (D94): the thread its old session still holds, closed there first.
            await take_over(thread_id, self)
        attributes = params.get("attributes")  # the host's current words (D140), or nothing
        if attributes is not None and not isinstance(attributes, dict):
            raise ValueError("attributes must be an object")
        thread = await host.resume(
            thread_id,
            observer=ActivityToWire(self._peer, thread_id),
            **(
                {"plan_limits": params["plan_limits"]}
                if params.get("plan_limits") is not None
                else {}
            ),
            **({"attributes": attributes} if attributes is not None else {}),
            **self._peer_components(params),
        )
        self.threads[thread.id] = thread
        # A question the last host left open (D80) is offered again: pushed the way a live one
        # is, so a page that only listens shows the card, and in the result for the one that
        # asked.
        for question in thread.pending:
            await self._peer.notify(
                INPUT_REQUEST if question.kind == "input" else APPROVAL_REQUEST,
                {"thread_id": thread.id, "request": _pending_json(question)},
            )
        result = {
            "thread_id": thread.id,
            **_workspace_json(thread),
            "provider": thread.record.provider,
            "mode": thread.record.mode,
            "plan_limits": _plan_limits_json(thread.plan_limits),
            "modes": await self._modes(host, thread),
            "turns": [_turn_json(t) for t in thread.record.turns],
            "pending": [_pending_json(q) for q in thread.pending],
            **_identity_json(thread),
        }
        result["capabilities"] = _selection_json(_selection_of(host, thread.id))
        return result

    def _peer_components(self, params: dict[str, Any]) -> dict[str, Any]:
        """The host's own components, by inversion (ENH-030, D21): with `host_components: true`
        this connection's `RemoteComponents` port joins the thread's registry — the runtime asks
        the host what it has and asks it to act, exactly as `run` does. Passed only when asked
        for, so a host written before the door opened is called the way it always was."""
        if not params.get("host_components"):
            return {}
        from shadow_hdk.wire.remote import RemoteComponents

        return {
            "peer_components": (RemoteComponents(self._peer, self._holder, session=self._session),)
        }

    async def _close(self, params: dict[str, Any]) -> dict[str, Any]:
        thread = self._thread(params)
        await thread.close()
        del self.threads[thread.id]
        return {"closed": thread.id}

    async def close_one(self, thread_id: str) -> None:
        """One thread closed and forgotten — taken over by another session (D94)."""
        thread = self.threads.pop(thread_id, None)
        if thread is not None:
            await thread.close()

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
        """Every thread in the store, each row saying who holds it now (D81) — `None` when
        nobody does, so a page knows which it may resume."""
        host = self._host_or_raise()
        store = getattr(host, "threads", None)
        who = getattr(store, "held_by", None)
        rows = []
        for record in await host.list():
            row = _thread_json(record)
            row["held_by"] = await who(record.id) if who is not None else None
            rows.append(row)
        return {"threads": rows}

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
        thread = self._thread(params)
        changed = await thread.set_mode(str(params.get("mode", "")))
        return {
            "events": await self._announced(thread, changed),
            "environment": thread.environment_mode,
            "unmapped_behaviour": list(thread.unmapped_behaviour),
            "plan_limits": _plan_limits_json(thread.plan_limits),
        }

    async def _amend(self, params: dict[str, Any]) -> dict[str, Any]:
        """A parked plan continued on a different composition (D116). `composition` is the
        kernel's `Composition` as JSON; `answer` the person's answer to the question the plan
        parked on — `{"kind": "approve"}` and the rest, as `approvals/answer` reads them. The
        amendment is admitted under the thread's limits before the run takes it: `admitted`
        with the events down the stream, or refused with every `mismatch`, the plan as it was
        and the question still open."""
        thread = self._thread(params)
        composition = load(json.dumps(params.get("composition")), Composition)
        events = await thread.amend(
            str(params.get("handle", "")), composition, params.get("answer")
        )
        lines = await self._announced(thread, events)
        refusal = next(
            (line for line in lines if line["kind"] == "plan_refused" and line.get("amendment")),
            None,
        )
        return {
            "admitted": refusal is None,
            "mismatches": list(refusal["mismatches"]) if refusal is not None else [],
            "events": lines,
        }

    async def _add_root(self, params: dict[str, Any]) -> dict[str, Any]:
        thread = self._thread(params)
        changed = await thread.add_root(str(params.get("name", "")), str(params.get("path", "")))
        return {
            "events": await self._announced(thread, changed),
            **_workspace_json(thread),
        }

    async def _announced(self, thread: Thread, changed: list[Event]) -> list[dict[str, Any]]:
        """A change between turns is on the record, so it goes down the stream like any event —
        a reader that only listens sees it — and comes back in the result for the one that asked."""
        lines = [json.loads(dump(e, Event)) for e in changed]
        for line in lines:
            await self._peer.notify(EVENT, {"thread_id": thread.id, "event": line})
        return lines

    async def _set_option(self, params: dict[str, Any]) -> dict[str, Any]:
        await self._thread(params).set_option(str(params.get("key", "")), params.get("value"))
        return {"ok": True}

    async def _remaining(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"lease": json.loads(dump(self._thread(params).remaining(), Lease))}

    # ------------------------------------------------------------------ the turn

    async def _turn(self, params: dict[str, Any]) -> dict[str, Any]:
        """`when` (D81) names what this turn does while one runs: `enqueue` (the default),
        `reject` — the refusal names the running turn — or `interrupt`. `on_question` (D88):
        `wait` puts a question to the host live; `park` keeps it and ends the turn `parked`, for
        a host whose request must return — `approvals/answer` settles it later."""
        thread = self._thread(params)
        text = str(params.get("text", ""))
        when = cast(When, str(params.get("when", "enqueue") or "enqueue"))
        on_question = cast(OnQuestion, str(params.get("on_question", "wait") or "wait"))
        attributes = params.get("attributes")  # this turn's words (D140), or nothing
        if attributes is not None and not isinstance(attributes, dict):
            raise ValueError("attributes must be an object")
        fold = Fold()
        count = 0
        # **One fold, both sides of the wire** (D46) — the same one `run` uses.
        async for event in thread.turn(
            text, when=when, on_question=on_question, attributes=attributes
        ):
            count += 1
            await self._peer.notify(
                EVENT, {"thread_id": thread.id, "event": json.loads(dump(event, Event))}
            )
            fold.feed(event)
            for done in fold.closed_now:
                await self._peer.notify(ITEM, {"thread_id": thread.id, "item": as_json(done)})
        last = thread.conversation.last
        ended = next(
            (t for t in thread.record.turns if last is not None and t.id == last.id),
            thread.record.turns[-1],
        )
        return {"events": count, "turn": _turn_json(ended)}

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
        """Every question open now: the ones a running turn waits on live, and the ones a host
        that died left on a thread's record (D80), each once."""
        host = self._host_or_raise()
        live = [_request_json(p) for p in host.approvals.pending()]
        seen = {r["handle"] for r in live}
        left = [
            _pending_json(q)
            for thread in self.threads.values()
            for q in thread.pending
            if q.handle not in seen
        ]
        return {"requests": [*live, *left]}

    async def _answer(self, params: dict[str, Any]) -> dict[str, Any]:
        """The host's answer, as JSON: `{"kind": "approve"}`, `{"kind": "deny", "reason"}`,
        `{"kind": "approve_and_add_rule", "rule": {...}}`, `{"kind": "park"}` (kept for a later
        request — D88) — or `{"text": "..."}` for an input request. The runtime's
        `accept_answer` reads these shapes (D65). A question a running turn waits on is
        answered live; one a turn left (D80, D88) is settled by its thread — the parked act
        runs from its checkpoint, and what happened goes down the stream."""
        host = self._host_or_raise()
        answer = params.get("answer")
        if isinstance(answer, dict) and "text" in answer and "kind" not in answer:
            answer = str(answer["text"])
        handle = str(params.get("handle", ""))
        if host.approvals.answer(handle, answer):
            return {"answered": True}
        for thread in self.threads.values():
            if any(q.handle == handle for q in thread.pending):
                settled = await thread.settle(handle, answer)
                return {"answered": True, "events": await self._announced(thread, settled)}
        return {"answered": False}

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

    async def _modes_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """Every mode — or, with a `thread_id`, the ones in that thread's scope (D82)."""
        host = self._host_or_raise()
        thread = self._thread(params) if params.get("thread_id") else None
        return {"modes": await self._modes(host, thread)}

    async def _rules_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """Every rule — or, with a `thread_id`, the ones in that thread's scope (D82)."""
        from shadow_hdk.kernel import ActRule

        host = self._host_or_raise()
        registry = getattr(host, "rules", None)
        if registry is None:
            return {"rules": []}
        all_now = getattr(registry, "all_now", None)
        if all_now is None:
            rules = registry.all()
        elif params.get("thread_id"):
            rules = await all_now(**_scope_of(self._thread(params)))
        else:
            rules = await all_now()
        return {"rules": [json.loads(dump(r, ActRule)) for r in rules]}

    # ------------------------------------------------------------------ the workspace (D69)

    async def _files_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """Every file under every root (D76), each entry saying which root it is in."""
        found: list[dict[str, Any]] = []
        for root in self._thread(params).workspace.roots:
            base = Path(root.path)
            for path in sorted(base.rglob("*")):
                parts = path.relative_to(base).parts
                if any(part.startswith(".") or part == "__pycache__" for part in parts):
                    continue
                if path.is_file():
                    stat = path.stat()
                    found.append(
                        {
                            "root": root.name,
                            "path": str(path.relative_to(base)),
                            "bytes": stat.st_size,
                            "mtime": stat.st_mtime,
                        }
                    )
        return {"files": found}

    async def _files_read(self, params: dict[str, Any]) -> dict[str, Any]:
        """One file, under the root named — the primary when none is (D76)."""
        workspace = self._thread(params).workspace
        name = str(params.get("root", "") or "")
        if name and not workspace.has(name):
            raise FileNotFoundError(f"no root {name!r}: {name!r} is not in the workspace")
        root = Path((workspace.named(name) if name else workspace.primary).path)
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

    async def _providers_list(self, _params: dict[str, Any]) -> dict[str, Any]:
        host = self._host_or_raise()
        listing = getattr(host, "provider_listing", None)
        return {"providers": await listing() if listing is not None else []}

    async def _capabilities_check(self, params: dict[str, Any]) -> dict[str, Any]:
        host = self._host_or_raise()
        check = getattr(host, "check_capabilities", None)
        if check is None:
            raise RuntimeError("this thread host does not expose capability selection")
        selected = await check(
            mode=str(params.get("mode", "") or ""),
            want=params.get("provider") or None,
            requirements=params.get("requirements"),
            root=str(params.get("root", "") or ""),
        )
        return {"capabilities": _selection_json(selected)}

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

    # ------------------------------------------------------------------ operations (D86)

    async def _admin_sessions(self, _params: dict[str, Any]) -> dict[str, Any]:
        """Every session the process serves: its id, when it opened, the threads it has open."""
        if self._admin is None:
            return {"sessions": []}
        return {"sessions": await self._admin.sessions()}

    async def _admin_threads(self, _params: dict[str, Any]) -> dict[str, Any]:
        """Every thread in the store, with who holds it (D81) and which session has it open —
        the operator's view; a page shows a person their own through `thread/list`. A runtime
        with no thread host has no threads to list, which is an answer, not a refusal."""
        host = self._host
        if host is None:
            return {"threads": []}
        sessions = await self._admin.sessions() if self._admin is not None else []
        open_in = {tid: s["id"] for s in sessions for tid in s["threads"]}
        store = getattr(host, "threads", None)
        who = getattr(store, "held_by", None)
        rows = []
        for record in await host.list():
            rows.append(
                {
                    "id": record.id,
                    "created_at": record.created_at,
                    "mode": record.mode,
                    "provider": record.provider,
                    "principal": record.principal,
                    "attributes": dict(record.attributes),
                    "turns": len(record.turns),
                    "pending": len(record.pending),
                    "spent": json.loads(dump(record.spent, Spent)),
                    "archived": record.archived,
                    "held_by": await who(record.id) if who is not None else None,
                    "session": open_in.get(record.id),
                }
            )
        return {"threads": rows}

    async def _modes(self, host: ThreadHost, thread: Thread | None = None) -> list[dict[str, Any]]:
        """The modes — in the thread's scope when one is named (D82)."""
        registry = getattr(host, "modes", None)
        if registry is None:
            return []
        modes = (
            await registry.all(**_scope_of(thread)) if thread is not None else await registry.all()
        )
        return [
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "source": m.source,
                "scope": m.scope,
                "plan": _plan_limits_json(getattr(m, "plan", None)),
            }
            for m in modes
        ]


def _plan_limits_json(limits: PlanLimits | None) -> dict[str, Any] | None:
    """Plan limits as the wire says them (D109): the three axes, `null` where unbounded; `null`
    as a whole when nothing bounds the plan."""
    if limits is None:
        return None
    return {"depth": limits.depth, "fan_out": limits.fan_out, "steps": limits.steps}


def _scope_of(thread: Thread) -> dict[str, Any]:
    """The thread's identity, as the registries take it (D82)."""
    return {
        "principal": thread.record.principal or None,
        "attributes": dict(thread.record.attributes),
    }


def _identity_json(thread: Thread) -> dict[str, Any]:
    return {"principal": thread.record.principal, "attributes": dict(thread.record.attributes)}


def _selection_json(selection: ExecutionSelection) -> dict[str, Any]:
    selected: dict[str, Any] = json.loads(dump(selection, ExecutionSelection))
    return selected


def _selection_of(host: ThreadHost, thread_id: str) -> ExecutionSelection:
    selected = getattr(host, "capabilities_for", None)
    if selected is not None:
        return cast(ExecutionSelection, selected(thread_id))
    return ExecutionSelection(ProviderCapabilities(), EnvironmentCapabilities(), Compatibility())


def _pending_json(question: Any) -> dict[str, Any]:
    """A question off the record (D80), in the shape a live request has — a page shows both the
    same way — with the turn it belongs to."""
    return {
        "handle": question.handle,
        "run_id": question.run_id,
        "step": question.step,
        "question": question.question,
        "component": question.component,
        "inputs": question.inputs,
        "kind": question.kind,
        "turn": question.turn,
    }


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


def _workspace_json(thread: Thread) -> dict[str, Any]:
    """`root` (the primary) for a one-root reader; `roots` the whole workspace; `environment`
    the sandbox's own mode beside the policy's (D76); `unmapped_behaviour` the fields the mode
    set that the provider could not take (ENH-020) — a host hides those controls."""
    return {
        "root": thread.record.root,
        "roots": thread.workspace.as_json(),
        "environment": thread.environment_mode,
        "unmapped_behaviour": list(thread.unmapped_behaviour),
    }


def _turn_json(turn: Any) -> dict[str, Any]:
    return {
        "id": turn.id,
        "run_id": turn.run_id,
        "prompt": turn.prompt,
        "at": turn.at,
        "outcome": turn.outcome,
        "text": turn.text,
        "failure": getattr(turn, "failure", ""),
    }


def _thread_json(record: ThreadRecord) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(dump(record, ThreadRecord))
    return loaded


__all__ = ["ActivityToWire", "ThreadHost", "ThreadMethods", "host_checkpointer"]
