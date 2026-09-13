"""A skill costs a name and a line until chosen; choosing and minting are governed steps (D55, D56).

The registry is offered as a **component** — `use_skill`, and `mint_skill` where the host allows
it — so choosing a procedure is a step on the record like any other act, reachable by an agent in
process, an agent over the wire, and a CLI by subscription through the registry socket. The names
and lines ride the tool's own description, rebuilt on every catalogue, so a skill minted a turn ago
is there the next. Choosing is where D17's check runs, against `visible()`: a skill needing what
this run does not offer is refused by name and its body never arrives. Minting proposes through
the sink as `kind="skill"`; the runtime keeps nothing, and a host that keeps it hands it back.
"""

from __future__ import annotations

from typing import Any

import pytest

from shadow_hdk.adapters.agent import (
    AgentComponent,
    MintedSkills,
    Pattern,
    Skill,
    SkillComponents,
    SkillRegistry,
    kept_from,
)
from shadow_hdk.adapters.agent.registry import MINT_SKILL, USE_SKILL
from shadow_hdk.adapters.basic import AllowAll, CallableComponents
from shadow_hdk.adapters.modes import Mode, ModeGovernance
from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Composition,
    Event,
    Floor,
    Invoke,
    Lease,
    ScopeSet,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import ModelRequest, ModelResponse, ToolCall
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
AT = "2026-01-01T00:00:00+00:00"

CAREFUL = Skill(
    name="look-before-you-change",
    description="Read what is there before changing it.",
    prompt="Before any change, read the current state and say what will change.",
    needs=frozenset({"look"}),
)
NEEDS_A_DEPLOY = Skill(
    name="ship-it",
    description="Deploy the thing.",
    prompt="Run the deploy and watch it.",
    needs=frozenset({"deploy"}),
)


def look(topic: str) -> str:
    """Look a topic up."""
    return f"found {topic}"


def a_registry(*skills: Skill) -> SkillRegistry:
    handed = MintedSkills()
    for skill in skills:
        handed._skills.append(skill)  # noqa: SLF001 — a source with exactly these, as labelled
    return SkillRegistry((handed,))


async def drive(
    responses: list[ModelResponse],
    *,
    registry: SkillRegistry | None,
    minting: bool = False,
    governance: Any = None,
) -> tuple[ScriptedModel, ListSink, list[Event]]:
    tools = CallableComponents(registered_by="tests", at=AT)
    tools.add(look, effects=EffectProfile(reads=WORKSPACE))
    agent = AgentComponent(
        pattern=Pattern(name="p", system="do the work"), effects=EffectProfile(costs=True), at=AT
    )
    components: tuple[Any, ...] = (tools, agent)
    if registry is not None:
        components += (SkillComponents(registry, minting=minting, at=AT),)
    model = ScriptedModel(responses)
    sink = ListSink()
    ports = Ports(
        model=model,
        components=components,
        governance=governance or AllowAll(),
        sink=sink,
        clock=FixedClock(),
    )
    plan = Composition((Invoke("a1", agent.registration_id, (Binding(name="brief", value="go"),)),))
    events = [
        event
        async for event in run(
            plan, ports, options=RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0)))
        )
    ]
    return model, sink, events


def says(*calls: ToolCall) -> ModelResponse:
    return ModelResponse("", calls)


DONE = ToolCall("d", "done", {"summary": "finished"})


def offered(request: ModelRequest, name: str) -> Any:
    return next((t for t in request.tools if t.name == name), None)


def tool_answer(model: ScriptedModel, turn: int, call_id: str) -> str:
    """What the model was told in reply to one of its calls, as of its next request."""
    for message in model.requests[turn].messages:
        if message.role == "tool" and message.tool_call_id == call_id:
            return message.content
    raise AssertionError(f"no answer to {call_id!r} in turn {turn}")


def steps_named(events: list[Event], component: str) -> list[Any]:
    """The observations of every step that invoked `component`, wherever in the tree it ran."""
    invoked = {
        (e.run_id, e.step)
        for e in events
        if e.kind == "invoked" and getattr(e, "component", "") == component
    }
    return [e for e in events if e.kind == "observed" and (e.run_id, e.step) in invoked]


# ---------------------------------------------------------------- names and lines, on the tool


async def test_the_model_sees_names_and_lines_on_the_tool_and_nothing_more() -> None:
    model, _, _ = await drive([says(DONE)], registry=a_registry(CAREFUL, NEEDS_A_DEPLOY))

    verb = offered(model.requests[0], USE_SKILL)
    assert verb is not None, "a registry with skills in it must offer the tool"
    assert "look-before-you-change — Read what is there before changing it." in verb.description
    assert "ship-it — Deploy the thing." in verb.description
    assert "Before any change" not in verb.description, "the body is disclosed on use, not before"
    assert verb.input_schema["properties"]["name"]["enum"] == ["look-before-you-change", "ship-it"]


async def test_no_skills_no_tool() -> None:
    model, _, _ = await drive([says(DONE)], registry=SkillRegistry(()))
    assert offered(model.requests[0], USE_SKILL) is None
    model, _, _ = await drive([says(DONE)], registry=None)
    assert offered(model.requests[0], USE_SKILL) is None


# ---------------------------------------------------------------- choosing reveals, after the check


async def test_choosing_a_skill_is_a_step_on_the_record_and_loads_its_body() -> None:
    model, _, events = await drive(
        [says(ToolCall("u1", USE_SKILL, {"name": "look-before-you-change"})), says(DONE)],
        registry=a_registry(CAREFUL),
    )
    answer = tool_answer(model, 1, "u1")
    assert "Before any change, read the current state" in answer
    assert "look-before-you-change" in answer
    # The act is on the record: a step, invoked and observed, like any other.
    (chosen,) = steps_named(events, USE_SKILL)
    assert chosen.observation.kind == "completed"
    assert chosen.observation.output["skill"] == "look-before-you-change"


