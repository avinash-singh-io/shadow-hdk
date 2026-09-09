"""The emitter — one monotone stream, stamped by the clock port, with the observer off the path.

D6: `run()` yields events *and* feeds an observer. Both see the same sequence. D11: the observer is
fed from its own queue on its own task and is never awaited on the critical path, so an observer
that blocks or raises cannot slow or fail a step.
"""

from __future__ import annotations

import pytest

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Ended,
    Event,
    Floor,
    Lease,
    Observed,
    Started,
)
from shadow_hdk.runtime.emit import Emitter
from shadow_hdk.runtime.testing import FixedClock, ListObserver

LEASE = Lease(Ceiling(10, 600), Floor(0))


async def drain(emitter: Emitter) -> list[Event]:
    return [event async for event in emitter.stream()]


@pytest.mark.asyncio
async def test_seq_starts_at_zero_and_strictly_increases() -> None:
    emitter = Emitter("run-1", FixedClock(), None)
    await emitter.emit(lambda **k: Started(lease=LEASE, **k))
    for i in range(3):
        step = f"s{i}"
        await emitter.emit(
            lambda step=step, **k: Observed(step=step, observation=Completed(None), **k)
        )
    await emitter.emit(lambda **k: Ended(reason="completed", steps_taken=3, **k))
    emitter.close()
    events = await drain(emitter)
    assert [e.seq for e in events] == [0, 1, 2, 3, 4]
    assert all(e.run_id == "run-1" for e in events)


@pytest.mark.asyncio
async def test_every_stamp_comes_from_the_clock_port() -> None:
    clock = FixedClock(start="2030-01-01T00:00:00+00:00")
    emitter = Emitter("run-1", clock, None)
    first = await emitter.emit(lambda **k: Started(lease=LEASE, **k))
    clock.advance(30)
    second = await emitter.emit(lambda **k: Ended(reason="completed", steps_taken=0, **k))
    assert first.at == "2030-01-01T00:00:00+00:00"
    assert second.at == "2030-01-01T00:00:30+00:00"


@pytest.mark.asyncio
async def test_the_iterator_and_the_observer_see_the_same_sequence() -> None:
    observer = ListObserver()
    emitter = Emitter("run-1", FixedClock(), observer)
    await emitter.emit(lambda **k: Started(lease=LEASE, **k))
    await emitter.emit(lambda **k: Ended(reason="completed", steps_taken=0, **k))
    emitter.close()
    yielded = await drain(emitter)
    await emitter.drained()
    assert [(e.seq, e.kind) for e in yielded] == [(e.seq, e.kind) for e in observer.events]


@pytest.mark.asyncio
async def test_an_observer_that_raises_does_not_fail_a_step_and_is_counted() -> None:
    observer = ListObserver(raises=True)
    emitter = Emitter("run-1", FixedClock(), observer)
    await emitter.emit(lambda **k: Started(lease=LEASE, **k))
    await emitter.emit(lambda **k: Ended(reason="completed", steps_taken=0, **k))
    emitter.close()
    assert len(await drain(emitter)) == 2
    await emitter.drained()
    assert emitter.observer_failures == 2


@pytest.mark.asyncio
async def test_emitting_never_awaits_the_observer() -> None:
    """A never-returning observer must not block the emitter. If emit() awaited the observer,
    this test would hang rather than fail — so it is written with a timeout."""
    import asyncio

    class Blocked(ListObserver):
        async def on(self, event: Event) -> None:
            await asyncio.Event().wait()

    emitter = Emitter("run-1", FixedClock(), Blocked())
    await asyncio.wait_for(emitter.emit(lambda **k: Started(lease=LEASE, **k)), timeout=1.0)
    emitter.close(wait=False)
