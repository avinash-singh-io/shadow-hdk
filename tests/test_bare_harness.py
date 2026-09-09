"""The bare-harness test — the definition of done for *generic* (`09` §1, §11; `10` §5 R0).

A composition runs against a component that arrived from outside, a model, and a sub-agent, governed
by allow-all, with everything written to stdout — **using zero lines of any product's code.** If
this ever needs a product import, the decoupling was a claim rather than a property.

The marker is off. It stays off: `tests/invariants/test_stands_alone.py` fails the build if anything
under `packages/` or `examples/` reaches for a product, and this file fails it if the demo stops
running end to end.
"""

from __future__ import annotations

import io
import json
from typing import Any

from examples.bare import bare_harness

from shadow_hdk.kernel import (
    Completed,
    Composed,
    Ended,
    Event,
    Observed,
    Proposed,
    Spawned,
    Started,
)


async def _run() -> tuple[list[Event], list[dict[str, Any]]]:
    out = io.StringIO()
    events = await bare_harness(out)
    written: list[dict[str, Any]] = [
        json.loads(line) for line in out.getvalue().splitlines() if line.strip()
    ]
    return events, written


async def test_the_bare_harness_runs_with_zero_product_code() -> None:
    events, _ = await _run()
    assert isinstance(events[0], Started)
    assert isinstance(events[-1], Ended)
    assert events[-1].reason == "completed"


async def test_a_component_that_arrived_from_outside_was_invoked() -> None:
    """The MCP-shaped server's tool, with its effects **derived** from annotations rather than
    trusted: read-only, closed-world, and still uncontained and costly, because nothing said
    otherwise."""
    events, _ = await _run()
    looked_up = [e for e in events if isinstance(e, Observed) and e.step in {"t1", "r1"}]
    assert looked_up, "the reference server was never called"
    assert all(isinstance(e.observation, Completed) for e in looked_up)


async def test_the_agent_authored_a_plan_and_the_runtime_ran_it() -> None:
    events, _ = await _run()
    composed = [e for e in events if isinstance(e, Composed)]
    assert len(composed) >= 4, "each turn's plan is on the record"
    assert any(len(e.composition.steps) == 1 for e in composed)


async def test_a_sub_agent_ran_inside_the_lead_s_turn() -> None:
    events, _ = await _run()
    spawned = [e for e in events if isinstance(e, Spawned)]
    assert spawned, "no child run"
    children = {e.child_run_id for e in spawned}
    started = {e.run_id for e in events if isinstance(e, Started) and e.parent_run_id}
    assert children <= started
    assert len({e.run_id for e in events}) >= 4, "the tree is more than one level deep"


async def test_every_child_lease_is_carved_from_its_parent() -> None:
    events, _ = await _run()
    root = next(e for e in events if isinstance(e, Started) and e.parent_run_id is None)
    for started in [e for e in events if isinstance(e, Started) and e.parent_run_id]:
        assert started.lease.ceiling.max_steps <= root.lease.ceiling.max_steps


async def test_a_proposal_left_through_the_sink_and_nothing_else_wrote() -> None:
    """The runtime proposes; it never commits. The only thing that left is a proposal, and it left
    the way everything leaves — through a port the host implements."""
    events, written = await _run()
    proposed = [e for e in events if isinstance(e, Proposed)]
    assert len(proposed) == 1
    assert proposed[0].proposal.kind == "claim"
    claims = [line for line in written if line.get("kind") == "claim"]
    assert claims and claims[0]["payload"]["asset"] == "LATHE-3"


async def test_the_whole_run_is_on_stdout_once_each() -> None:
    events, written = await _run()
    stamped = [(line["run_id"], line["seq"]) for line in written if "seq" in line]
    assert len(stamped) == len(set(stamped)), "an event was written more than once"
    assert stamped == [(e.run_id, e.seq) for e in events]


async def test_it_is_deterministic_enough_to_diff() -> None:
    """Two runs differ only where the system clock and its ids do — which is what a recorded model
    and a fixed clock remove, and what makes the replay differ in `10` §5 R3 cost nothing."""
    first, _ = await _run()
    second, _ = await _run()
    assert [(e.kind, getattr(e, "step", None)) for e in first] == [
        (e.kind, getattr(e, "step", None)) for e in second
    ]
