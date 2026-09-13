"""The derivation engine as a component that proposes its ground (D26, `09` §5).

*A derivation engine is a component.* So it is reached the way anything else is — a step in a
composition, judged by governance, observed on the record — and what it hands back is not a
number but a **claim**: the value, its unit, the ground that produced it, and the fingerprint that
is that ground's identity. The same thing goes to the sink as a proposal, because a number nobody
can re-derive is not a fact the record should hold.

*No containment needed.* It is a pure function over data, so its effect profile is the narrowest
there is, and a mode that allows nothing else still lets it run.
"""

from __future__ import annotations

from pydantic import JsonValue
from shadow_hdk.adapters.basic import AllowAll

from shadow_hdk.adapters.derivation import DerivationComponents, parse, to_tree
from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Composition,
    EffectProfile,
    Event,
    Floor,
    Invoke,
    Lease,
    Observed,
)
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

OK: JsonValue = {"status": "ok"}
DEFECTIVE: JsonValue = {"status": "defective"}
ROWS: list[JsonValue] = [OK] * 1839 + [DEFECTIVE] * 3
LOT: JsonValue = {"columns": {"status": "text"}, "units": {}, "row_unit": "unit", "rows": ROWS}
RATE: JsonValue = {
    "percent": {"div": [{"count_where": {"col": "status", "eq": "defective"}}, {"count": "*"}]}
}


async def _derive(ground: JsonValue, table: JsonValue = LOT) -> tuple[list[Event], ListSink]:
    sink = ListSink()
    ports = Ports(
        model=ScriptedModel(),
        components=(DerivationComponents(),),
        governance=AllowAll(),
        sink=sink,
        clock=FixedClock(),
    )
    events = [
        e
        async for e in run(
            Composition(
                (
                    Invoke(
                        "d1",
                        "derive",
                        (Binding(name="table", value=table), Binding(name="ground", value=ground)),
                    ),
                )
            ),
            ports,
            options=RunOptions(lease=Lease(Ceiling(10, 600, 100), Floor(0))),
        )
    ]
    return events, sink


async def test_the_engine_answers_with_a_claim_not_a_number() -> None:
    events, _ = await _derive(RATE)
    observed = [e for e in events if isinstance(e, Observed) and e.step == "d1"]
    assert observed, "the derivation was never observed"
    out = observed[-1].observation
    assert out.kind == "completed", out
    payload = out.output
    assert isinstance(payload, dict)
    assert payload["value"] == "0.162866449511"
    assert payload["unit"] == "%"
    assert payload["ground"] == RATE, "the ground has to travel with the number"
    assert isinstance(payload["fingerprint"], str) and len(payload["fingerprint"]) == 64


async def test_the_claim_reaches_the_sink_as_a_proposal_with_its_ground() -> None:
    """Record through the sink (`09` principle 3). The runtime writes nothing; the host decides."""
    _, sink = await _derive(RATE)
    proposals = [p for p in sink.proposals if p.kind == "derivation"]
    assert len(proposals) == 1
    payload = proposals[0].payload
    assert isinstance(payload, dict)
    assert payload["ground"] == RATE
    assert payload["value"] == "0.162866449511"
    assert proposals[0].provenance.adapter == "derivation"


async def test_an_indeterminate_is_a_claim_too_and_says_why() -> None:
    """A comparison that can answer indeterminate is R8's requirement; so the record holds the
    indeterminate with its reason, not a missing row."""
    empty: JsonValue = {"columns": {"status": "text"}, "units": {}, "row_unit": "unit", "rows": []}
    events, sink = await _derive(RATE, empty)
    out = [e for e in events if isinstance(e, Observed)][-1].observation
    assert out.kind == "completed"
    assert isinstance(out.output, dict)
    assert out.output["value"] is None
    why = out.output["indeterminate"]
    assert isinstance(why, dict) and why["reason"] == "division_by_zero"
    assert isinstance(why["detail"], str) and why["detail"]
    proposed = sink.proposals[0].payload
    assert isinstance(proposed, dict)
    also_why = proposed["indeterminate"]
    assert isinstance(also_why, dict) and also_why["reason"] == "division_by_zero"


async def test_a_malformed_ground_is_the_authors_error_and_proposes_nothing() -> None:
    """D7: a bad input is a `Failed` observation the model can read. And nothing reaches the sink,
    because a claim that could not even be parsed is not a claim."""
    events, sink = await _derive({"eval": "1+1"})
    out = [e for e in events if isinstance(e, Observed)][-1].observation
    assert out.kind == "failed"
    assert "eval" in out.error
    assert sink.proposals == []


async def test_it_needs_no_containment_and_no_permission_beyond_existing() -> None:
    """The narrowest mode there is still runs it, because it reads, writes and reaches nothing."""
    from shadow_hdk.adapters.modes import Rule, RuleGovernance, RuleSet

    nothing = RuleSet((Rule(name="nothing", ceiling=EffectProfile()),))
    sink = ListSink()
    ports = Ports(
        model=ScriptedModel(),
        components=(DerivationComponents(),),
        governance=RuleGovernance(nothing),
        sink=sink,
        clock=FixedClock(),
    )
    events = [
        e
        async for e in run(
            Composition(
                (
                    Invoke(
                        "d1",
                        "derive",
                        (Binding(name="table", value=LOT), Binding(name="ground", value=RATE)),
                    ),
                )
            ),
            ports,
            options=RunOptions(lease=Lease(Ceiling(10, 600, 100), Floor(0))),
        )
    ]
    assert not [e for e in events if e.kind == "refused"], "a pure derivation was refused"
    assert [e for e in events if isinstance(e, Observed)][-1].observation.kind == "completed"


async def test_a_comparison_through_the_component_is_a_verdict_with_its_ground() -> None:
    """The `cmp` path, which nothing above reaches: the value is a boolean, not a string of one."""
    against: JsonValue = {"cmp": [RATE, "gt", {"lit": "0.05", "unit": "%"}]}
    events, sink = await _derive(against)
    out = [e for e in events if isinstance(e, Observed)][-1].observation
    assert out.kind == "completed" and isinstance(out.output, dict)
    assert out.output["value"] is True
    # The **canonical** ground, not the caller's spelling. A claim records what it derived from in
    # one form, so that two callers who wrote the same comparison differently record one thing
    # (BUG-013); the literal below is `"0.05"` as written and twelve places as recorded.
    assert out.output["ground"] == to_tree(parse(against))
    proposed = sink.proposals[0].payload
    assert isinstance(proposed, dict) and proposed["value"] is True
