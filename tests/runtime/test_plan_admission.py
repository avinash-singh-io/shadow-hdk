"""RED scenarios for Phase 36 — admission inside `spawn`, the plan parked as one question, a
refused plan as an observation, limits that meet, a plan after its planner, amend as a resume.

These fail for the stated reasons until Groups 2–5 land. They drive the kit's own loop
(`AgentComponent` + `ScriptedModel`) authoring a plan through `compose`, the way the shipped
patterns do, so what they prove holds for every planner behind the same registry (D110).
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import JsonValue

from shadow_hdk.adapters.agent import AgentComponent, Pattern
from shadow_hdk.adapters.agent.pattern import COMPOSE, DONE, PROPOSE
from shadow_hdk.adapters.basic import AllowAll, CallableComponents
from shadow_hdk.kernel import (
    Allow,
    Ask,
    Binding,
    Ceiling,
    Composition,
    Context,
    EffectProfile,
    FanOut,
    Floor,
    Invoke,
    Judgement,
    Lease,
    PlanLimits,
    Refuse,
    ScopeSet,
)
from shadow_hdk.kernel.events import (
    Composed,
    Ended,
    Event,
    Invoked,
    PlanAdmitted,
    PlanRefused,
    Spawned,
)
from shadow_hdk.kernel.ports import ModelResponse, ToolCall
from shadow_hdk.runtime import Ports, RunOptions, resume, run
from shadow_hdk.runtime.approvals import Approvals
from shadow_hdk.runtime.checkpoints import InMemoryRunStore, saver_over
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
AT = "2026-01-01T00:00:00+00:00"


def look(topic: str) -> str:
    """Look a topic up."""
    return f"found {topic}"


def wipe(what: str) -> str:
    """Delete something."""
    return f"wiped {what}"


class NoWrites:
    async def judge(self, effects: EffectProfile, _context: Context) -> Judgement:
        if effects.writes.names or effects.writes.everything:
            return Refuse("writing is not permitted in this deployment")
        return Allow()


class AskBeforeWrites:
    async def judge(self, effects: EffectProfile, _context: Context) -> Judgement:
        if effects.writes.names or effects.writes.everything:
            return Ask("a write — a person decides")
        return Allow()


def invoke(step_id: str, component: str, **inputs: JsonValue) -> dict[str, JsonValue]:
    return {
        "kind": "invoke",
        "id": step_id,
        "component": component,
        "inputs": [{"name": k, "value": v} for k, v in inputs.items()],
    }


def fan_out(step_id: str, *steps: dict[str, JsonValue]) -> dict[str, JsonValue]:
    return {"kind": "fan_out", "id": step_id, "steps": list(steps)}


def a_plan(*steps: dict[str, JsonValue]) -> dict[str, JsonValue]:
    return {"steps": list(steps)}


THREE_LOOKS = a_plan(
    fan_out(
        "f",
        invoke("a", "look", topic="1"),
        invoke("b", "look", topic="2"),
        invoke("c", "look", topic="3"),
    )
)


def _agent(pattern: Pattern | None = None) -> AgentComponent:
    return AgentComponent(
        pattern=pattern
        or Pattern(name="p", system="plan it", meta_tools=frozenset({COMPOSE, PROPOSE, DONE})),
        effects=EffectProfile(costs=True),
        at=AT,
    )


def _tools() -> CallableComponents:
    tools = CallableComponents(registered_by="tests", at=AT)
    tools.add(look, effects=EffectProfile(reads=WORKSPACE))
    tools.add(wipe, effects=EffectProfile(writes=WORKSPACE, reversible=False))
    return tools


def _ports(model: ScriptedModel, agent: AgentComponent, governance: Any = None) -> Ports:
    return Ports(
        model=model,
        components=(_tools(), agent),
        governance=governance or AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


def _model(plan: dict[str, JsonValue]) -> ScriptedModel:
    return ScriptedModel(
        [
            ModelResponse("planning", (ToolCall("c1", "compose", plan),)),
            ModelResponse("ok", (ToolCall("d1", "done", {"summary": "finished"}),)),
        ]
    )


def _brief(agent: AgentComponent) -> Composition:
    return Composition((Invoke("a1", agent.registration_id, (Binding(name="brief", value="go"),)),))


async def _drive(
    plan: dict[str, JsonValue],
    *,
    limits: PlanLimits | None = None,
    pattern: Pattern | None = None,
    governance: Any = None,
    approvals: Approvals | None = None,
) -> tuple[list[Event], ScriptedModel]:
    agent = _agent(pattern)
    model = _model(plan)
    options = RunOptions(
        lease=Lease(Ceiling(60, 3600, 10_000), Floor(0)),
        plan_limits=limits,
        approvals=approvals,
    )
    events = [
        e async for e in run(_brief(agent), _ports(model, agent, governance), options=options)
    ]
    return events, model


def _kinds(events: list[Event]) -> list[str]:
    return [e.kind for e in events]


def _invoked(events: list[Event]) -> list[str]:
    return [e.step for e in events if isinstance(e, Invoked)]


def _tool_answer(model: ScriptedModel, call_id: str = "c1") -> str:
    return next(
        m.content
        for m in model.requests[1].messages
        if m.role == "tool" and m.tool_call_id == call_id
    )


# ---------------------------------------------------------------- refused before anything runs


async def test_a_plan_over_the_limits_is_refused_before_anything_runs() -> None:
    """D108: the judgement no step can make, made before compile. No `Spawned`, no `Invoked` for
    any step of the plan — the refusal is the only trace, and it names the axis."""
    events, _ = await _drive(THREE_LOOKS, limits=PlanLimits(fan_out=2))
    refused = [e for e in events if isinstance(e, PlanRefused)]
    assert len(refused) == 1
    assert [(m.axis, m.step, m.required, m.found) for m in refused[0].mismatches] == [
        ("fan_out", "f", "2", "3")
    ]
    assert not any(isinstance(e, Spawned) for e in events), "a refused plan is never spawned"
    assert _invoked(events) == ["a1"], "only the planner's own step ran"


async def test_the_same_plan_inside_the_limits_is_admitted_and_spawned() -> None:
    events, _ = await _drive(THREE_LOOKS, limits=PlanLimits(fan_out=3))
    admitted = [e for e in events if isinstance(e, PlanAdmitted)]
    assert len(admitted) == 1 and admitted[0].limits == PlanLimits(fan_out=3)
    assert any(isinstance(e, Spawned) for e in events)
    assert {"a", "b", "c"} <= set(_invoked(events))
    kinds = _kinds(events)
    assert kinds.index("plan_admitted") < kinds.index("spawned"), "admitted, then spawned"


async def test_an_unregistered_component_refuses_the_plan_by_name() -> None:
    events, _ = await _drive(a_plan(invoke("a", "look", topic="1"), invoke("b", "nope")))
    refused = next(e for e in events if isinstance(e, PlanRefused))
    assert [(m.axis, m.step, m.found) for m in refused.mismatches] == [("component", "b", "nope")]
    assert "a" not in _invoked(events), "existence is checked for the whole plan before any step"


# ---------------------------------------------------------------- effects, dry-judged


async def test_a_step_the_policy_refuses_is_named_on_the_admission_and_refused_at_its_step() -> (
    None
):
    """D108 as amended: a step's own refusal is a judgement the step *can* make, so admission
    names it (`refusals`) and the plan runs — the harmless step completes, the refused one is
    refused at its invocation and the planner is told per step, as BUG-012 promised."""
    events, model = await _drive(
        a_plan(invoke("a", "look", topic="1"), invoke("b", "wipe", what="all")),
        governance=NoWrites(),
    )
    admitted = next(e for e in events if isinstance(e, PlanAdmitted))
    assert admitted.refusals == ("b",) and admitted.asks == ()
    assert "a" in _invoked(events) and "b" not in _invoked(events)
    assert any(e.kind == "refused" and getattr(e, "step", "") == "b" for e in events)
    answer = _tool_answer(model)
    assert "found 1" in answer and "not permitted" in answer, "every result, per step"


async def test_a_step_the_policy_asks_about_is_named_on_the_admission_and_asks_at_its_step() -> (
    None
):
    """D121 as amended: admission names the steps the policy will ask about, and raises no question
    of its own — the step asks at its invocation through the path that already exists (here the
    in-process park, D57). A plan of one step therefore asks exactly once, as it always has; a
    host that wants one card for the whole plan has the list and the rules to keep."""
    plan = a_plan(invoke("a", "look", topic="1"), invoke("b", "wipe", what="all"))
    events, _ = await _drive(plan, governance=AskBeforeWrites())
    admitted = next(e for e in events if isinstance(e, PlanAdmitted))
    assert admitted.asks == ("b",), "what will ask, named up front"
    assert "a" in _invoked(events), "the harmless step ran"
    inner = [e for e in events if e.kind == "approval_requested" and getattr(e, "step", "") == "b"]
    assert len(inner) == 1, "the write asked once, at its own step"
    assert "b" not in _invoked(events) and not any(isinstance(e, Ended) for e in events), (
        "and the run parks there, as today"
    )


# ---------------------------------------------------------------- limits meet


async def test_a_childs_limits_are_the_meet_of_the_hosts_and_the_patterns() -> None:
    """D109: host fan_out=3, the pattern's own fan_out=2 — the effective limit is 2."""
    pattern = Pattern(
        name="p",
        system="plan it",
        meta_tools=frozenset({COMPOSE, PROPOSE, DONE}),
        plan=PlanLimits(fan_out=2),
    )
    events, _ = await _drive(THREE_LOOKS, limits=PlanLimits(fan_out=3), pattern=pattern)
    refused = next(e for e in events if isinstance(e, PlanRefused))
    assert [(m.axis, m.required, m.found) for m in refused.mismatches] == [("fan_out", "2", "3")]


