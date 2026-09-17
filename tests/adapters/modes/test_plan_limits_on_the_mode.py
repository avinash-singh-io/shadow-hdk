"""D109: how much plan a mode admits is data on the mode — parsed from a document, shipped with
defaults that narrow from `full` down to `read-only`, narrowing-only for a team's mode, and read
by the thread at every turn so a mode switch changes the limits live.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.adapters.modes.registry import (
    ModeRegistry,
    ModeSpec,
    mode_from_document,
    shipped_modes,
)
from shadow_hdk.kernel import Ceiling, Floor, Lease, PlanLimits
from shadow_hdk.kernel.events import PlanAdmitted, PlanRefused
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.planning import plan_components
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink, make_registration
from shadow_hdk.runtime.threads import InMemoryThreads, Thread
from shadow_hdk.testing import ScriptedAgent

pytestmark = pytest.mark.anyio


def a_mode(**plan: int) -> dict[str, Any]:
    return {"id": "tight", "policy": "ask", "plan": plan}


# ---------------------------------------------------------------- a document


def test_a_mode_document_carries_its_plan_limits() -> None:
    spec = mode_from_document(a_mode(depth=2, fan_out=3, steps=10), source="store")
    assert spec.plan == PlanLimits(depth=2, fan_out=3, steps=10)


def test_a_document_without_plan_limits_defers_to_its_policys_shipped_default() -> None:
    spec = mode_from_document({"id": "mine", "policy": "read-only"}, source="store")
    shipped = next(m for m in shipped_modes() if m.id == "read-only")
    assert spec.plan == shipped.plan, "the shipped policy's limits, not unbounded"


@pytest.mark.parametrize(
    "plan, why",
    [
        ({"depth": 0}, "at least 1"),
        ({"fan_out": -2}, "at least 1"),
        ({"steps": "many"}, "integer"),
        ({"width": 3}, "unknown plan field"),
        ("wide", "table"),
    ],
)
def test_a_malformed_plan_table_is_refused_by_name(plan: Any, why: str) -> None:
    with pytest.raises(ValueError, match=why):
        mode_from_document({"id": "bad", "policy": "ask", "plan": plan}, source="store")


# ---------------------------------------------------------------- the shipped four


def test_the_shipped_modes_carry_limits_that_narrow_from_full_to_read_only() -> None:
    plans: dict[str, PlanLimits] = {}
    for mode in shipped_modes():
        assert mode.plan is not None, f"{mode.id} ships no plan limits"
        assert all(v is not None for v in (mode.plan.depth, mode.plan.fan_out, mode.plan.steps))
        plans[mode.id] = mode.plan
    assert plans["read-only"].narrower_than(plans["ask"])
    assert plans["ask"].narrower_than(plans["workspace-write"])
    assert plans["workspace-write"].narrower_than(plans["full"])


# ---------------------------------------------------------------- narrowing only


def test_a_teams_mode_may_only_narrow_the_limits_of_the_policy_it_names() -> None:
    """A document narrows the policy it names, never widens it (D109; D24 for rule files): the
    check names the axis, and the parser refuses the document by name."""
    from shadow_hdk.adapters.modes.check import widens_plan

    shipped = next(m for m in shipped_modes() if m.id == "ask")
    assert shipped.plan is not None and shipped.plan.fan_out is not None
    narrower = mode_from_document(
        {"id": "t", "policy": "ask", "plan": {"depth": 1, "fan_out": 2, "steps": 4}}, source="s"
    )
    assert widens_plan(narrower.plan, shipped.plan) == []
    found = widens_plan(PlanLimits(fan_out=shipped.plan.fan_out + 1), shipped.plan)
    assert [w.field for w in found] == ["depth", "fan_out", "steps"], "unset axes are unbounded"
    with pytest.raises(ValueError, match="widens policy 'ask'"):
        mode_from_document(
            {"id": "t", "policy": "ask", "plan": {"fan_out": shipped.plan.fan_out + 1}},
            source="s",
        )


def test_an_unbounded_axis_widens_a_bounded_house() -> None:
    from shadow_hdk.adapters.modes.check import widens_plan

    found = widens_plan(PlanLimits(fan_out=2), PlanLimits(depth=2, fan_out=4, steps=8))
    assert [w.field for w in found] == ["depth", "steps"], "None is wider than any bound"


# ---------------------------------------------------------------- live, on a thread

LOOK = make_registration("look")


async def look(_inputs: Any) -> Any:
    from shadow_hdk.kernel import Completed

    return Completed({"found": True})


def a_plan(width: int) -> dict[str, Any]:
    return {
        "steps": [
            {
                "kind": "fan_out",
                "id": "f",
                "steps": [
                    {"kind": "invoke", "id": f"s{i}", "component": "look", "inputs": []}
                    for i in range(width)
                ],
            }
        ]
    }


def _ports() -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(LOOK, look)]), plan_components()),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


async def test_a_turn_runs_under_its_modes_limits_and_a_switch_changes_them_live(
    tmp_path: Path,
) -> None:
    """The mode's limits reach admission at every turn, met with the host's; `set_mode` to a
    wider mode admits at the next turn what the tighter one refused."""
    tight = ModeSpec.of("tight", plan=PlanLimits(fan_out=2))
    wide = ModeSpec.of("wide", plan=PlanLimits(fan_out=8))
    modes = ModeRegistry((tight, wide))
    agent = ScriptedAgent([([("compose", a_plan(3))], "one"), ([("compose", a_plan(3))], "two")])
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(60, 600, None), Floor(0)),
        modes=modes,
        mode="tight",
    )
    agent.reach = thread.registry.call
    try:
        first = [e async for e in thread.turn("plan three")]
        await thread.set_mode("wide")
        second = [e async for e in thread.turn("plan three again")]
    finally:
        await thread.close()
    refused = [e for e in first if isinstance(e, PlanRefused)]
    assert refused and [(m.axis, m.required, m.found) for m in refused[-1].mismatches] == [
        ("fan_out", "2", "3")
    ]
    admitted = [e for e in second if isinstance(e, PlanAdmitted)]
    assert admitted and admitted[-1].limits.fan_out == 8


async def test_the_hosts_limits_and_the_modes_meet(tmp_path: Path) -> None:
    wide = ModeSpec.of("wide", plan=PlanLimits(fan_out=8))
    agent = ScriptedAgent([([("compose", a_plan(3))], "one")])
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(60, 600, None), Floor(0)),
        modes=ModeRegistry((wide,)),
        mode="wide",
        plan_limits=PlanLimits(fan_out=2),
    )
    agent.reach = thread.registry.call
    try:
        events = [e async for e in thread.turn("plan three")]
    finally:
        await thread.close()
    refused = [e for e in events if isinstance(e, PlanRefused)]
    assert refused and refused[-1].mismatches[0].required == "2", "the host's 2 met the mode's 8"