async def test_a_skill_needing_what_this_run_lacks_is_refused_by_name_and_not_loaded() -> None:
    model, _, events = await drive(
        [says(ToolCall("u1", USE_SKILL, {"name": "ship-it"})), says(DONE)],
        registry=a_registry(NEEDS_A_DEPLOY),
    )
    answer = tool_answer(model, 1, "u1")
    assert "deploy" in answer and "not loaded" in answer
    assert "Run the deploy" not in answer, "a refused skill's body reached the model"
    (refused,) = steps_named(events, USE_SKILL)
    assert refused.observation.kind == "failed"


async def test_a_skill_hidden_by_the_mode_is_refused_the_same_way() -> None:
    """`needs` is checked against what the *policy* leaves visible, not against what is
    registered — the same computation the catalogue comes from."""
    looking_at_nothing = Mode("blind", ceiling=EffectProfile(costs=True))
    model, _, _ = await drive(
        [says(ToolCall("u1", USE_SKILL, {"name": "look-before-you-change"})), says(DONE)],
        registry=a_registry(CAREFUL),
        governance=ModeGovernance({"blind": looking_at_nothing}, default="blind"),
    )
    answer = tool_answer(model, 1, "u1")
    assert "look" in answer and "not loaded" in answer


async def test_a_name_nobody_registered_is_answered_with_what_there_is() -> None:
    model, _, _ = await drive(
        [says(ToolCall("u1", USE_SKILL, {"name": "nope"})), says(DONE)],
        registry=a_registry(CAREFUL),
    )
    answer = tool_answer(model, 1, "u1")
    assert "nope" in answer and "look-before-you-change" in answer


# ----------------------------------------------------------------- minted, and proposed for keeping


MINT = ToolCall(
    "m1",
    MINT_SKILL,
    {
        "name": "triage",
        "description": "Sort what came in by urgency before touching any of it.",
        "prompt": "List everything first. Then order by urgency. Only then act on the first.",
        "needs": ["look"],
    },
)


async def test_a_minted_skill_is_usable_at_once_and_proposed_for_keeping() -> None:
    registry = a_registry(CAREFUL)
    model, sink, events = await drive(
        [says(MINT), says(ToolCall("u1", USE_SKILL, {"name": "triage"})), says(DONE)],
        registry=registry,
        minting=True,
    )
    assert "triage" in tool_answer(model, 1, "m1")
    on_offer = offered(model.requests[1], USE_SKILL).input_schema["properties"]["name"]["enum"]
    assert on_offer == ["look-before-you-change", "triage"]
    assert "List everything first" in tool_answer(model, 2, "u1")
    minted = await registry.find("triage")
    assert minted is not None and minted.source == "minted"
    assert len(steps_named(events, MINT_SKILL)) == 1, "minting is a step on the record"

    kept = [p for p in sink.proposals if p.kind == "skill"]
    assert len(kept) == 1
    assert kept[0].payload == {
        "name": "triage",
        "description": "Sort what came in by urgency before touching any of it.",
        "prompt": "List everything first. Then order by urgency. Only then act on the first.",
        "needs": ["look"],
    }
    assert kept[0].provenance.adapter == "agent"


async def test_minting_is_not_offered_unless_the_host_allows_it() -> None:
    model, _, _ = await drive([says(DONE)], registry=a_registry(CAREFUL))
    assert offered(model.requests[0], MINT_SKILL) is None


async def test_minting_writes_the_record_so_a_mode_can_refuse_it_by_effect() -> None:
    """`mint_skill` declares `writes: {record}`; a mode that permits no writes hides it — the
    policy never heard of minting, and does not need to."""
    reads_only = Mode("reads", ceiling=EffectProfile(reads=ScopeSet(everything=True), costs=True))
    model, sink, _ = await drive(
        [says(DONE)],
        registry=a_registry(CAREFUL),
        minting=True,
        governance=ModeGovernance({"reads": reads_only}, default="reads"),
    )
    assert offered(model.requests[0], MINT_SKILL) is None
    assert offered(model.requests[0], USE_SKILL) is not None, "choosing is pure and stays"


async def test_a_badly_shaped_mint_is_refused_and_nothing_is_kept() -> None:
    registry = a_registry(CAREFUL)
    bad = ToolCall("m1", MINT_SKILL, {"name": "x", "prompt": "do it"})
    model, sink, _ = await drive([says(bad), says(DONE)], registry=registry, minting=True)
    assert "description" in tool_answer(model, 1, "m1")
    assert await registry.find("x") is None
    assert [p for p in sink.proposals if p.kind == "skill"] == []


async def test_a_kept_proposal_comes_back_as_a_source_next_run() -> None:
    """The host's half: it kept the proposal — however it keeps things — and hands it back."""
    registry = a_registry(CAREFUL)
    _, sink, _ = await drive([says(MINT), says(DONE)], registry=registry, minting=True)
    kept = kept_from(sink.proposals[0], source="kept")
    assert kept.name == "triage" and kept.source == "kept" and kept.needs == frozenset({"look"})

    next_run = SkillRegistry((a_registry(kept),))  # a registry is a source; the host composes
    model, _, _ = await drive([says(DONE)], registry=next_run)
    assert "triage — Sort what came in" in offered(model.requests[0], USE_SKILL).description
