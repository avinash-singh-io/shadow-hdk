"""`ask_person`: the agent's own question to the person, as a component (D65).

Every product that ships an agent has this item — Codex's `requestUserInput`, Claude Code's
`AskUserQuestion`, OpenCode's `question` — and ours wrote the question into its prose. As a
component it is offered like any tool, declares **no effects** (asking changes nothing in the
world, so every mode offers it), puts `InputRequested` on the record where it was asked, and
waits on the host's handle for text. Nobody there is a failure that says so, never an invented
answer.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import JsonValue

from shadow_hdk.kernel import (
    Completed,
    Component,
    EffectProfile,
    Failed,
    Interface,
    Observation,
    Provenance,
    Refused,
    Registration,
)
from shadow_hdk.kernel.ports import ComponentPort
from shadow_hdk.runtime.approvals import Parked
from shadow_hdk.runtime.bindings import current_run

ASK_PERSON = "ask_person"
PARKED_INPUT_REASON = (
    "not now: your question {question!r} is kept for the person, who will answer on a later "
    "request — you will be told what they said at your next turn. Say what you asked and why, "
    "then stop."
)


class PersonComponents(ComponentPort):
    """One component: `ask_person(question) -> {answer}`."""

    def __init__(self, *, at: str = "2026-09-12T00:00:00+00:00") -> None:
        self._registration = Registration(
            id=ASK_PERSON,
            component=Component(
                interface=Interface(
                    name=ASK_PERSON,
                    description=(
                        "Ask the person a question and wait for their answer. Use it when you "
                        "cannot proceed without a decision only they can make."
                    ),
                    input_schema={
                        "type": "object",
                        "properties": {"question": {"type": "string"}},
                        "required": ["question"],
                    },
                    output_schema={
                        "type": "object",
                        "properties": {"answer": {"type": "string"}},
                    },
                ),
                effects=EffectProfile(),
                provenance=Provenance(registered_by="runtime", adapter="person", at=at),
                labels=frozenset({"tool", "person"}),
            ),
        )

    async def registrations(self) -> Sequence[Registration]:
        return [self._registration]

    async def invoke(self, registration: str, inputs: JsonValue) -> Observation:
        if registration != ASK_PERSON:
            return Failed(f"no component registered as {registration!r}")
        question = str(inputs.get("question", "")) if isinstance(inputs, dict) else ""
        if not question:
            return Failed("ask_person needs a question")
        context = current_run()
        if context is None:
            return Failed("ask_person runs inside a run, and there is none")
        answered = await context.request_input(question)
        if answered is None:
            return Failed("nobody was there to answer: the run has no Approvals handle")
        if isinstance(answered, Parked):
            # **Kept, not answered** (D88, BUG-044): the person will answer on a later request
            # and the agent hears it then, folded ahead of its next prompt — never as this
            # call's output.
            return Refused(PARKED_INPUT_REASON.format(question=question))
        return Completed({"answer": answered})


def person_components() -> PersonComponents:
    return PersonComponents()


__all__ = ["ASK_PERSON", "PersonComponents", "person_components"]
