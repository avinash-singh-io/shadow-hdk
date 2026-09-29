"""A parked call is reported as a fact about the call, not as an instruction (BUG-228).

Lane P measured this: a key-backed model (DeepSeek V4 Flash) parked a `WriteArtifact` call, and the
turn's answer — shown to the person — was the kit's own parked note, ending *"Say what you proposed
and why, then stop."* Claude Code receives the same sentence as the parked call's error and simply
did not repeat it; a weaker model does.

Two rules come out of it, and they are what these tests pin:

1. **The note is a fact, not a directive.** An observation handed to a model is data about the
   world. A sentence addressed to the model in the second person is an instruction wearing an
   observation's clothes, and a model that reads its tool results back to the person will read that
   out too. Steering belongs in the instruction channel, which is the mode's behaviour.
2. **A turn that ends parked says so in its stop reason,** so a host can speak in its own words
   without parsing, or repeating, anything the kit wrote for a model.
"""

from __future__ import annotations

import re

from shadow_hdk.runtime.offer import PARKED_REASON

SECOND_PERSON = re.compile(r"\b(you|your|yours|yourself)\b", re.IGNORECASE)


def test_the_note_names_the_call_it_is_about() -> None:
    assert "WriteArtifact" in PARKED_REASON.format(name="WriteArtifact")


def test_the_note_addresses_nobody() -> None:
    """The property, not the wording: no second person anywhere in it. A model cannot echo an
    instruction it was never given, and a host that shows a tool result verbatim shows a fact."""
    said = PARKED_REASON.format(name="WriteArtifact")

    assert not SECOND_PERSON.search(said), said


def test_the_note_gives_no_order() -> None:
    """The exact sentence a model read out to a person, and the shape of it."""
    said = PARKED_REASON.format(name="WriteArtifact")

    assert "Say what you proposed" not in said
    assert "then stop" not in said


def test_the_note_still_says_the_call_is_kept_and_has_not_run() -> None:
    """What the model does need to know, and the only reason the note exists: the call did not
    happen, and it was not refused either — so it is not one to make again."""
    said = PARKED_REASON.format(name="WriteArtifact").lower()

    assert "waiting" in said or "not run" in said
    assert "kept" in said


def test_a_parked_turns_own_text_addresses_nobody_either() -> None:
    """What a key-backed model's turn says it did. The kit wrote the agent-facing note here, so
    the product showed an instruction to the person; now the two are separate sentences with
    separate jobs, and neither is aimed at anyone."""
    from shadow_hdk.runtime.offer import PARKED_TURN

    said = PARKED_TURN.format(name="WriteArtifact")

    assert "WriteArtifact" in said
    assert not SECOND_PERSON.search(said), said
    assert said != PARKED_REASON.format(name="WriteArtifact"), "two sentences, two audiences"
