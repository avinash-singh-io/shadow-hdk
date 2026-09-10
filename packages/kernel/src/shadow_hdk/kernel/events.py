"""Events are the only channel out of the runtime (09 §7).

The runtime emits; anyone may observe. A UI renders them, a record derives from them, a meter
charges from them, a replay differ compares two runs of them. ``at`` is text because the kernel
has no clock: the runtime stamps it from its clock port.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import Field, JsonValue

from shadow_hdk.kernel.components import Posture, RegistrationId
from shadow_hdk.kernel.composition import Composition, Handle, StepId
from shadow_hdk.kernel.leases import Lease
from shadow_hdk.kernel.observations import Observation, Proposal
from shadow_hdk.kernel.usage import Usage

RunId = str


@dataclass(frozen=True)
class Started:
    run_id: RunId
    seq: int
    at: str
    lease: Lease
    parent_run_id: RunId | None = None
    kind: Literal["started"] = "started"


@dataclass(frozen=True)
class Composed:
    """What the agent planned — emitted every time the composition changes, so plan-versus-actual
    comes for free."""

    run_id: RunId
    seq: int
    at: str
    composition: Composition
    kind: Literal["composed"] = "composed"


@dataclass(frozen=True)
class Invoked:
    run_id: RunId
    seq: int
    at: str
    step: StepId
    component: RegistrationId
    inputs: JsonValue
    kind: Literal["invoked"] = "invoked"


@dataclass(frozen=True)
class Observed:
    """What a step observed, and the **posture** of what produced it (D30): `controlled` is *we
    gated it before it happened*; `observed` is *evidence recorded after something else acted* —
    attributable, never pre-authorised by us. Stamped by the runtime from the registration, so a
    component cannot claim a posture it does not have."""

    run_id: RunId
    seq: int
    at: str
    step: StepId
    observation: Observation
    posture: Posture = "controlled"
    kind: Literal["observed"] = "observed"


@dataclass(frozen=True)
class Proposed:
    run_id: RunId
    seq: int
    at: str
    proposal: Proposal
    kind: Literal["proposed"] = "proposed"


@dataclass(frozen=True)
class Refused:
    """Governance said no before the step ran."""

    run_id: RunId
    seq: int
    at: str
    step: StepId
    reason: str
    kind: Literal["refused"] = "refused"


@dataclass(frozen=True)
class Asked:
    run_id: RunId
    seq: int
    at: str
    step: StepId
    question: str
    handle: Handle
    kind: Literal["asked"] = "asked"


@dataclass(frozen=True)
class Spawned:
    run_id: RunId
    seq: int
    at: str
    child_run_id: RunId
    lease: Lease
    kind: Literal["spawned"] = "spawned"


@dataclass(frozen=True)
class Spent:
    """What a step cost, said out loud (D20).

    Phase 1 asked that tokens reach the observer. They did not: an adapter *reports* usage inside a
    `Completed` observation's output dict, by convention, and anyone wanting to know what a run cost
    had to know that convention and parse somebody else's payload. Reporting and recording are
    different jobs, and this is the record.

    Emitted only when there is something to say — a step that cost nothing emits none, because a
    kind that appears when there is nothing to report is a kind readers learn to skip.
    """

    run_id: RunId
    seq: int
    at: str
    step: StepId
    usage: Usage
    kind: Literal["spent"] = "spent"


@dataclass(frozen=True)
class Held:
    """A child parked instead of ending, and its parent is keeping it (D16).

    Without this a host would have to infer holding from the *absence* of `Ended` — which a child
    that died silently also looks like. `steps_spent` is what the child cost on the way in; it is
    not a reservation, because a parked run settles what it did not use back to its parent.
    """

    run_id: RunId
    seq: int
    at: str
    child_run_id: RunId
    handle: str
    steps_spent: int
    kind: Literal["held"] = "held"


EndReason = Literal["completed", "lease_exhausted", "gave_up", "cancelled", "failed"]


@dataclass(frozen=True)
class Ended:
    run_id: RunId
    seq: int
    at: str
    reason: EndReason
    steps_taken: int
    detail: str | None = None
    """Why, in the words of whoever stopped it — the host's cancellation reason, the lease's
    complaint, the failing port. Optional because `completed` has nothing to add."""
    kind: Literal["ended"] = "ended"


Event = Annotated[
    Started
    | Composed
    | Invoked
    | Observed
    | Proposed
    | Refused
    | Asked
    | Spawned
    | Held
    | Spent
    | Ended,
    Field(discriminator="kind"),
]
