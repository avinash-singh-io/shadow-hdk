"""A host can stop a run, and the record says who asked (D15).

`Cancelled` and `EndReason("cancelled")` have existed since Phase 0 with nothing raising either.
The question was never whether a run can be stopped but **who asks and where**. A run already stops
for reasons of one shape — the executor asks, before spending a step, whether it may — so
cancellation is asked in that same place, first, before the lease.
"""

from __future__ import annotations

from pydantic import JsonValue

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    Ended,
    Event,
    Floor,
    Invoke,
    Lease,
    Observation,
)
from shadow_hdk.runtime import Cancellation, RunOptions, current_run, run
from shadow_hdk.runtime.testing import make_registration
from tests.runtime.conftest import ports_over

FIRST = make_registration("first")
SECOND = make_registration("second")
SPAWNER = make_registration("spawner", labels=frozenset({"agent"}))
CHILD_WORK = make_registration("child_work")


def a_lease(steps: int = 20) -> Lease:
    return Lease(Ceiling(steps, 3600, 1000), Floor(0))


def _ended(events: list[Event]) -> Ended:
    last = events[-1]
    assert isinstance(last, Ended), f"a run ends with Ended, not {last.kind}"
    return last


def _ran(events: list[Event]) -> list[str]:
    return [e.step for e in events if e.kind == "invoked"]


async def test_a_run_cancelled_before_it_starts_takes_no_step() -> None:
    stop = Cancellation()
    stop.cancel("the user closed the tab")
    ports, _ = ports_over([(FIRST, "one"), (SECOND, "two")])
    events = [
        e
        async for e in run(
            Composition((Invoke("s1", FIRST.id), Invoke("s2", SECOND.id))),
            ports,
            options=RunOptions(lease=a_lease(), cancellation=stop),
        )
    ]
    assert _ran(events) == [], "a cancelled run spent a step"
    assert _ended(events).reason == "cancelled"
    # Not merely un-invoked: un-charged. The check is above the meter, so the step is never bought.
    assert _ended(events).steps_taken == 0


async def test_a_run_cancelled_between_two_steps_does_not_take_the_second() -> None:
    stop = Cancellation()

    async def cancel_after_me(_inputs: JsonValue) -> Observation:
        stop.cancel("enough")
        return Completed("one")

    ports, _ = ports_over([(FIRST, cancel_after_me), (SECOND, "two")])
    events = [
        e
        async for e in run(
            Composition((Invoke("s1", FIRST.id), Invoke("s2", SECOND.id))),
            ports,
            options=RunOptions(lease=a_lease(), cancellation=stop),
        )
    ]
    assert _ran(events) == ["s1"], "the step after the cancellation ran"
    assert _ended(events).reason == "cancelled"


async def test_the_reason_the_host_gave_is_on_the_record() -> None:
    stop = Cancellation()
    stop.cancel("the user closed the tab")
    ports, _ = ports_over([(FIRST, "one")])
    events = [
        e
        async for e in run(
            Composition((Invoke("s1", FIRST.id),)),
            ports,
            options=RunOptions(lease=a_lease(), cancellation=stop),
        )
    ]
    assert "the user closed the tab" in (_ended(events).detail or "")


async def test_cancelling_a_parent_stops_its_child() -> None:
    """A child that outlived the run that spawned it is a leak with a budget."""
    stop = Cancellation()
    seen: list[list[Event]] = []

    async def spawn_a_child(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        stop.cancel("the parent was told to stop")
        child = Composition((Invoke("c1", CHILD_WORK.id),))
        seen.append(
            [
                e
                async for e in run(
                    child, context.ports, options=context.spawn_options(Ceiling(5, 600, 100))
                )
            ]
        )
        return Completed("spawned")

    ports, _ = ports_over([(SPAWNER, spawn_a_child), (CHILD_WORK, "child did it")])
    [
        e
        async for e in run(
            Composition((Invoke("s1", SPAWNER.id),)),
            ports,
            options=RunOptions(lease=a_lease(), cancellation=stop),
        )
    ]
    assert seen, "the spawner never ran"
    assert _ran(seen[0]) == [], "the child took a step after its parent was cancelled"
    assert _ended(seen[0]).reason == "cancelled"


async def test_a_child_holding_its_own_handle_survives_the_parents() -> None:
    """Inheritance is a default, not a rule. A child handed its own handle is its own to stop."""
    parents_stop = Cancellation()
    seen: list[list[Event]] = []

    async def spawn_a_child(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        parents_stop.cancel("the parent was told to stop")
        child = Composition((Invoke("c1", CHILD_WORK.id),))
        options = context.spawn_options(Ceiling(5, 600, 100), cancellation=Cancellation())
        seen.append([e async for e in run(child, context.ports, options=options)])
        return Completed("spawned")

    ports, _ = ports_over([(SPAWNER, spawn_a_child), (CHILD_WORK, "child did it")])
    [
        e
        async for e in run(
            Composition((Invoke("s1", SPAWNER.id),)),
            ports,
            options=RunOptions(lease=a_lease(), cancellation=parents_stop),
        )
    ]
    assert seen, "the spawner never ran"
    assert _ran(seen[0]) == ["c1"], "a child with its own handle was stopped by its parent's"
    assert _ended(seen[0]).reason == "completed"


async def test_the_first_reason_is_the_one_recorded() -> None:
    """Idempotent on purpose. A second asker does not get to rewrite why the run stopped."""
    stop = Cancellation()
    stop.cancel("the user closed the tab")
    stop.cancel("the budget ran out")
    ports, _ = ports_over([(FIRST, "one")])
    events = [
        e
        async for e in run(
            Composition((Invoke("s1", FIRST.id),)),
            ports,
            options=RunOptions(lease=a_lease(), cancellation=stop),
        )
    ]
    assert "the user closed the tab" in (_ended(events).detail or "")
