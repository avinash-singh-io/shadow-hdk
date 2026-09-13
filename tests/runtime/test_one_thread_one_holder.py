"""One thread, one holder (Phase 29 group 2, D81).

A thread is held by the process that opened it — a lease on the thread store, renewed while the
thread is open, released at close, lapsing when the holder dies. A second holder is refused by
name. And a second `turn/start` while one runs is a named choice: `enqueue` (the default: it
waits its turn), `reject` (refused at once), or `interrupt` (the running turn is stopped and this
one starts) — LangGraph Server's double-texting strategies, in the harness's words.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.kernel import Ceiling, Completed, EffectProfile, Floor, Lease, ScopeSet, Turn
from shadow_hdk.kernel.ports import AgentSession, Allow, Context, Judgement, ToolSource
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink, make_registration
from shadow_hdk.runtime.threads import InMemoryThreads, Thread, ThreadHeld, TurnRunning

pytestmark = pytest.mark.anyio

LOOK = make_registration("look", effects=EffectProfile(reads=ScopeSet.of("workspace")))


class _AllowAll:
    async def judge(self, _effects: EffectProfile, _context: Context) -> Judgement:
        return Allow()


class SlowAgent:
    """Each turn waits until it is let go, or is interrupted — so a second turn can arrive while
    the first runs."""

    def __init__(self) -> None:
        self.current: asyncio.Event | None = None
        self.interrupted = 0
        self.turns: list[str] = []

    def release(self) -> None:
        """Let the running turn finish."""
        assert self.current is not None
        self.current.set()

    async def running(self, count: int) -> None:
        """Wait until `count` turns have reached the provider."""
        for _ in range(200):
            if len(self.turns) >= count:
                return
            await asyncio.sleep(0.01)
        raise AssertionError(f"only {self.turns} reached the provider")

    async def open(self, *, tools: tuple[ToolSource, ...] = (), **_: Any) -> AgentSession:
        agent = self

        class _Session:
            async def turn(self, prompt: str) -> Turn:
                mine = asyncio.Event()
                agent.current = mine
                agent.turns.append(prompt)
                await mine.wait()
                return Turn(text="said " + prompt)

            async def interrupt(self) -> bool:
                agent.interrupted += 1
                agent.release()
                return True

            async def steer(self, text: str) -> bool:
                return False

            async def close(self) -> None:
                pass

            async def stream(self, prompt: str) -> AsyncIterator[Any]:  # pragma: no cover
                raise NotImplementedError
                yield

        return cast(AgentSession, _Session())


async def look(_inputs: Any) -> Any:
    return Completed({"found": 1})


def _ports() -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(LOOK, look)]),),
        governance=_AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


def _lease() -> Lease:
    return Lease(Ceiling(40, 600, None), Floor(0))


async def _drain(events: AsyncIterator[Any]) -> list[Any]:
    return [e async for e in events]


# ---------------------------------------------------------------- the hold


async def test_an_open_thread_is_held_by_its_holder_and_let_go_at_close(tmp_path: Path) -> None:
    store = InMemoryThreads()
    thread = await Thread.open(
        agent=cast(Any, SlowAgent()),
        ports=_ports(),
        store=store,
        root=tmp_path,
        lease=_lease(),
        holder="host-a",
    )
    assert await store.held_by(thread.id) == "host-a"
    assert thread.holder == "host-a"
    await thread.close()
    assert await store.held_by(thread.id) is None


async def test_a_second_holder_is_refused_by_name(tmp_path: Path) -> None:
    store = InMemoryThreads()
    thread = await Thread.open(
        agent=cast(Any, SlowAgent()),
        ports=_ports(),
        store=store,
        root=tmp_path,
        lease=_lease(),
        holder="host-a",
    )
    try:
        with pytest.raises(ThreadHeld, match="host-a") as refused:
            await Thread.resume(
                thread.id,
                agent=cast(Any, SlowAgent()),
                ports=_ports(),
                store=store,
                lease=_lease(),
                holder="host-b",
            )
        assert refused.value.holder == "host-a" and refused.value.thread_id == thread.id
        assert await store.held_by(thread.id) == "host-a", "the refusal took nothing"
    finally:
        await thread.close()
    again = await Thread.resume(
        thread.id,
        agent=cast(Any, SlowAgent()),
        ports=_ports(),
        store=store,
        lease=_lease(),
        holder="host-b",
    )
    try:
        assert await store.held_by(thread.id) == "host-b"
    finally:
        await again.close()


async def test_the_hold_is_renewed_while_the_thread_is_open(tmp_path: Path) -> None:
    """A ttl shorter than the test: without renewal the hold would lapse and a second holder
    could take the thread from under a live one."""
    store = InMemoryThreads()
    thread = await Thread.open(
        agent=cast(Any, SlowAgent()),
        ports=_ports(),
        store=store,
        root=tmp_path,
        lease=_lease(),
        holder="host-a",
        hold_seconds=0.3,
    )
    try:
        await asyncio.sleep(0.8)
        assert await store.held_by(thread.id) == "host-a", "renewed, not lapsed"
        with pytest.raises(ThreadHeld):
            await Thread.resume(
                thread.id,
                agent=cast(Any, SlowAgent()),
                ports=_ports(),
                store=store,
                lease=_lease(),
                holder="host-b",
            )
    finally:
        await thread.close()


async def test_a_holder_that_died_lapses_and_the_next_takes_the_thread(tmp_path: Path) -> None:
    store = InMemoryThreads()
    dead = await Thread.open(
        agent=cast(Any, SlowAgent()),
        ports=_ports(),
        store=store,
        root=tmp_path,
        lease=_lease(),
        holder="host-a",
        hold_seconds=0.2,
    )
    assert dead._renewing is not None  # noqa: SLF001 — the process died: nothing renews
    dead._renewing.cancel()  # noqa: SLF001 — and nothing releases
    await asyncio.sleep(0.35)
    assert await store.held_by(dead.id) is None
    taken = await Thread.resume(
        dead.id,
        agent=cast(Any, SlowAgent()),
        ports=_ports(),
        store=store,
        lease=_lease(),
        holder="host-b",
    )
    try:
        assert await store.held_by(dead.id) == "host-b"
    finally:
        await taken.close()
        await dead.close()


async def test_a_thread_without_a_holder_is_not_held(tmp_path: Path) -> None:
    """The in-process shape with nothing to share the store with: no holder, no hold — a test
    double that opens threads without naming itself is not refused by a lease it never took."""
    store = InMemoryThreads()
    thread = await Thread.open(
        agent=cast(Any, SlowAgent()), ports=_ports(), store=store, root=tmp_path, lease=_lease()
    )
    try:
        assert thread.holder == "" and await store.held_by(thread.id) is None
    finally:
        await thread.close()


# ---------------------------------------------------------------- a second turn


async def _open(tmp_path: Path, agent: SlowAgent) -> Thread:
    return await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=_lease(),
        holder="host-a",
    )


async def test_enqueue_is_the_default_and_the_second_turn_waits_its_turn(tmp_path: Path) -> None:
    agent = SlowAgent()
    thread = await _open(tmp_path, agent)
    try:
        first = asyncio.create_task(_drain(thread.turn("one")))
        await agent.running(1)
        second = asyncio.create_task(_drain(thread.turn("two")))
        await asyncio.sleep(0.05)
        assert agent.turns == ["one"], "the second has not started"
        agent.release()
        await asyncio.wait_for(first, 10)
        await agent.running(2)
        agent.release()
        await asyncio.wait_for(second, 10)
        assert [t.outcome for t in thread.record.turns] == ["completed", "completed"]
    finally:
        await thread.close()


async def test_reject_refuses_at_once_while_a_turn_runs(tmp_path: Path) -> None:
    agent = SlowAgent()
    thread = await _open(tmp_path, agent)
    try:
        first = asyncio.create_task(_drain(thread.turn("one")))
        await agent.running(1)
        with pytest.raises(TurnRunning, match="turn-1"):
            await _drain(thread.turn("two", when="reject"))
        agent.release()
        await asyncio.wait_for(first, 10)
        assert [t.id for t in thread.record.turns] == ["turn-1"], "nothing was recorded for it"
        third = asyncio.create_task(_drain(thread.turn("three", when="reject")))  # nothing runs
        await agent.running(2)
        agent.release()
        await asyncio.wait_for(third, 10)
        assert [t.id for t in thread.record.turns] == ["turn-1", "turn-2"]
    finally:
        await thread.close()


async def test_interrupt_stops_the_running_turn_and_starts_this_one(tmp_path: Path) -> None:
    agent = SlowAgent()
    thread = await _open(tmp_path, agent)
    try:
        first = asyncio.create_task(_drain(thread.turn("one")))
        await agent.running(1)
        second = asyncio.create_task(_drain(thread.turn("two", when="interrupt")))
        await asyncio.wait_for(first, 10)
        assert agent.interrupted == 1
        assert thread.record.turns[0].outcome == "cancelled"
        await agent.running(2)
        agent.release()
        await asyncio.wait_for(second, 10)
        assert thread.record.turns[1].outcome == "completed"
    finally:
        await thread.close()


async def test_an_unknown_strategy_is_refused_by_name(tmp_path: Path) -> None:
    thread = await _open(tmp_path, SlowAgent())
    try:
        with pytest.raises(ValueError, match="sometime"):
            await _drain(thread.turn("x", when="sometime"))  # type: ignore[arg-type]
    finally:
        await thread.close()
