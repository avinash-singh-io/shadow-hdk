"""C: limits stored as data decide whether work actually runs."""

from typing import Any

import pytest

from shadow_hdk.adapters.agent import AgentComponent
from shadow_hdk.adapters.agent.loader import pattern_from
from shadow_hdk.adapters.basic import AllowAll, CallableComponents
from shadow_hdk.kernel import Binding, Ceiling, Composition, EffectProfile, Floor, Invoke, Lease
from shadow_hdk.kernel.planning import PlanLimits
from shadow_hdk.kernel.ports import ModelResponse, ToolCall
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

pytestmark = pytest.mark.anyio

ROW = {"name": "planner", "system": "plan it", "meta_tools": ["compose", "done"]}


@pytest.mark.parametrize("axis", ["depth", "fan_out", "steps"])
def test_each_axis_loads_as_a_contract(axis: str) -> None:
    pattern = pattern_from({**ROW, "plan": {axis: 2}}, where="row")
    assert pattern.plan == PlanLimits(**{axis: 2})


@pytest.mark.parametrize("extra", [{}, {"plan": None}])
def test_an_unset_plan_defers_to_the_run(extra: dict[str, Any]) -> None:
    assert pattern_from({**ROW, **extra}, where="row").plan is None


def test_a_malformed_limit_is_refused() -> None:
    with pytest.raises(ValueError):
        pattern_from({**ROW, "plan": {"steps": "many"}}, where="row")


@pytest.mark.parametrize("key", ["absorb", "offload_over"])
def test_loop_tuning_is_still_not_accepted_as_a_row(key: str) -> None:
    with pytest.raises(ValueError, match=key):
        pattern_from({**ROW, key: 1}, where="row")


@pytest.mark.parametrize("bound, calls", [(0, []), (1, ["ran"])])
async def test_a_stored_bound_decides_whether_the_plan_runs(bound: int, calls: list[str]) -> None:
    executed: list[str] = []

    def work() -> str:
        """Count execution."""
        executed.append("ran")
        return "ok"

    tools = CallableComponents(registered_by="test", at="2026-01-01T00:00:00+00:00")
    tools.add(work, effects=EffectProfile())
    pattern = pattern_from({**ROW, "plan": {"steps": bound}}, where="row")
    agent = AgentComponent(pattern=pattern, effects=EffectProfile())
    model = ScriptedModel(
        [
            ModelResponse(
                "",
                (
                    ToolCall(
                        "p",
                        "compose",
                        {
                            "steps": [
                                {"kind": "invoke", "id": "w", "component": "work", "inputs": []}
                            ]
                        },
                    ),
                ),
            ),
            ModelResponse("", (ToolCall("d", "done", {"summary": "finished"}),)),
        ]
    )
    async for _ in run(
        Composition(
            (Invoke("agent", agent.registration_id, (Binding(name="brief", value="go"),)),)
        ),
        Ports(
            model=model,
            components=(tools, agent),
            governance=AllowAll(),
            clock=FixedClock(),
            sink=ListSink(),
        ),
        options=RunOptions(lease=Lease(Ceiling(40, 3600, 10000), Floor(0))),
    ):
        pass
    assert executed == calls
