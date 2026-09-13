"""Tokens and running time on the record (Phase 30 group 2, D90).

A subscription is *tokens counted, no price*: a thread's record says how many went in and out
across its turns, and says when a call reported none (`unmetered` — unknown, never zero). And
a thread's seconds are its turns' running time: a thread open overnight with one ten-second
turn has spent ten seconds, not the night — D33's rule for a run, held for the thread.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.kernel import Ceiling, Completed, EffectProfile, Floor, Lease, ScopeSet, Turn
from shadow_hdk.kernel.ports import AgentSession, Allow, Context, Judgement, ToolSource, Usage
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink, make_registration
from shadow_hdk.runtime.threads import InMemoryThreads, Thread

pytestmark = pytest.mark.anyio

LOOK = make_registration("look", effects=EffectProfile(reads=ScopeSet.of("workspace")))


class _AllowAll:
    async def judge(self, _effects: EffectProfile, _context: Context) -> Judgement:
        return Allow()


class Agent:
    """A provider whose turns report what they used — or, once, nothing — and take some time
    on the clock they are handed."""

    def __init__(self, clock: FixedClock, turns: list[tuple[Usage | None, float]]) -> None:
        self.clock = clock
        self.turns = list(turns)
        self.reach: Any = None

    async def open(self, *, tools: tuple[ToolSource, ...] = (), **_: Any) -> AgentSession:
        agent = self

        class _Session:
            async def turn(self, prompt: str) -> Turn:
                usage, seconds = agent.turns.pop(0)
                agent.clock.advance(seconds)
                return Turn(text="ok", usage=usage)

            async def close(self) -> None:
                pass

            async def stream(self, prompt: str) -> AsyncIterator[Any]:  # pragma: no cover
                raise NotImplementedError
                yield

        return cast(AgentSession, _Session())


async def look(_inputs: Any) -> Any:
    return Completed({"found": 1})


def _ports(clock: FixedClock) -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(LOOK, look)]),),
        governance=_AllowAll(),
        sink=ListSink(),
        clock=clock,
    )


async def test_tokens_are_on_the_record_and_an_unreported_call_says_so(tmp_path: Path) -> None:
    clock = FixedClock()
    agent = Agent(
        clock,
        [
            (Usage(input_tokens=100, output_tokens=20, cost_cents=None), 1.0),
            (Usage(input_tokens=50, output_tokens=5, cost_cents=None), 1.0),
            (None, 1.0),
        ],
    )
    store = InMemoryThreads()
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(clock),
        store=store,
        root=tmp_path,
        lease=Lease(Ceiling(40, 3600, 500), Floor(0)),
    )
    agent.reach = thread.registry.call
    try:
        [e async for e in thread.turn("one")]
        spent = thread.record.spent
        assert (spent.input_tokens, spent.output_tokens) == (100, 20)
        assert spent.unmetered is False
        assert spent.unpriced is True, "a call that could not be priced: cents is a floor"
        [e async for e in thread.turn("two")]
        assert (thread.record.spent.input_tokens, thread.record.spent.output_tokens) == (150, 25)
        [e async for e in thread.turn("three")]
        after = thread.record.spent
        assert (after.input_tokens, after.output_tokens) == (150, 25), "nothing invented"
        assert after.unmetered is True, "a call that reported nothing: the count is a floor"
        kept = await store.get(thread.id)
        assert kept is not None and kept.spent == after
    finally:
        await thread.close()

    resumed = await Thread.resume(
        thread.id,
        agent=cast(Any, Agent(clock, [(Usage(1, 1, None), 1.0)])),
        ports=_ports(clock),
        store=store,
        lease=Lease(Ceiling(40, 3600, 500), Floor(0)),
    )
    try:
        [e async for e in resumed.turn("four")]
        assert resumed.record.spent.input_tokens == 151, "carried across the opening"
        assert resumed.record.spent.unmetered is True, "and so is the floor"
    finally:
        await resumed.close()


async def test_a_threads_seconds_are_its_turns_running_time_not_its_life(tmp_path: Path) -> None:
    clock = FixedClock()
    agent = Agent(clock, [(None, 10.0), (None, 5.0)])
    store = InMemoryThreads()
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(clock),
        store=store,
        root=tmp_path,
        lease=Lease(Ceiling(40, 3600, None), Floor(0)),
    )
    agent.reach = thread.registry.call
    try:
        clock.advance(1000)  # open, idle: the person is away
        assert thread.remaining().ceiling.max_wall_seconds == 3600, "idle is not spent"
        [e async for e in thread.turn("one")]
        assert thread.record.spent.seconds == pytest.approx(10.0)
        clock.advance(24 * 3600)  # overnight
        assert thread.remaining().ceiling.max_wall_seconds == 3590
        [e async for e in thread.turn("two")]
        assert thread.record.spent.seconds == pytest.approx(15.0)
    finally:
        await thread.close()
    clock.advance(24 * 3600)
    resumed = await Thread.resume(
        thread.id,
        agent=cast(Any, Agent(clock, [(None, 2.0)])),
        ports=_ports(clock),
        store=store,
        lease=Lease(Ceiling(40, 3600, None), Floor(0)),
    )
    try:
        assert resumed.remaining().ceiling.max_wall_seconds == 3585
        [e async for e in resumed.turn("three")]
        assert resumed.record.spent.seconds == pytest.approx(17.0)
    finally:
        await resumed.close()
