"""A big catalogue is names until the model asks for more — D13's fourth mechanism.

D13: *above a threshold (a setting, default ~30) the model sees names and one-line descriptions and
pulls a schema on demand with `describe`.* Below the threshold nothing changes, because a catalogue
small enough to read whole is cheaper read whole than fetched twice.

`describe` is a **meta-tool**, which is to say the pattern's and never the runtime's (D3). It also
cannot answer for something the policy hides: the catalogue is `visible()`, and a describe that
reached past it would be a way to read the registry a mode had closed.
"""

from __future__ import annotations

import pytest

from shadow_hdk.adapters.agent import DESCRIBE, Pattern, describe_for, thin
from shadow_hdk.kernel.components import Interface
from shadow_hdk.runtime.testing import make_registration

ROLE = "You are working on one task, using the tools you are given, and you may ask about them."


def _some(count: int) -> list[object]:
    return [
        make_registration(
            f"tool_{index}",
            description=f"Does the {index}th thing.",
            input_schema={
                "type": "object",
                "properties": {"topic": {"type": "string"}},
                "required": ["topic"],
            },
        )
        for index in range(count)
    ]


def _pattern(threshold: int = 30) -> Pattern:
    return Pattern(name="p", system=ROLE, catalogue_threshold=threshold)


def test_a_catalogue_under_the_threshold_keeps_its_schemas() -> None:
    """Nothing changes below the line: a small catalogue is cheaper read whole."""
    shown = thin([r.component.interface for r in _some(29)], _pattern())  # type: ignore[attr-defined]
    assert len(shown) == 29
    assert all(interface.input_schema.get("properties") for interface in shown)


def test_a_catalogue_over_the_threshold_is_names_and_one_liners() -> None:
    shown = thin([r.component.interface for r in _some(31)], _pattern())  # type: ignore[attr-defined]
    assert len(shown) == 31, "thinning must not drop a component, only its schema"
    assert [interface.name for interface in shown] == [f"tool_{i}" for i in range(31)]
    assert all(not interface.input_schema.get("properties") for interface in shown)
    assert all("Does the" in (interface.description or "") for interface in shown), (
        "the one-line description is the whole point of the thinned form"
    )
    # A thinned entry is **a name and a line** — not a line plus one sentence two hundred times.
    # How to get the schema back is said once, on `describe` itself, which the loop offers whenever
    # it thins (Phase 21). This used to assert the sentence per entry, and was measured to make it a
    # third of a two-hundred-tool catalogue.
    assert all(DESCRIBE not in (interface.description or "") for interface in shown), (
        "the how-to-ask sentence is repeated per entry"
    )


def test_the_threshold_is_a_setting() -> None:
    """Default 30 (D13), and a pattern file may say otherwise."""
    assert _pattern().catalogue_threshold == 30
    shown = thin([r.component.interface for r in _some(5)], _pattern(threshold=4))  # type: ignore[attr-defined]
    assert all(not interface.input_schema.get("properties") for interface in shown)


def test_describe_brings_one_schema_back() -> None:
    visible = _some(31)
    answer = describe_for("tool_7", visible)  # type: ignore[arg-type]
    assert isinstance(answer, Interface)
    assert answer.name == "tool_7"
    assert answer.input_schema["required"] == ["topic"]


@pytest.mark.parametrize("asked", ["tool_99", ""], ids=["not registered", "nothing"])
def test_describe_cannot_answer_for_what_is_not_visible(asked: str) -> None:
    """The catalogue is `visible()`, so a describe that reached past it would be a way to read a
    registry the mode had closed. It answers with a refusal a model can read, not with a schema."""
    answer = describe_for(asked, _some(31))  # type: ignore[arg-type]
    assert isinstance(answer, str)
    assert asked in answer or "no component" in answer


async def test_the_loop_answers_a_describe_from_what_the_policy_left() -> None:
    """End to end through the agent loop, because the wiring is where this can quietly not work.

    The model asks about `search`, gets a schema back as a tool result, and finishes. The catalogue
    itself is small here — thinning is tested above — so what this proves is that the verb is
    dispatched, answered, and put where the model will read it.
    """
    from shadow_hdk.adapters.agent import Pattern as P
    from shadow_hdk.kernel.ports import ModelResponse, ToolCall
    from tests.adapters.agent.test_agent import drive_agent

    asking = P(name="asks", system=ROLE, meta_tools=frozenset({DESCRIBE, "done"}))
    _events, model, _sink = await drive_agent(
        [
            ModelResponse("let me check", (ToolCall("c1", DESCRIBE, {"name": "search"}),)),
            ModelResponse("that will do", (ToolCall("c2", "done", {"summary": "asked"}),)),
        ],
        pattern=asking,
    )
    second_turn = model.requests[1]
    answers = [m.content for m in second_turn.messages if m.role == "tool"]
    assert answers, "the describe was never answered"
    assert "query" in answers[-1], answers[-1]


async def test_a_describe_for_something_the_policy_hid_is_a_sentence_not_a_schema() -> None:
    from shadow_hdk.adapters.agent import Pattern as P
    from shadow_hdk.kernel.ports import ModelResponse, ToolCall
    from tests.adapters.agent.test_agent import drive_agent

    asking = P(name="asks", system=ROLE, meta_tools=frozenset({DESCRIBE, "done"}))
    _events, model, _sink = await drive_agent(
        [
            ModelResponse("let me check", (ToolCall("c1", DESCRIBE, {"name": "launch_missiles"}),)),
            ModelResponse("fine", (ToolCall("c2", "done", {"summary": "asked"}),)),
        ],
        pattern=asking,
    )
    answers = [m.content for m in model.requests[1].messages if m.role == "tool"]
    assert answers and "launch_missiles" in answers[-1]
    assert "properties" not in answers[-1], "a hidden component still handed back a schema"


async def test_the_catalogue_the_model_is_offered_is_thinned_above_the_threshold() -> None:
    """The wiring, not the function. `thin` is tested above; this proves the loop actually uses it,
    which a mutation showed nothing else did — the catalogue could have gone out whole."""
    from shadow_hdk.adapters.agent import Pattern as P
    from shadow_hdk.kernel.ports import ModelResponse, ToolCall
    from tests.adapters.agent.test_agent import drive_agent

    # Two tools are registered, so a threshold of two puts this catalogue over the line.
    crowded = P(name="crowded", system=ROLE, meta_tools=frozenset({"done"}), catalogue_threshold=2)
    _events, model, _sink = await drive_agent(
        [ModelResponse("nothing to do", (ToolCall("c1", "done", {"summary": "looked"}),))],
        pattern=crowded,
    )
    offered = {i.name: i for i in model.requests[0].tools}
    assert "search" in offered, "thinning dropped a component"
    assert not offered["search"].input_schema.get("properties"), "the catalogue went out whole"
    # The way to ask is said **once, on the verb**, never per entry (Phase 21): this test used to
    # assert the sentence on every one-liner, and over two hundred tools that sentence was a third
    # of the catalogue. The verb is offered instead — whether or not this pattern enabled it.
    assert DESCRIBE not in (offered["search"].description or "")
    assert DESCRIBE in offered, "thinned without the verb that fetches the rest"
    # The model's own verbs are never thinned: a verb it has to ask about is one it will not use.
    assert offered["done"].input_schema.get("properties"), "a meta-tool was thinned"
