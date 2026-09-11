"""What the two halves agree on before anything else.

`specs/architecture/wire.md`: *negotiated at `initialize`, refusing rather than degrading on a
version mismatch.* Degrading is how two peers come to disagree about what a message means while both
believe they are talking — a class of bug that shows up far from its cause.

The method names are split by direction on purpose. Reading them is meant to answer *who asks whom*,
which is the one thing about this protocol that surprises people: the runtime is the **caller** for
four of them.
"""

from __future__ import annotations

from dataclasses import dataclass

PROTOCOL_VERSION = "1"
"""Bumped when a message's meaning changes. Not the package version: a package may release many
times without the wire's vocabulary moving, and a client generated from published schemas cares
about this number rather than ours."""

# host → runtime
INITIALIZE = "initialize"
RUN = "run"
RESUME = "resume"

# runtime → host — the inversion
JUDGE = "governance.judge"
COMPLETE = "model.complete"
REGISTRATIONS = "components.registrations"
INVOKE = "components.invoke"
PROPOSE = "sink.propose"

# host → runtime, from inside a component the host is running on the runtime's behalf
CONTEXT_PROPOSE = "context.propose"
CONTEXT_REMAINING = "context.remaining"
CONTEXT_REASONED = "context.reasoned"
CONTEXT_VISIBLE = "context.visible"
CONTEXT_FLOOR_MET = "context.floor_met"
CONTEXT_ASK = "context.ask"
CONTEXT_KEEP = "context.keep"
CONTEXT_RESUMED = "context.resumed"
CONTEXT_SPAWN = "context.children.spawn"
CONTEXT_SEND = "context.children.send"
CONTEXT_RELEASE = "context.children.release"
CONTEXT_IS_HELD = "context.children.is_held"
"""What a component running on the host asks the run for (D51). Each belongs to the run — the
registry, the meter, the children — and crosses back rather than being answered locally, because
there is one of each and it is on the runtime's side."""

# runtime → host, one way
EVENT = "event"
STEP = "step"
"""The projection, folded runtime-side, one notification per closed step (D46) — so a host in
another language renders agent steps without porting the fold."""

HOST_DRIVES = frozenset({INITIALIZE, RUN, RESUME, CONTEXT_PROPOSE, CONTEXT_REMAINING})
RUNTIME_CALLS_BACK = frozenset({JUDGE, COMPLETE, REGISTRATIONS, INVOKE, PROPOSE})


class WireError(Exception):
    """Something the protocol itself refused."""


class VersionMismatch(WireError):
    """`initialize` was offered a version this build does not speak."""


@dataclass(frozen=True)
class Agreed:
    """What `initialize` settled."""

    protocol_version: str


__all__ = [
    "COMPLETE",
    "CONTEXT_PROPOSE",
    "CONTEXT_REMAINING",
    "EVENT",
    "HOST_DRIVES",
    "INITIALIZE",
    "INVOKE",
    "JUDGE",
    "PROPOSE",
    "PROTOCOL_VERSION",
    "REGISTRATIONS",
    "RESUME",
    "RUN",
    "RUNTIME_CALLS_BACK",
    "Agreed",
    "VersionMismatch",
    "WireError",
]
