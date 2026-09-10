"""Feedback is what every component already produces (09 §6).

Every invocation returns one ``Observation``. A test runner, a grader, a rubric and a person are
components; their verdicts are observations like any other. There is no feedback subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Literal

from pydantic import Field, JsonValue

from shadow_hdk.kernel.components import Provenance
from shadow_hdk.kernel.composition import Handle


@dataclass(frozen=True)
class Completed:
    output: JsonValue = None
    kind: Literal["completed"] = "completed"


@dataclass(frozen=True)
class Refused:
    reason: str
    kind: Literal["refused"] = "refused"


@dataclass(frozen=True)
class Asked:
    """The step paused; whoever implements governance decides what asking means."""

    question: str
    handle: Handle
    kind: Literal["asked"] = "asked"


@dataclass(frozen=True)
class Failed:
    error: str
    kind: Literal["failed"] = "failed"


@dataclass(frozen=True)
class Acted:
    """The receipt of a world-effect (`08` §249: `ActReceipt`). *The only place anything happens
    outside the log* — so every one of them is attributed and re-checkable.

    `foreign_id` is what the world called it; `idempotency_key` is what we called it, so a retry
    can be told from a second act; `exit` is how it ended in the world's own vocabulary; `grounds`
    is what it was performed under — the argv, the lease remaining, the warrant — so an auditor can
    ask not only *what happened* but *on whose authority at that moment*.
    """

    foreign_id: str
    idempotency_key: str
    exit: str
    grounds: JsonValue = None
    kind: Literal["acted"] = "acted"


@dataclass(frozen=True)
class Pending:
    """The answer arrives later, under this handle."""

    handle: Handle
    kind: Literal["pending"] = "pending"


Observation = Annotated[
    Completed | Refused | Asked | Failed | Pending | Acted, Field(discriminator="kind")
]


@dataclass(frozen=True)
class Proposal:
    """What the runtime hands to the sink. It proposes; it never commits anything anywhere."""

    kind: str
    payload: JsonValue
    provenance: Provenance
    grounds: tuple[Handle, ...] = field(default_factory=tuple)
