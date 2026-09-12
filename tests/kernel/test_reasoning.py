"""Thinking is on the record (D45): the twelfth event kind.

The stream recorded what an agent did and threw away what it thought. A model's reasoning — the
thinking a provider streams before it reaches for a tool — is the one thing on a run a person most
wants to read, and it is the one thing that was not there.

Same rule `UsageReported` set (D20): emitted only when there is something to say. A model that
reports no reasoning emits none, because a kind that appears when there is nothing to report is
a kind readers learn to skip.

Two contract changes carry it: `Reasoning` itself, and a `reasoning` field on `ModelResponse`,
`ModelChunk` and `Turn`, each defaulting empty so no adapter that never heard of it breaks — D14's
argument for a *method* applied to a *field*.
"""

from __future__ import annotations

from shadow_hdk.kernel import Event, ModelChunk, ModelResponse, Reasoning, Turn
from shadow_hdk.kernel.contracts import round_trip


def test_reasoned_is_an_event_kind() -> None:
    thought = Reasoning(run_id="r", seq=3, at="t", step="plan", text="the lathe is on line 3")

    assert thought.kind == "reasoning"
    assert thought.text == "the lathe is on line 3"
    assert thought.step == "plan"


def test_reasoned_is_in_the_union_and_round_trips() -> None:
    """A host in another language reads it off the wire like any other kind."""
    thought = Reasoning(run_id="r", seq=3, at="t", step="plan", text="hmm")

    assert round_trip(thought, Event) == thought


def test_there_are_twelve_kinds() -> None:
    """Eleven was the number in every document; this is the count, held."""
    from typing import get_args

    members = get_args(get_args(Event)[0])
    kinds = {member.__dataclass_fields__["kind"].default for member in members}

    assert "reasoning" in kinds
    assert len(kinds) == 13, sorted(
        kinds
    )  # reasoning was the twelfth; input_requested (D61) the thirteenth


def test_a_response_carries_reasoning_and_defaults_to_none() -> None:
    """The field exists, and an adapter that never heard of it produces a response that reads as
    *did not reason* rather than failing to construct."""
    assert ModelResponse().reasoning == ""
    assert (
        ModelResponse(text="12kg", reasoning="the handbook says so").reasoning
        == "the handbook says so"
    )
    assert ModelChunk().reasoning == ""
    assert Turn().reasoning == ""


def test_a_chunk_of_reasoning_is_a_delta() -> None:
    """Like `text`: the pieces concatenate to the whole, never accumulate."""
    pieces = [ModelChunk(reasoning="the "), ModelChunk(reasoning="lathe"), ModelChunk(done=True)]

    assert "".join(p.reasoning for p in pieces) == "the lathe"
