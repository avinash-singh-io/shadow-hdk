"""D110: planning is a registered component, so a resident CLI plans through the socket exactly
as the kit's own loop does — one path into `children.spawn`, one admission, one record.

`compose` is offered like any tool: no effects (proposing is not an effect; running is), the
composition as its input, the plan's results as its output. Through the offer a CLI's call to
`compose` becomes a one-step child whose step spawns the plan as a grandchild — nothing new in the
runtime, the same nesting a sub-agent already has.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import JsonValue

from shadow_hdk.adapters.basic import AllowAll, CallableComponents
from shadow_hdk.adapters.recording import RecordingServer
from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Floor,
    Invoke,
    Lease,
    Observation,
    PlanLimits,
    Refused,
    ScopeSet,
)
from shadow_hdk.kernel.events import Event, PlanAdmitted, PlanRefused, Spawned
from shadow_hdk.runtime import Ports, RunOptions, current_run, run
from shadow_hdk.runtime.planning import COMPOSE, PlanComponents, plan_components
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink, make_registration
from shadow_hdk.testing.contracts import ComponentPortContract

pytestmark = pytest.mark.anyio

AT = "2026-01-01T00:00:00+00:00"
WORKSPACE = ScopeSet.of("workspace")
DRIVER = make_registration("driver")


def look(topic: str) -> str:
    """Look a topic up."""
    return f"found {topic}"


def _tools() -> CallableComponents:
    tools = CallableComponents(registered_by="tests", at=AT)
    tools.add(look, effects=EffectProfile(reads=WORKSPACE))
    return tools


def a_plan(*steps: dict[str, JsonValue]) -> dict[str, JsonValue]:
    return {"steps": list(steps)}


def invoke(step_id: str, component: str, **inputs: JsonValue) -> dict[str, JsonValue]:
    return {
        "kind": "invoke",
        "id": step_id,
        "component": component,
        "inputs": [{"name": k, "value": v} for k, v in inputs.items()],
    }


async def _run(driver: Any, *, limits: PlanLimits | None = None) -> list[Event]:
    ports = Ports(
        model=None,
        components=(_tools(), plan_components(), InMemoryComponents([(DRIVER, driver)])),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    options = RunOptions(lease=Lease(Ceiling(40, 600, 1_000), Floor(0)), plan_limits=limits)
    return [
        e
        async for e in run(
            Composition((Invoke("d1", DRIVER.id, (Binding(name="brief", value="go"),)),)),
            ports,
            options=options,
        )
    ]


def test_compose_is_registered_with_no_effects() -> None:
    [registration] = PlanComponents()._registrations  # noqa: SLF001 — the shape, once
    assert registration.id == COMPOSE
    assert registration.component.effects == EffectProfile(), "proposing is not an effect"
    assert "steps" in json.dumps(registration.component.interface.input_schema)


async def test_a_component_invokes_compose_and_the_plan_runs_under_admission() -> None:
    seen: dict[str, Any] = {}

    async def driver(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        seen["visible"] = sorted(r.id for r in await context.visible())
        port, _ = context._registry.resolve(COMPOSE)  # noqa: SLF001 — resolve as the step does
        seen["result"] = await port.invoke(
            COMPOSE, a_plan(invoke("a", "look", topic="1"), invoke("b", "look", topic="2"))
        )
        return Completed(None)

    events = await _run(driver)
    assert COMPOSE in seen["visible"], "offered like any tool"
    result = seen["result"]
    assert isinstance(result, Completed), result
    assert "found 1" in json.dumps(result.output) and "found 2" in json.dumps(result.output)
    assert any(isinstance(e, PlanAdmitted) for e in events), "admitted on the record"
    assert any(isinstance(e, Spawned) for e in events)


async def test_a_refused_plan_through_compose_is_a_refused_observation_with_every_reason() -> None:
    seen: dict[str, Any] = {}

    async def driver(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        port, _ = context._registry.resolve(COMPOSE)  # noqa: SLF001
        seen["result"] = await port.invoke(
            COMPOSE,
            a_plan(
                {
                    "kind": "fan_out",
                    "id": "f",
                    "steps": [
                        invoke("a", "look", topic="1"),
                        invoke("b", "ghost"),
                        invoke("c", "look", topic="3"),
                    ],
                }
            ),
        )
        return Completed(None)

    events = await _run(driver, limits=PlanLimits(fan_out=2))
    result = seen["result"]
    assert isinstance(result, Refused), result
    assert "fan_out" in result.reason and "ghost" in result.reason, "every reason (D111)"
    assert any(isinstance(e, PlanRefused) for e in events)
    assert not any(isinstance(e, Spawned) for e in events)


async def test_a_plan_that_does_not_parse_is_a_failure_not_a_crash() -> None:
    seen: dict[str, Any] = {}

    async def driver(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        port, _ = context._registry.resolve(COMPOSE)  # noqa: SLF001
        seen["result"] = await port.invoke(COMPOSE, {"steps": [{"kind": "nonsense"}]})
        return Completed(None)

    await _run(driver)
    assert not isinstance(seen["result"], Completed)
    assert (
        "parse" in getattr(seen["result"], "error", getattr(seen["result"], "reason", "")).lower()
    )


# ---------------------------------------------------------------- through the socket's registry


async def test_a_cli_plans_through_the_offer_and_the_record_shows_it() -> None:
    """The socket path a resident CLI takes, without a CLI: the `RecordingServer` over the run's
    context, a `compose` call in the vocabulary the CLI speaks. The plan is admitted and runs;
    the CLI reads every result; the record carries the admission."""
    seen: dict[str, Any] = {}

    async def driver(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        server = RecordingServer(context, withhold=set())
        seen["offered"] = sorted(tool.name for tool in await server.tools())
        seen["result"] = await server.call_tool(
            COMPOSE, a_plan(invoke("a", "look", topic="1"), invoke("b", "look", topic="2"))
        )
        return Completed(None)

    events = await _run(driver)
    assert COMPOSE in seen["offered"], "a CLI is offered compose like any tool"
    result = seen["result"]
    assert result.is_error is False, result
    text = "".join(getattr(c, "text", "") for c in result.content)
    assert "found 1" in text and "found 2" in text
    assert any(isinstance(e, PlanAdmitted) for e in events)


# ---------------------------------------------------------------- the loop's meta-tool is sugar


async def test_the_loop_never_shows_the_plan_component_beside_its_own_meta_tool() -> None:
    """D110: for the kit's own loop, the registered `compose` *is* the `compose` meta-tool — one
    path, one name. A pattern that offers `compose` shows it once (the meta-tool); `single`, which
    withholds it so the model cannot change its shape, shows it not at all — a registered
    component must not hand a `single` agent the planning its pattern denies."""
    from shadow_hdk.adapters.agent import AgentComponent, Pattern
    from shadow_hdk.adapters.agent.pattern import COMPOSE as META
    from shadow_hdk.adapters.agent.pattern import DONE, PROPOSE
    from shadow_hdk.kernel.ports import ModelResponse, ToolCall
    from shadow_hdk.runtime.testing import ScriptedModel

    seen: dict[str, list[str]] = {}
    for name, meta in (("planner", {META, PROPOSE, DONE}), ("single", {PROPOSE, DONE})):
        agent = AgentComponent(
            pattern=Pattern(name=name, system="go", meta_tools=frozenset(meta)),
            effects=EffectProfile(costs=True),
            at=AT,
        )
        model = ScriptedModel([ModelResponse("ok", (ToolCall("d1", "done", {"summary": "x"}),))])
        ports = Ports(
            model=model,
            components=(_tools(), plan_components(), agent),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        )
        [
            _
            async for _ in run(
                Composition(
                    (Invoke("a1", agent.registration_id, (Binding(name="brief", value="go"),)),)
                ),
                ports,
                options=RunOptions(lease=Lease(Ceiling(20, 600, 1_000), Floor(0))),
            )
        ]
        seen[name] = sorted(t.name for t in model.requests[0].tools)
    assert seen["planner"].count(COMPOSE) == 1, seen["planner"]
    assert COMPOSE not in seen["single"], seen["single"]


# ---------------------------------------------------------------- the port's contract


class TestPlanComponentsIsAComponentPort(ComponentPortContract):
    def port(self) -> Any:
        return plan_components()

    def valid_call(self) -> tuple[str, Any]:
        return COMPOSE, a_plan(invoke("a", "look", topic="1"))