# ---------------------------------------------------------------- the planner is told


async def test_a_refused_plan_reaches_the_planner_as_an_observation_with_every_reason() -> None:
    """D111: the planner hears every mismatch and decides; the runtime never trims the plan."""
    plan = a_plan(
        fan_out(
            "f",
            invoke("a", "look", topic="1"),
            invoke("b", "ghost"),
            invoke("c", "look", topic="3"),
        )
    )
    events, model = await _drive(plan, limits=PlanLimits(fan_out=2))
    answer = _tool_answer(model)
    assert "refused" in answer.lower()
    assert "fan_out" in answer and "ghost" in answer, "every reason, not the first"
    composed = [e for e in events if isinstance(e, Composed)]
    assert all(len(e.composition.steps) == 1 for e in composed), "no trimmed plan was composed"
    assert not any(isinstance(e, Spawned) for e in events)


# ---------------------------------------------------------------- after its planner


async def test_a_plan_can_run_after_its_planner() -> None:
    """D112: with `absorb=False` the planner's own step closes before the plan's first step runs,
    and the plan still runs to its end inside the same parent run — on the record, not in the
    planner's transcript."""
    pattern = Pattern(
        name="p", system="plan it", meta_tools=frozenset({COMPOSE, PROPOSE, DONE}), absorb=False
    )
    events, model = await _drive(a_plan(invoke("a", "look", topic="1")), pattern=pattern)
    kinds_and_steps = [(e.kind, getattr(e, "step", None)) for e in events]
    planner_closed = kinds_and_steps.index(("observed", "a1"))
    first_plan_step = next(
        i for i, e in enumerate(events) if isinstance(e, Invoked) and e.step == "a"
    )
    assert planner_closed < first_plan_step, "the planner's step closed first"
    assert isinstance(events[-1], Ended) and "a" in _invoked(events)
    assert "found 1" not in _tool_answer(model), "the planner did not absorb the results"


