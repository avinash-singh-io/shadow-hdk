"""A skill's needs are checked before the first turn, or they are not checked at all (BUG-012).

`skills.py` says exactly when this happens — *the check runs **before the first turn**, against
`RunContext.visible()`* — and `missing_for` was exported, documented, and called by nothing outside
its own tests. `AgentComponent` had nowhere to put a skill, so there was no first turn for it to run
before. The module's central claim was true of nothing.

Checking early is the whole value. A skill that needs a component the deployment hides will fail
somewhere in the middle of a run, after paying for the turns that got there, and the model will be
left inferring from a refusal what a check could have said in one sentence.

A skill is *not* a permission. Naming a component grants nothing — the check can only ever say no.
"""

from __future__ import annotations

from typing import Any

from shadow_hdk.adapters.agent import AgentComponent, Pattern, Skill
from shadow_hdk.adapters.basic import AllowAll, CallableComponents
from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Completed,
    Composition,
    Event,
    Floor,
    Invoke,
    Lease,
    Observed,
    ScopeSet,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import ModelResponse, ToolCall
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

WORKSPACE = ScopeSet.of("workspace")

RELEASE_NOTES = Skill(
    name="release-notes",
    prompt="Read the changelog, then write the notes in the house style.",
    needs=frozenset({"look"}),
)


def look(topic: str) -> str:
    """Look a topic up."""
    return f"found {topic}"


async def drive(skill: Skill | None) -> tuple[ScriptedModel, list[Event]]:
    tools = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    tools.add(look, effects=EffectProfile(reads=WORKSPACE))
    agent = AgentComponent(
        pattern=Pattern(name="p", system="do the work"),
        effects=EffectProfile(costs=True),
        at="2026-01-01T00:00:00+00:00",
        skill=skill,
    )
    model = ScriptedModel([ModelResponse("ok", (ToolCall("d1", "done", {"summary": "finished"}),))])
    ports = Ports(
        model=model,
        components=(tools, agent),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
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
    return model, events


def outcome(events: list[Event]) -> dict[str, Any]:
    """The agent's own output, which every way this loop ends is a `Completed` dict."""
    observation = [e for e in events if isinstance(e, Observed)][-1].observation
    assert isinstance(observation, Completed)
    assert isinstance(observation.output, dict)
    return observation.output


async def test_a_skill_needing_what_nobody_offers_stops_before_the_model_is_called() -> None:
    """*Before the first turn* is the claim, so what is asserted is that the provider was never
    reached — not merely that the run ended badly. A check that costs a turn to perform has given
    up most of the reason to perform it."""
    model, events = await drive(
        Skill(name="s", prompt="do it", needs=frozenset({"look", "deploy", "invoice"}))
    )

    assert model.requests == [], "the model was called before the skill was checked"
    assert outcome(events)["reason"] == "skill_unmet"


async def test_it_names_what_is_missing_and_not_what_is_present() -> None:
    """One sentence a person can act on. Naming everything the skill wanted would make the reader
    find the difference themselves, and the difference is the whole message."""
    _model, events = await drive(
        Skill(name="s", prompt="do it", needs=frozenset({"look", "deploy", "invoice"}))
    )
    said = str(outcome(events)["text"])

    assert "deploy" in said and "invoice" in said
    assert "look" not in said, f"the message names a component that was offered: {said}"


async def test_a_skill_whose_needs_are_met_runs() -> None:
    model, events = await drive(RELEASE_NOTES)

    assert len(model.requests) == 1
    assert outcome(events)["reason"] == "done"


async def test_the_skill_reaches_the_model_as_part_of_its_instructions() -> None:
    """A skill is a procedure somebody wrote down, and a procedure the model never reads is a file.
    It joins the role prompt rather than replacing it: the pattern says how this role works, the
    skill says what this piece of work is."""
    model, _events = await drive(RELEASE_NOTES)
    system = [m.content for m in model.requests[0].messages if m.role == "system"]

    assert len(system) == 1, "the skill was sent as a second system message"
    assert "do the work" in system[0], "the pattern's own role prompt was lost"
    assert "house style" in system[0], "the skill's procedure never reached the model"


async def test_no_skill_changes_nothing() -> None:
    """The default. Every agent built before this parameter existed behaves as it did."""
    model, events = await drive(None)

    assert [m.content for m in model.requests[0].messages if m.role == "system"] == ["do the work"]
    assert outcome(events)["reason"] == "done"


async def test_a_skill_that_needs_nothing_is_not_a_gate() -> None:
    """`needs` is a declaration of dependency, and an empty one declares none — so a skill that is
    purely a procedure runs anywhere, which is what makes procedures shareable."""
    model, events = await drive(Skill(name="s", prompt="just follow this"))

    assert len(model.requests) == 1
    assert outcome(events)["reason"] == "done"
