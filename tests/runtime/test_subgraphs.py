"""A nested composite is a subgraph with a name of its own.

Phase 0 inlined them: more nodes and edges in one flat graph, which ran correctly and left the
runtime unable to say *where* anything happened. A subgraph gives the scope a name — which is what
a checkpoint namespace is, and what Phase 7's branch-level cancel will need something to point at.

The discriminating test is structural: after this, the inner composite's children are **not** nodes
of the root graph. Everything else here would pass under inlining too, and is a regression guard.
"""

from __future__ import annotations

from shadow_hdk.kernel import (
    Allow,
    Ask,
    Ceiling,
    Composition,
    Condition,
    Ended,
    Event,
    FanOut,
    Floor,
    Invoke,
    Lease,
    Observed,
    Sequence,
    Until,
)
from shadow_hdk.runtime import RunOptions, run
from shadow_hdk.runtime.compile import plan_for
from shadow_hdk.runtime.testing import Judge, make_registration
from tests.runtime.conftest import ports_over

A = make_registration("a")
B = make_registration("b")
C = make_registration("c")


def a_lease(steps: int = 20) -> Lease:
    return Lease(Ceiling(steps, 3600, 1000), Floor(0))


def _ended(events: list[Event]) -> Ended:
    last = events[-1]
    assert isinstance(last, Ended), f"a run ends with Ended, not {last.kind}"
    return last


NESTED = Composition(
    (
        Invoke("first", A.id),
        Sequence("inner", (Invoke("deep", B.id),)),
        Invoke("last", C.id),
    )
)


def test_a_nested_composite_is_one_node_of_the_root_graph() -> None:
    """The whole point. Under inlining `deep` was a node of the root; now `inner` is, and `deep`
    belongs to `inner`'s own plan."""
    plan = plan_for(NESTED)
    assert set(plan.steps) == {"first", "last"}, (
        "the inner composite's children leaked into the root"
    )
    assert "inner" in plan.subgraphs, "the nested composite did not become a subgraph"
    assert set(plan.subgraphs["inner"].steps) == {"deep"}


async def test_a_nested_composite_still_runs_in_order() -> None:
    """A regression guard: the shape changed, the behaviour must not."""
    ports, _ = ports_over([(A, "one"), (B, "two"), (C, "three")])
    events = [e async for e in run(NESTED, ports, options=RunOptions(lease=a_lease()))]
    assert [e.step for e in events if e.kind == "invoked"] == ["first", "deep", "last"]
    assert _ended(events).reason == "completed"


async def test_what_a_subgraph_observed_reaches_the_parents_record() -> None:
    """State crosses the boundary: the subgraph shares `RunState`, so its observations merge into
    the parent's through the same reducers."""
    ports, _ = ports_over([(A, "one"), (B, "two"), (C, "three")])
    events = [e async for e in run(NESTED, ports, options=RunOptions(lease=a_lease()))]
    seen = {e.step for e in events if isinstance(e, Observed)}
    assert "deep" in seen, "what happened inside the subgraph never reached the parent"


async def test_a_duplicate_step_id_ends_the_run_rather_than_running_the_wrong_graph() -> None:
    """Found while building this: two steps sharing an id silently collapsed into **one node with a
    self-edge**, so a composition an agent authored ran a graph nobody wrote.

    They cannot be scoped apart: `RunState.handles` is one flat dict keyed by step id, and that
    flatness is what lets a `Binding` reach an earlier sibling in an outer scope. So a repeat is an
    error, and it is caught at plan time rather than discovered at runtime.
    """
    twice = Composition((Invoke("s1", A.id), Sequence("inner", (Invoke("s1", B.id),))))
    ports, _ = ports_over([(A, "one"), (B, "two")])
    events = [e async for e in run(twice, ports, options=RunOptions(lease=a_lease()))]
    ended = _ended(events)
    assert ended.reason == "failed"
    assert "s1" in (ended.detail or ""), "the record does not say which id was repeated"


NESTED_FAN = Composition(
    (
        Invoke("before", A.id),
        FanOut("fan", (Invoke("arm0", B.id), Invoke("arm1", C.id))),
        Invoke("after", A.id),
    )
)

NESTED_LOOP = Composition(
    (
        Invoke("before", A.id),
        Until("loop", Invoke("body", B.id), Condition("done", True), max_iterations=3),
    )
)


async def test_a_nested_fanout_still_runs_every_arm() -> None:
    """`Send` addresses a node by name, and the dispatcher now lives inside the subgraph. Both arms
    still run, because the fan-out was moved whole rather than cut in half."""
    ports, _ = ports_over([(A, "one"), (B, "two"), (C, "three")])
    events = [e async for e in run(NESTED_FAN, ports, options=RunOptions(lease=a_lease()))]
    ran = [e.step for e in events if e.kind == "invoked"]
    assert ran[0] == "before"
    assert sorted(ran[1:3]) == ["arm0", "arm1"]
    assert ran[3] == "after"
    assert _ended(events).reason == "completed"


async def test_a_nested_until_loops_inside_its_own_subgraph() -> None:
    """The tick node and the conditional edge went into the subgraph together, so the loop runs
    there and the parent sees one node that took a while."""
    ports, _ = ports_over([(A, "one"), (B, {"done": False})])
    events = [e async for e in run(NESTED_LOOP, ports, options=RunOptions(lease=a_lease()))]
    bodies = [e.step for e in events if e.kind == "invoked" and e.step == "body"]
    assert len(bodies) == 3, "the loop did not run to its ceiling inside the subgraph"
    assert _ended(events).reason == "completed"


async def test_an_ask_inside_a_subgraph_parks_the_whole_run() -> None:
    """An interrupt raised in a nested scope has to reach the top. LangGraph propagates it out of
    the subgraph; what this checks is that our drive still sees the run as parked rather than done.
    """
    ports, _ = ports_over(
        [(A, "one"), (B, "two"), (C, "three")],
        judge=Judge(lambda effects, context: Ask("may it?") if context.step == "deep" else Allow()),
    )
    events = [
        e
        async for e in run(
            NESTED,
            ports,
            options=RunOptions(lease=a_lease(), run_id="parked-in-a-subgraph"),
        )
    ]
    assert [e.kind for e in events if e.kind == "asked"], "the nested Ask never reached the top"
    assert not [e for e in events if isinstance(e, Ended)], "a parked run must not report Ended"
