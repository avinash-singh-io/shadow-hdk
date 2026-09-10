"""The meta-tools — the model's own verbs, offered by the pattern and never by the runtime (D3).

The runtime knows none of these names. They exist here because *this* adapter is where "the model
proposes" lives; a different agent adapter could offer entirely different verbs and the runtime
would not notice.
"""

from __future__ import annotations

from shadow_hdk.adapters.agent.pattern import COMPOSE, DESCRIBE, DONE, PROPOSE

from shadow_hdk.kernel.components import Interface

DONE_INTERFACE = Interface(
    name=DONE,
    description=(
        "Finish. Say what happened — what you settled, and anything you could not settle."
    ),
    input_schema={
        "type": "object",
        "properties": {"summary": {"type": "string"}},
        "required": ["summary"],
    },
)

PROPOSE_INTERFACE = Interface(
    name=PROPOSE,
    description=(
        "Offer something worth keeping to whoever is listening. It is not stored by you: "
        "the host decides whether to keep it."
    ),
    input_schema={
        "type": "object",
        "properties": {"kind": {"type": "string"}, "payload": {}},
        "required": ["kind", "payload"],
    },
)

COMPOSE_INTERFACE = Interface(
    name=COMPOSE,
    description=(
        "Lay out several steps as a plan instead of calling one tool at a time: a sequence, "
        "things in parallel, or a loop with a stop. The plan runs and you see every result."
    ),
    input_schema={
        "type": "object",
        "properties": {"steps": {"type": "array", "items": {"type": "object"}}},
        "required": ["steps"],
    },
)

DESCRIBE_INTERFACE = Interface(
    name=DESCRIBE,
    description=(
        "Ask what a tool takes. The list you were given has names and one-line descriptions; "
        "this returns the full input schema for one of them."
    ),
    input_schema={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
)

BY_NAME = {
    DESCRIBE: DESCRIBE_INTERFACE,
    DONE: DONE_INTERFACE,
    PROPOSE: PROPOSE_INTERFACE,
    COMPOSE: COMPOSE_INTERFACE,
}

__all__ = [
    "BY_NAME",
    "COMPOSE_INTERFACE",
    "DESCRIBE_INTERFACE",
    "DONE_INTERFACE",
    "PROPOSE_INTERFACE",
]