# ---------------------------------------------------------------- amend is a resume


async def test_an_amendment_is_admitted_like_the_original_and_takes_effect_on_resume() -> None:
    """D116: `resume` already takes the plan back in; an amended composition is admitted before it
    is taken, `Composed` fires with it, and the run continues on the new shape."""
    store = InMemoryRunStore()
    saver = saver_over(store)
    tools = _tools()
    ports = Ports(
        model=None,
        components=(tools,),
        governance=AskBeforeWrites(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    options = RunOptions(
        lease=Lease(Ceiling(60, 3600, 10_000), Floor(0)),
        run_id="amendable",
        checkpointer=saver,
        plan_limits=PlanLimits(fan_out=2),
    )
    original = Composition((Invoke("w", "wipe", (Binding(name="what", value="all"),)),))
    parked = [e async for e in run(original, ports, options=options)]
    assert not any(isinstance(e, Ended) for e in parked), "parked on the ask"

    amended = Composition(
        (
            Invoke("w", "wipe", (Binding(name="what", value="all"),)),
            Invoke("l", "look", (Binding(name="topic", value="after"),)),
        )
    )
    continued = [e async for e in resume(amended, Allow(), ports, options=options)]
    kinds = _kinds(continued)
    assert "plan_admitted" in kinds and "composed" in kinds
    assert next(e for e in continued if isinstance(e, PlanAdmitted)).amendment is True
    assert next(e for e in continued if isinstance(e, Composed)).composition == amended
    assert "l" in _invoked(continued) and isinstance(continued[-1], Ended)


async def test_a_refused_amendment_leaves_the_parked_run_untouched() -> None:
    store = InMemoryRunStore()
    saver = saver_over(store)
    ports = Ports(
        model=None,
        components=(_tools(),),
        governance=AskBeforeWrites(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    options = RunOptions(
        lease=Lease(Ceiling(60, 3600, 10_000), Floor(0)),
        run_id="amendable-2",
        checkpointer=saver,
        plan_limits=PlanLimits(fan_out=1),
    )
    original = Composition((Invoke("w", "wipe", (Binding(name="what", value="all"),)),))
    _ = [e async for e in run(original, ports, options=options)]
    too_wide = Composition(
        (
            FanOut(
                "f",
                (
                    Invoke("x", "look", (Binding(name="topic", value="1"),)),
                    Invoke("y", "look", (Binding(name="topic", value="2"),)),
                ),
            ),
        )
    )
    continued = [e async for e in resume(too_wide, Allow(), ports, options=options)]
    assert _kinds(continued) == ["plan_refused"], "refused, and nothing else happened"
    assert next(e for e in continued if isinstance(e, PlanRefused)).amendment is True
