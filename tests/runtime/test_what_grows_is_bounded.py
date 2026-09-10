"""What grows with traffic is bounded; what does not is argued (TD-005).

Group 1 set the test this file applies: **does the key set grow with load?** The `TypeAdapter` cache
is unbounded deliberately, because its key is a *type* and a program holds finitely many, created by
module import rather than by traffic. The two here fail that test and one passes it, and each is
treated accordingly rather than uniformly.

**The plan cache grows.** Its key is the full JSON of a composition, and a model authors a new one
on most turns. Measured: 2000 distinct compositions gave 2000 entries, about 6.3 MiB, and nothing is
ever evicted. A plan is pure and cheap to rebuild, so an evicted one costs a rebuild and nothing
else — which is what makes a bound safe here and unsafe for an adapter.

**The observer queue grows.** Measured: a slow observer handled 1 event while 49,999 piled up behind
it. The observer is deliberately off the critical path (D11), so the run must not block on it — the
bound therefore **drops and counts**, the shape TD-002 already chose for the MQTT witness, because
an observer that has fallen 50,000 events behind is not going to catch up and the events it has
missed are better named than hidden.

**The caller's stream does not grow, and must stay unbounded.** It is drained by the `async for` in
the same task that fills it, so a bound there would deadlock the run against itself rather than
protect anything.
"""

from __future__ import annotations

import asyncio

from shadow_hdk.kernel import Ceiling, Composition, Floor, Invoke, Lease, Sequence
from shadow_hdk.kernel.events import Event, Started
from shadow_hdk.runtime.compile import PLAN_CACHE_MAX, plan_cache_stats, plan_for
from shadow_hdk.runtime.emit import OBSERVER_BACKLOG_MAX, Emitter
from shadow_hdk.runtime.testing import FixedClock

LEASE = Lease(Ceiling(10, 600, 100), Floor(0))


def a_composition(n: int) -> Composition:
    return Composition(
        (
            Sequence("s", tuple(Invoke(f"n{i}", "noop") for i in range(4))),
            Invoke(f"unique-{n}", "noop"),
        )
    )


class Slow:
    """An observer that never returns, which is what a wedged exporter looks like from here."""

    def __init__(self) -> None:
        self.seen = 0

    async def on(self, event: Event) -> None:
        self.seen += 1
        await asyncio.sleep(3600)


# ------------------------------------------------------------------ the plan cache


def test_the_plan_cache_stops_growing() -> None:
    """The bug: every distinct composition a model authors was kept for the life of the process."""
    for n in range(PLAN_CACHE_MAX * 2):
        plan_for(a_composition(n))

    assert plan_cache_stats()["size"] <= PLAN_CACHE_MAX


def test_the_shape_in_front_of_you_is_still_cached() -> None:
    """What the cache is *for* (D11): a composition re-authored turn after turn is planned once.
    A bound that evicted the thing being used would trade a leak for a slowdown."""
    plan_for(a_composition(-1))
    before = plan_cache_stats()["hits"]

    for _ in range(20):
        plan_for(a_composition(-1))

    assert plan_cache_stats()["hits"] == before + 20


def test_the_least_recently_used_shape_is_what_goes() -> None:
    """Least recently used, not arbitrary: a shape touched on every turn must survive, and a cache
    evicting the oldest *inserted* would drop the one it is about to need.

    **Two earlier versions of this test could not fail**, and the same mutation survived both.
    The first never crossed the bound, so nothing was evicted under either policy. The second
    crossed it but asserted the **end state** — and the end state is identical, because a shape
    evicted on one turn is re-planned and re-inserted on the next, so it is present either way by
    the time anyone looks.

    What differs is not whether the shape is there at the end; it is **how often it had to be
    rebuilt on the way**. Under least-recently-used it is planned once, ever.
    """
    warm = a_composition(-2)
    plan_for(warm)
    misses_before = plan_cache_stats()["misses"]
    fresh = PLAN_CACHE_MAX * 2

    for n in range(fresh):
        plan_for(a_composition(n + 10_000))
        plan_for(warm)  # touched after every insert, so it is never the least recently used

    assert plan_cache_stats()["evicted"] > 0, "the arrangement failed: the bound was never crossed"
    assert plan_cache_stats()["misses"] - misses_before == fresh, (
        "the shape in constant use was evicted and re-planned "
        f"{plan_cache_stats()['misses'] - misses_before - fresh} times"
    )


