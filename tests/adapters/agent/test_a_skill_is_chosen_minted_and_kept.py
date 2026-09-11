"""A skill costs a name and a line until the model chooses it; minting is a governed act (D55, D56).

The model sees the registry's names and lines on the `use_skill` verb itself — the same
disclosure a thinned tool catalogue gets (D13, Phase 21): a line each, the body on demand. Choosing
is where D17's check runs, against `visible()`, so a skill that needs what this run does not offer
is refused by name and not loaded. A model that works out a procedure worth keeping mints it with
`mint_skill`: usable at once through the registry it was handed, and *proposed* through the sink
as `kind="skill"` — the runtime keeps nothing; a host that keeps it hands it back next run.
"""

from __future__ import annotations

from typing import Any

import pytest
from shadow_hdk.adapters.agent import (
    MINT_SKILL,
    USE_SKILL,
    AgentComponent,
    MintedSkills,
    Pattern,
    Skill,
    SkillRegistry,
    kept_from,
)
from shadow_hdk.adapters.basic import AllowAll, CallableComponents

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
        handed._skills.append(skill)  # noqa: SLF001 — a source with exactly these, labelled by the skill
    return SkillRegistry((handed,))


async def drive(
    responses: list[ModelResponse],
    *,
    registry: SkillRegistry | None,
    meta: frozenset[str] = frozenset({"propose", "done"}),
) -> tuple[ScriptedModel, ListSink, list[Event]]:
    tools = CallableComponents(registered_by="tests", at=AT)
    tools.add(look, effects=EffectProfile(reads=WORKSPACE))
    agent = AgentComponent(
        pattern=Pattern(name="p", system="do the work", meta_tools=meta),
        effects=EffectProfile(costs=True),
        at=AT,
        skills=registry,
    )
    model = ScriptedModel(responses)
    sink = ListSink()
    ports = Ports(
        model=model, components=(tools, agent), governance=AllowAll(), sink=sink, clock=FixedClock()
    )
    events = [
        event
        async for event in run(
            Composition(
                (Invoke("a1", agent.registration_id, (Binding(name="brief", value="go"),)),)
            ),
            ports,
            options=RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0))),
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


# ------------------------------------------------------------------ names and lines, on the verb


async def test_the_model_sees_names_and_lines_on_the_verb_and_nothing_more() -> None:
    model, _, _ = await drive([says(DONE)], registry=a_registry(CAREFUL, NEEDS_A_DEPLOY))

    verb = offered(model.requests[0], USE_SKILL)
    assert verb is not None, "a registry with skills in it must offer the verb"
    assert "look-before-you-change — Read what is there before changing it." in verb.description
    assert "ship-it — Deploy the thing." in verb.description
    assert "Before any change" not in verb.description, "the body is disclosed on use, not before"
    assert verb.input_schema["properties"]["name"]["enum"] == ["look-before-you-change", "ship-it"]


async def test_no_skills_no_verb() -> None:
    model, _, _ = await drive([says(DONE)], registry=SkillRegistry(()))
    assert offered(model.requests[0], USE_SKILL) is None
    model, _, _ = await drive([says(DONE)], registry=None)
    assert offered(model.requests[0], USE_SKILL) is None


# ---------------------------------------------------------------- choosing reveals, after the check


async def test_choosing_a_skill_loads_its_body_as_the_answer() -> None:
    model, _, _ = await drive(
        [says(ToolCall("u1", USE_SKILL, {"name": "look-before-you-change"})), says(DONE)],
        registry=a_registry(CAREFUL),
    )
    answer = tool_answer(model, 1, "u1")
    assert "Before any change, read the current state" in answer
    assert "look-before-you-change" in answer


async def test_a_skill_needing_what_this_run_does_not_offer_is_refused_by_name_and_not_loaded() -> (
    None
):
    model, _, _ = await drive(
        [says(ToolCall("u1", USE_SKILL, {"name": "ship-it"})), says(DONE)],
        registry=a_registry(NEEDS_A_DEPLOY),
    )
    answer = tool_answer(model, 1, "u1")
    assert "deploy" in answer and "not loaded" in answer
    assert "Run the deploy" not in answer, "a refused skill's body reached the model"


