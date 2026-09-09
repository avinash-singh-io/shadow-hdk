"""A run started inside a step is a child (D2) — carved, announced, and streamed through its parent.

No label, no port, no branch in the runtime: a sub-agent is a component like any other, and what
makes its run a *child* is only that it began while a step was executing.
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
    Proposal,
    Provenance,
)
from shadow_hdk.runtime import RunOptions, current_run, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, make_registration
from tests.runtime.conftest import ports_over

CHILD_WORK = make_registration("child_work")
PARENT_AGENT = make_registration("agent", labels=frozenset({"agent"}))


def _ended(events: list[Event]) -> Ended:
    last = events[-1]
    assert isinstance(last, Ended), f"a finished run ends with Ended, not {last.kind}"
    return last


def a_lease(steps: int = 20, cost: int = 1000) -> Lease:
    return Lease(Ceiling(steps, 3600, cost), Floor(0))


async def _run_child(_inputs: JsonValue) -> Observation:
    """What a sub-agent component does: start a run of its own."""
    ctx = current_run()
    assert ctx is not None, "a component runs inside a run"
    child = Composition((Invoke("c1", CHILD_WORK.id),))
    seen = [
        event
        async for event in run(child, ctx.ports, options=ctx.spawn_options(Ceiling(5, 600, 100)))
    ]
    return Completed({"child_events": len(seen)})


async def test_a_run_started_inside_a_step_is_a_child() -> None:
    ports, _ = ports_over([(PARENT_AGENT, _run_child), (CHILD_WORK, "done")], clock=FixedClock())
    events = [
        e
        async for e in run(
            Composition((Invoke("p1", PARENT_AGENT.id),)),
            ports,
            options=RunOptions(lease=a_lease()),
        )
    ]
    kinds = [e.kind for e in events]
    assert "spawned" in kinds
    spawned = next(e for e in events if e.kind == "spawned")
    started = [e for e in events if e.kind == "started"]
    child_started = next(e for e in started if e.parent_run_id is not None)
    assert child_started.run_id == spawned.child_run_id
    assert child_started.parent_run_id == events[0].run_id


async def test_a_child_s_events_arrive_in_the_parent_s_stream() -> None:
    ports, _ = ports_over([(PARENT_AGENT, _run_child), (CHILD_WORK, "done")], clock=FixedClock())
    events = [
        e
        async for e in run(
            Composition((Invoke("p1", PARENT_AGENT.id),)),
            ports,
            options=RunOptions(lease=a_lease()),
        )
    ]
    parent_id = events[0].run_id
    child_ids = {e.run_id for e in events} - {parent_id}
    assert len(child_ids) == 1
    child_events = [e for e in events if e.run_id in child_ids]
    assert [e.seq for e in child_events] == sorted(e.seq for e in child_events)
    assert [e.kind for e in child_events][0] == "started"
    assert [e.kind for e in child_events][-1] == "ended"


async def test_a_child_is_carved_from_what_the_parent_has_left() -> None:
    seen: list[int] = []

    async def note_and_spawn(inputs: JsonValue) -> Observation:
        ctx = current_run()
        assert ctx is not None
        seen.append(ctx.remaining().ceiling.max_steps)
        return await _run_child(inputs)

    ports, _ = ports_over([(PARENT_AGENT, note_and_spawn), (CHILD_WORK, "done")])
    events = [
        e
        async for e in run(
            Composition((Invoke("p1", PARENT_AGENT.id),)),
            ports,
            options=RunOptions(lease=a_lease(steps=20)),
        )
    ]
    child_started = next(e for e in events if e.kind == "started" and e.parent_run_id)
    assert child_started.lease.ceiling.max_steps == 5
    assert child_started.lease.ceiling.max_steps < seen[0]


async def test_a_child_s_proposal_reaches_the_sink_with_the_child_s_run() -> None:
    sink = ListSink()

    async def propose_something(_inputs: JsonValue) -> Observation:
        ctx = current_run()
        assert ctx is not None
        await ctx.propose(
            Proposal(
                kind="claim",
                payload={"text": "3 of 1842"},
                provenance=Provenance(registered_by=ctx.run_id, adapter="test", at=ctx.now()),
            )
        )
        return Completed(None)

    async def spawn_a_proposer(_inputs: JsonValue) -> Observation:
        ctx = current_run()
        assert ctx is not None
        child = Composition((Invoke("c1", CHILD_WORK.id),))
        async for _ in run(child, ctx.ports, options=ctx.spawn_options(Ceiling(5, 600, 100))):
            pass
        return Completed(None)

    ports, _ = ports_over(
        [(PARENT_AGENT, spawn_a_proposer), (CHILD_WORK, propose_something)], sink=sink
    )
    events = [
        e
        async for e in run(
            Composition((Invoke("p1", PARENT_AGENT.id),)),
            ports,
            options=RunOptions(lease=a_lease()),
        )
    ]
    parent_id = events[0].run_id
    assert len(sink.proposals) == 1
    assert sink.proposals[0].provenance.registered_by != parent_id
    proposed = next(e for e in events if e.kind == "proposed")
    assert proposed.run_id != parent_id


async def test_an_explicit_root_is_not_a_child_even_inside_a_step() -> None:
    async def spawn_a_root(_inputs: JsonValue) -> Observation:
        ctx = current_run()
        assert ctx is not None
        child = Composition((Invoke("c1", CHILD_WORK.id),))
        seen = [
            e
            async for e in run(child, ctx.ports, options=RunOptions(lease=a_lease(5), parent=None))
        ]
        return Completed({"n": len(seen)})

    ports, _ = ports_over([(PARENT_AGENT, spawn_a_root), (CHILD_WORK, "done")])
    events = [
        e
        async for e in run(
            Composition((Invoke("p1", PARENT_AGENT.id),)),
            ports,
            options=RunOptions(lease=a_lease()),
        )
    ]
    assert not [e for e in events if e.kind == "spawned"]
    assert all(getattr(e, "parent_run_id", None) is None for e in events if e.kind == "started")


async def test_a_run_that_spends_its_ceiling_ends_saying_so() -> None:
    reg = make_registration("step")
    steps = tuple(Invoke(f"s{i}", reg.id) for i in range(6))
    from shadow_hdk.kernel import Sequence

    ports, _ = ports_over([(reg, "ok")])
    events = [
        e
        async for e in run(
            Composition((Sequence("seq", steps),)),
            ports,
            options=RunOptions(lease=Lease(Ceiling(3, 3600, 100), Floor(0))),
        )
    ]
    ended = _ended(events)
    assert ended.reason == "lease_exhausted"
    assert ended.steps_taken == 3


async def test_a_plain_run_inside_a_step_becomes_a_child_without_being_told() -> None:
    """D2's actual claim. Every other test here reaches a child through `spawn_options`, which
    names the parent; this one starts a run the way any component naively would — no parent
    argument at all — and it must still be carved, announced and forwarded."""

    async def spawn_naively(_inputs: JsonValue) -> Observation:
        child = Composition((Invoke("c1", CHILD_WORK.id),))
        ports_here = current_run().ports  # type: ignore[union-attr]
        async for _ in run(child, ports_here, options=RunOptions(lease=a_lease(5))):
            pass
        return Completed(None)

    ports, _ = ports_over([(PARENT_AGENT, spawn_naively), (CHILD_WORK, "done")])
    events = [
        e
        async for e in run(
            Composition((Invoke("p1", PARENT_AGENT.id),)),
            ports,
            options=RunOptions(lease=a_lease()),
        )
    ]
    assert [e.kind for e in events if e.kind == "spawned"] == ["spawned"]
    child_started = next(e for e in events if e.kind == "started" and e.parent_run_id)
    assert child_started.parent_run_id == events[0].run_id


async def test_children_in_a_row_do_not_drain_the_parent_with_reservations() -> None:
    """The end-to-end of the same rule: three children, each asking five steps and spending one.

    Before the reservation was settled this drained fifteen of the parent's twenty steps and the
    fourth child could not be carved at all — which is exactly what an agent's turn loop does.
    """
    remaining_seen: list[int] = []

    async def spawn_three(_inputs: JsonValue) -> Observation:
        ctx = current_run()
        assert ctx is not None
        for _ in range(3):
            child = Composition((Invoke("c1", CHILD_WORK.id),))
            async for _e in run(child, ctx.ports, options=ctx.spawn_options(Ceiling(5, 600, 100))):
                pass
            remaining_seen.append(ctx.remaining().ceiling.max_steps)
        return Completed(None)

    ports, _ = ports_over([(PARENT_AGENT, spawn_three), (CHILD_WORK, "done")])
    events = [
        e
        async for e in run(
            Composition((Invoke("p1", PARENT_AGENT.id),)),
            ports,
            options=RunOptions(lease=a_lease(steps=20)),
        )
    ]
    # 20 - 1 (the parent's own step, counted when it began) - 1 per child that spent one.
    # Before settle existed this read [14, 9, 4] and the fourth child could not be carved.
    assert remaining_seen == [18, 17, 16]
    assert _ended(events).reason == "completed"
