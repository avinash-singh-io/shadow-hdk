"""A thread over the wire (D67): a host in any language opens one, turns it, and sees items and
activity as they happen — the host's controls of Phase 25, crossed.

The runtime side holds the ports in this shape (a batteries host: the process serving the wire
hands in a `ThreadHost`); the inverted shape (`run`/`resume` with host-side ports) is untouched.
The host side is driven through the raw peer, the way a client in another language would call.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import anyio
import pytest

from shadow_hdk.kernel import Ceiling, EffectProfile, Floor, Lease, ScopeSet, Turn
from shadow_hdk.kernel.ports import AgentSession, Allow, Context, Judgement
from shadow_hdk.runtime import Approvals, Ports
from shadow_hdk.runtime.store import InMemoryStore
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)
from shadow_hdk.runtime.threads import InMemoryThreads, Thread
from shadow_hdk.wire.sides import loopback
from shadow_hdk.wire.threads import ThreadHost

pytestmark = pytest.mark.anyio

LOOK = make_registration("look", effects=EffectProfile(reads=ScopeSet.of("workspace")))


async def look(_inputs: Any) -> Any:
    from shadow_hdk.kernel import Completed

    return Completed({"found": 1})


class ScriptedAgent:
    """Calls `look` through the registry, streams a little activity, says its line."""

    def __init__(self) -> None:
        self.reach: Any = None
        self.opened = 0
        self.steered: list[str] = []

    async def open(self, *, tools: Any = (), workspace: Any = None, behaviour: Any = None) -> Any:
        self.opened += 1
        agent = self

        class _Session:
            async def turn(self, prompt: str) -> Turn:
                from shadow_hdk.runtime import current_run

                context = current_run()
                assert context is not None
                await context.activity("thinking", "hmm")
                await agent.reach("look", {})
                await context.activity("text", "the ")
                await context.activity("text", "answer")
                return Turn(text="the answer to " + prompt, reasoning="thought")

            async def steer(self, text: str) -> None:
                agent.steered.append(text)

            async def close(self) -> None:
                pass

            async def stream(self, prompt: str) -> AsyncIterator[Any]:  # pragma: no cover
                raise NotImplementedError
                yield

        return cast(AgentSession, _Session())


class AllowAll:
    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        return Allow()


class _OwnIds(FixedClock):
    def new_id(self) -> str:
        return "thread-" + super().new_id()


class ScriptedThreads:
    """A `ThreadHost` over the doubles: what `serve` composes from the shipped adapters."""

    def __init__(self, tmp_path: Path) -> None:
        self.approvals = Approvals()
        self.store: Any = InMemoryStore()
        self.threads = InMemoryThreads()
        self.agent = ScriptedAgent()
        self.rules: Any = None
        self.modes: Any = None
        self.skills: Any = None
        self._tmp = tmp_path

    def _ports(self, observer: Any) -> Ports:
        return Ports(
            model=None,
            components=(InMemoryComponents([(LOOK, look)]),),
            governance=AllowAll(),
            sink=ListSink(),
            # Its own ids, unlike the wire's clock: a thread mints its id from *these* ports, so
            # the wire cannot guess it in advance and must re-tag its observer once it knows —
            # with one shared clock both sides counted in step and a wrong tag never showed.
            clock=_OwnIds(),
            observer=observer,
        )

    async def open(
        self,
        *,
        root: str,
        mode: str,
        want: str | None,
        name: str,
        observer: Any,
        roots: Any = None,
    ) -> Thread:
        thread = await Thread.open(
            agent=cast(Any, self.agent),
            ports=self._ports(observer),
            store=self.threads,
            root=root or str(self._tmp),
            lease=Lease(Ceiling(20, 600, None), Floor(0)),
            name=name,
            approvals=self.approvals,
            mode=mode,
            provider="scripted",
        )
        self.agent.reach = thread.registry.call
        return thread

    async def resume(self, thread_id: str, *, observer: Any) -> Thread:
        thread = await Thread.resume(
            thread_id,
            agent=cast(Any, self.agent),
            ports=self._ports(observer),
            store=self.threads,
            lease=Lease(Ceiling(20, 600, None), Floor(0)),
            approvals=self.approvals,
        )
        self.agent.reach = thread.registry.call
        return thread

    async def list(self) -> Any:
        return await self.threads.list()


def _host(tmp_path: Path) -> ThreadHost:
    return cast(ThreadHost, ScriptedThreads(tmp_path))


async def test_a_thread_starts_and_a_turn_streams_events_items_and_activity(
    tmp_path: Path,
) -> None:
    heard: list[tuple[str, dict[str, Any]]] = []
    async with loopback(threads=_host(tmp_path)) as (host, _runtime):
        await host.initialize()
        host.peer.hears("event", _keeper(heard, "event"))
        host.peer.hears("item", _keeper(heard, "item"))
        host.peer.hears("activity", _keeper(heard, "activity"))

        started = await host.peer.call(
            "thread/start", {"root": str(tmp_path), "mode": "workspace-write", "name": "tools"}
        )
        assert started["thread_id"] and started["provider"] == "scripted"

        with anyio.fail_after(30):
            done = await host.peer.call(
                "turn/start", {"thread_id": started["thread_id"], "text": "hello?"}
            )

    assert done["turn"]["text"] == "the answer to hello?"
    assert done["turn"]["outcome"] == "completed" and done["turn"]["id"] == "turn-1"
    kinds = [p["event"]["kind"] for k, p in heard if k == "event"]
    assert "started" in kinds and "ended" in kinds and "reasoning" in kinds
    assert all(p["thread_id"] == started["thread_id"] for _k, p in heard), "every line is tagged"
    items = [p["item"] for k, p in heard if k == "item"]
    assert [i["step"] for i in items if i.get("component") == "turn"] == ["turn-1"]
    assert any(i.get("component") == "look" for i in items), "the tool call is an item too"
    activity = [(p["activity"]["kind"], p["activity"]["text"]) for k, p in heard if k == "activity"]
    assert activity == [("thinking", "hmm"), ("text", "the "), ("text", "answer")]


async def test_the_thread_operations_cross(tmp_path: Path) -> None:
    async with loopback(threads=_host(tmp_path)) as (host, _runtime):
        await host.initialize()
        started = await host.peer.call(
            "thread/start", {"root": str(tmp_path), "mode": "workspace-write"}
        )
        tid = started["thread_id"]
        with anyio.fail_after(30):
            await host.peer.call("turn/start", {"thread_id": tid, "text": "one"})
            await host.peer.call("turn/start", {"thread_id": tid, "text": "two"})

        listed = await host.peer.call("thread/list", {})
        assert [t["id"] for t in listed["threads"]] == [tid]
        assert [t["prompt"] for t in listed["threads"][0]["turns"]] == ["one", "two"]

        forked = await host.peer.call("thread/fork", {"thread_id": tid})
        assert forked["thread"]["forked_from"] == tid
        rolled = await host.peer.call("thread/rollback", {"thread_id": tid, "to_turn": 1})
        assert rolled["thread"]["seeded_turns"] == 1
        await host.peer.call("thread/archive", {"thread_id": rolled["thread"]["id"]})
        remaining = await host.peer.call("thread/list", {})
        assert rolled["thread"]["id"] not in [t["id"] for t in remaining["threads"]]

        remaining_now = await host.peer.call("thread/remaining", {"thread_id": tid})
        assert remaining_now["lease"]["ceiling"]["max_steps"] < 20


async def test_a_thread_resumes_over_the_wire_and_keeps_its_turns(tmp_path: Path) -> None:
    threads = _host(tmp_path)
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        started = await host.peer.call(
            "thread/start", {"root": str(tmp_path), "mode": "workspace-write"}
        )
        tid = started["thread_id"]
        with anyio.fail_after(30):
            await host.peer.call("turn/start", {"thread_id": tid, "text": "first"})
        await host.peer.call("thread/close", {"thread_id": tid})

        resumed = await host.peer.call("thread/resume", {"thread_id": tid})
        assert resumed["thread_id"] == tid
        with anyio.fail_after(30):
            await host.peer.call("turn/start", {"thread_id": tid, "text": "second"})
        listed = await host.peer.call("thread/list", {})
    assert [t["prompt"] for t in listed["threads"][0]["turns"]] == ["first", "second"]
    assert cast(Any, threads).agent.opened == 2, "resume reopened the provider"


async def test_steer_and_interrupt_cross(tmp_path: Path) -> None:
    threads = _host(tmp_path)
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        started = await host.peer.call(
            "thread/start", {"root": str(tmp_path), "mode": "workspace-write"}
        )
        tid = started["thread_id"]
        steered = await host.peer.call("turn/steer", {"thread_id": tid, "text": "and also…"})
        assert steered["taken"] in ("now", "next"), steered
        stopped = await host.peer.call("turn/interrupt", {"thread_id": tid})
        assert stopped["interrupted"] is False, "nothing was running to interrupt"


async def test_an_unknown_thread_is_an_error_not_a_crash(tmp_path: Path) -> None:
    async with loopback(threads=_host(tmp_path)) as (host, _runtime):
        await host.initialize()
        with pytest.raises(Exception, match="no thread"):
            await host.peer.call("turn/start", {"thread_id": "nobody", "text": "?"})


async def test_without_a_thread_host_the_methods_say_so(tmp_path: Path) -> None:
    async with loopback() as (host, _runtime):
        await host.initialize()
        with pytest.raises(Exception, match="no thread host"):
            await host.peer.call("thread/start", {"root": str(tmp_path), "mode": "workspace-write"})


def _keeper(into: list[tuple[str, dict[str, Any]]], kind: str) -> Any:
    async def keep(params: dict[str, Any]) -> None:
        into.append((kind, params))

    return keep
