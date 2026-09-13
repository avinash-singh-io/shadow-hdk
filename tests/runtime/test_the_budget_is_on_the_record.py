"""The budget on the record (Phase 29 group 5, D84; closes ENH-013).

A thread may be opened with a budget of its own — steps, seconds, cents — over the host's
default, and what it spent is on its record after every turn: a resumed thread starts from what
it spent, not from a fresh meter, so `remaining` is `budget − spent` however many times the page
reloads. Measured before this: `thread/remaining` read `400 steps · 500 ¢` after a turn had taken
it to `399 · 492` and the page reloaded onto the same thread.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.kernel import Ceiling, Completed, EffectProfile, Floor, Lease, ScopeSet, Turn
from shadow_hdk.kernel.ports import AgentSession, Allow, Context, Judgement, ToolSource
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink, make_registration
from shadow_hdk.runtime.threads import InMemoryThreads, Thread

pytestmark = pytest.mark.anyio

LOOK = make_registration("look", effects=EffectProfile(reads=ScopeSet.of("workspace")))


class _AllowAll:
    async def judge(self, _effects: EffectProfile, _context: Context) -> Judgement:
        return Allow()


class Agent:
    def __init__(self, calls: int = 1) -> None:
        self.calls = calls
        self.reach: Any = None

    async def open(self, *, tools: tuple[ToolSource, ...] = (), **_: Any) -> AgentSession:
        agent = self

        class _Session:
            async def turn(self, prompt: str) -> Turn:
                for _ in range(agent.calls):
                    await agent.reach("look", {})
                return Turn(text="looked")

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


DEFAULT = Lease(Ceiling(400, 3600, 500), Floor(0))


async def _open(store: InMemoryThreads, tmp_path: Path, **kw: Any) -> tuple[Thread, Agent]:
    agent = Agent()
    thread = await Thread.open(
        agent=cast(Any, agent), ports=_ports(), store=store, root=tmp_path, lease=DEFAULT, **kw
    )
    agent.reach = thread.registry.call
    return thread, agent


async def test_a_thread_may_be_opened_with_its_own_budget(tmp_path: Path) -> None:
    store = InMemoryThreads()
    thread, _ = await _open(store, tmp_path, budget=Ceiling(10, 60, 5))
    try:
        assert thread.record.budget == Ceiling(10, 60, 5)
        assert thread.remaining().ceiling.max_steps == 10
        assert thread.remaining().ceiling.max_cost_cents == 5
        default, _ = await _open(store, tmp_path)
        try:
            assert default.record.budget is None, "the host's default, not repeated on the record"
            assert default.remaining().ceiling.max_steps == 400
        finally:
            await default.close()
    finally:
        await thread.close()


async def test_what_a_turn_spent_is_on_the_record_and_a_resumed_thread_starts_from_it(
    tmp_path: Path,
) -> None:
    store = InMemoryThreads()
    thread, _ = await _open(store, tmp_path, budget=Ceiling(10, 600, None))
    try:
        [e async for e in thread.turn("look")]
        spent = thread.record.spent
        assert spent.steps >= 2, "the turn's step and the tool's"
        assert thread.remaining().ceiling.max_steps == 10 - spent.steps
        kept = await store.get(thread.id)
        assert kept is not None and kept.spent == spent, "on the store, not only in memory"
    finally:
        await thread.close()

    agent = Agent()
    resumed = await Thread.resume(
        thread.id, agent=cast(Any, agent), ports=_ports(), store=store, lease=DEFAULT
    )
    agent.reach = resumed.registry.call
    try:
        assert resumed.remaining().ceiling.max_steps == 10 - spent.steps, "not a fresh meter"
        [e async for e in resumed.turn("again")]
        assert resumed.record.spent.steps > spent.steps
        assert resumed.remaining().ceiling.max_steps == 10 - resumed.record.spent.steps
    finally:
        await resumed.close()


async def test_a_thread_out_of_budget_stays_out_after_a_resume(tmp_path: Path) -> None:
    store = InMemoryThreads()
    thread, _ = await _open(store, tmp_path, budget=Ceiling(2, 600, None))
    try:
        [e async for e in thread.turn("look")]
        assert thread.remaining().ceiling.max_steps == 0
    finally:
        await thread.close()
    agent = Agent()
    resumed = await Thread.resume(
        thread.id, agent=cast(Any, agent), ports=_ports(), store=store, lease=DEFAULT
    )
    try:
        with pytest.raises(RuntimeError, match="no steps left"):
            [e async for e in resumed.turn("more")]
    finally:
        await resumed.close()