def test_what_was_evicted_is_counted() -> None:
    """A cache that silently forgets is one nobody can size. The count is the only way to know the
    bound is being hit rather than merely set."""
    for n in range(PLAN_CACHE_MAX * 2):
        plan_for(a_composition(n + 50_000))

    assert plan_cache_stats()["evicted"] > 0


# ------------------------------------------------------------------ the observer queue


async def test_a_slow_observer_does_not_grow_without_limit() -> None:
    """The bug, measured: one event handled and 49,999 behind it."""
    emitter = Emitter("run-1", FixedClock(), Slow())

    for _ in range(OBSERVER_BACKLOG_MAX * 3):
        await emitter.emit(lambda **k: Started(lease=LEASE, **k))
    await asyncio.sleep(0)

    assert emitter.observer_backlog <= OBSERVER_BACKLOG_MAX


async def test_the_run_is_not_slowed_by_an_observer_that_has_stopped() -> None:
    """D11 says the observer is off the critical path, so *drop* rather than *block*. A bounded
    queue that made the run wait would turn a broken exporter into a broken runtime."""
    emitter = Emitter("run-1", FixedClock(), Slow())

    async def emit_many() -> None:
        for _ in range(OBSERVER_BACKLOG_MAX * 3):
            await emitter.emit(lambda **k: Started(lease=LEASE, **k))

    await asyncio.wait_for(emit_many(), 10.0)


async def test_the_events_an_observer_missed_are_counted() -> None:
    """Named rather than hidden. An observer's record with a hole in it and no count is a record
    that reads as complete — the same shape as a proposal that was not written and not reported."""
    emitter = Emitter("run-1", FixedClock(), Slow())

    for _ in range(OBSERVER_BACKLOG_MAX * 3):
        await emitter.emit(lambda **k: Started(lease=LEASE, **k))
    await asyncio.sleep(0)

    assert emitter.observer_dropped > 0


async def test_the_oldest_is_what_goes() -> None:
    """An observer that has fallen behind is more use with the recent events than the ancient ones,
    and a queue that dropped the *newest* would freeze its record at the moment it filled."""
    emitter = Emitter("run-1", FixedClock(), Slow())

    for _ in range(OBSERVER_BACKLOG_MAX * 2):
        await emitter.emit(lambda **k: Started(lease=LEASE, **k))
    await asyncio.sleep(0)
    held: list[Event] = []
    while not emitter._to_observer.empty():  # noqa: SLF001 — the claim is about which survived
        held.append(emitter._to_observer.get_nowait())  # noqa: SLF001

    assert held, "the arrangement failed: nothing was queued"
    assert held[-1].seq > held[0].seq
    assert held[-1].seq >= OBSERVER_BACKLOG_MAX, "the newest events were the ones dropped"


async def test_a_run_with_no_observer_queues_nothing() -> None:
    """Most runs have none, and the queue is not built for them."""
    emitter = Emitter("run-1", FixedClock(), None)

    for _ in range(100):
        await emitter.emit(lambda **k: Started(lease=LEASE, **k))

    assert emitter.observer_dropped == 0
    assert emitter.observer_backlog == 0


async def test_the_callers_stream_is_not_bounded() -> None:
    """Deliberate, and the reason belongs beside the bound above rather than in a comment: this
    queue is filled and drained by the **same task**, so a bound would deadlock a run against
    itself the moment a step emitted more events than the bound allows."""
    emitter = Emitter("run-1", FixedClock(), None)

    for _ in range(OBSERVER_BACKLOG_MAX * 3):
        await emitter.emit(lambda **k: Started(lease=LEASE, **k))

    assert emitter._stream.qsize() == OBSERVER_BACKLOG_MAX * 3  # noqa: SLF001