async def test_a_name_nobody_registered_is_answered_with_what_there_is() -> None:
    model, _, _ = await drive(
        [says(ToolCall("u1", USE_SKILL, {"name": "nope"})), says(DONE)],
        registry=a_registry(CAREFUL),
    )
    answer = tool_answer(model, 1, "u1")
    assert "nope" in answer and "look-before-you-change" in answer


async def test_describe_answers_for_a_skill_without_loading_it() -> None:
    model, _, _ = await drive(
        [says(ToolCall("q1", "describe", {"name": "look-before-you-change"})), says(DONE)],
        registry=a_registry(CAREFUL),
        meta=frozenset({"propose", "done", "describe"}),
    )
    answer = tool_answer(model, 1, "q1")
    assert "Before any change" in answer and "look" in answer


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
    model, sink, _ = await drive(
        [says(MINT), says(ToolCall("u1", USE_SKILL, {"name": "triage"})), says(DONE)],
        registry=registry,
        meta=frozenset({"propose", "done", MINT_SKILL}),
    )
    assert "minted" in tool_answer(model, 1, "m1")
    assert offered(model.requests[1], USE_SKILL).input_schema["properties"]["name"]["enum"] == [
        "look-before-you-change",
        "triage",
    ]
    assert "List everything first" in tool_answer(model, 2, "u1")
    minted = await registry.find("triage")
    assert minted is not None and minted.source == "minted"

    kept = [p for p in sink.proposals if p.kind == "skill"]
    assert len(kept) == 1
    assert kept[0].payload == {
        "name": "triage",
        "description": "Sort what came in by urgency before touching any of it.",
        "prompt": "List everything first. Then order by urgency. Only then act on the first.",
        "needs": ["look"],
    }
    assert kept[0].provenance.adapter == "agent"


async def test_minting_is_not_offered_unless_the_pattern_grants_it() -> None:
    model, _, _ = await drive([says(DONE)], registry=a_registry(CAREFUL))
    assert offered(model.requests[0], MINT_SKILL) is None


async def test_minting_is_not_offered_where_there_is_nothing_to_mint_into() -> None:
    """A pattern may grant the verb; a role with no registry still cannot offer it — a verb that
    answers 'nowhere to put that' every time is a verb the model will keep trying."""
    grants = frozenset({"propose", "done", MINT_SKILL})
    model, sink, _ = await drive([says(MINT), says(DONE)], registry=None, meta=grants)
    assert offered(model.requests[0], MINT_SKILL) is None
    assert "no skill registry" in tool_answer(model, 1, "m1")
    assert sink.proposals == []


async def test_a_badly_shaped_mint_is_refused_and_nothing_is_kept() -> None:
    registry = a_registry(CAREFUL)
    bad = ToolCall("m1", MINT_SKILL, {"name": "x", "prompt": "do it"})
    model, sink, _ = await drive(
        [says(bad), says(DONE)], registry=registry, meta=frozenset({"propose", "done", MINT_SKILL})
    )
    assert "description" in tool_answer(model, 1, "m1")
    assert await registry.find("x") is None
    assert [p for p in sink.proposals if p.kind == "skill"] == []


async def test_a_kept_proposal_comes_back_as_a_source_next_run() -> None:
    """The host's half: it kept the proposal — however it keeps things — and hands it back."""
    registry = a_registry(CAREFUL)
    _, sink, _ = await drive(
        [says(MINT), says(DONE)], registry=registry, meta=frozenset({"propose", "done", MINT_SKILL})
    )
    kept = kept_from(sink.proposals[0], source="kept")
    assert kept.name == "triage" and kept.source == "kept" and kept.needs == frozenset({"look"})

    next_run = SkillRegistry((a_registry(kept),))  # a registry is a source; the host composes
    model, _, _ = await drive([says(DONE)], registry=next_run)
    assert "triage — Sort what came in" in offered(model.requests[0], USE_SKILL).description
