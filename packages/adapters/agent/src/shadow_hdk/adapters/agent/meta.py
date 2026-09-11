"""The meta-tools — the model's own verbs, offered by the pattern and never by the runtime (D3).

The runtime knows none of these names. They exist here because *this* adapter is where "the model
proposes" lives; a different agent adapter could offer entirely different verbs and the runtime
would not notice.
"""

from __future__ import annotations

from shadow_hdk.adapters.agent.pattern import (
    COMPACT,
    COMPOSE,
    DESCRIBE,
    DONE,
    PROPOSE,
    RECALL,
    RELEASE,
    SEND,
    SPAWN,
)

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

RECALL_INTERFACE = Interface(
    name=RECALL,
    description=(
        "Read part of a result that was too large to show you whole. You were given its handle, "
        "its size and a preview; ask for a slice by start and length."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "handle": {"type": "string"},
            "start": {"type": "integer", "minimum": 0},
            "length": {"type": "integer", "minimum": 1},
        },
        "required": ["handle"],
    },
)

COMPACT_INTERFACE = Interface(
    name=COMPACT,
    description=(
        "Summarise what has happened so far, when the transcript is getting long. What you write "
        "replaces the middle of it — your role and the original request stay. It is offered to "
        "whoever is listening; it is not yours to keep."
    ),
    input_schema={
        "type": "object",
        "properties": {"summary": {"type": "string"}},
        "required": ["summary"],
    },
)

SPAWN_INTERFACE = Interface(
    name=SPAWN,
    description=(
        "Start a helper and keep it. Name an agent and give it a brief. You get back a handle; "
        "the helper does the brief and then waits, so you can ask it again without repeating "
        "yourself. Let it go with `release` when you are finished with it."
    ),
    input_schema={
        "type": "object",
        "properties": {"agent": {"type": "string"}, "brief": {"type": "string"}},
        "required": ["agent", "brief"],
    },
)

SEND_INTERFACE = Interface(
    name=SEND,
    description="Ask a helper you kept another question. It picks up where it left off.",
    input_schema={
        "type": "object",
        "properties": {"handle": {"type": "string"}, "message": {"type": "string"}},
        "required": ["handle", "message"],
    },
)

RELEASE_INTERFACE = Interface(
    name=RELEASE,
    description="Let a helper go. It stops, and its budget goes back to you.",
    input_schema={
        "type": "object",
        "properties": {"handle": {"type": "string"}},
        "required": ["handle"],
    },
)

BY_NAME = {
    COMPACT: COMPACT_INTERFACE,
    SPAWN: SPAWN_INTERFACE,
    SEND: SEND_INTERFACE,
    RELEASE: RELEASE_INTERFACE,
    DESCRIBE: DESCRIBE_INTERFACE,
    RECALL: RECALL_INTERFACE,
    DONE: DONE_INTERFACE,
    PROPOSE: PROPOSE_INTERFACE,
    COMPOSE: COMPOSE_INTERFACE,
}

__all__ = [
    "BY_NAME",
    "COMPACT_INTERFACE",
    "RELEASE_INTERFACE",
    "SEND_INTERFACE",
    "SPAWN_INTERFACE",
    "COMPOSE_INTERFACE",
    "DESCRIBE_INTERFACE",
    "DONE_INTERFACE",
    "PROPOSE_INTERFACE",
]
