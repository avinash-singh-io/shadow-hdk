"""Events are the only channel out of the runtime (09 §7).

The runtime emits; anyone may observe. A UI renders them, a record derives from them, a meter
charges from them, a replay differ compares two runs of them. ``at`` is text because the kernel
has no clock: the runtime stamps it from its clock port.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import Field, JsonValue

from shadow_hdk.kernel.authority import EffectEntryKind
from shadow_hdk.kernel.components import Posture, RegistrationId
from shadow_hdk.kernel.composition import Composition, Handle, StepId
from shadow_hdk.kernel.leases import Lease
from shadow_hdk.kernel.observations import Observation, Proposal
from shadow_hdk.kernel.planning import PlanLimits, PlanMismatch
from shadow_hdk.kernel.usage import Usage
from shadow_hdk.kernel.workspace import Root

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
class EffectRecorded:
    """One public fact from the append-only transaction history (D101-D104).

    This is deliberately a generic status event rather than one event class per transition. A
    client can render the exact history—including an explicit ``unknown``—without reimplementing
    transaction inference or receiving credentials, callbacks or hidden authorizer state.
    """

    run_id: RunId
    seq: int
    at: str
    step: StepId
    attempt_id: str
    status: EffectEntryKind
    stage_digest: str
    authorization_id: str | None = None
    detail: JsonValue = None
    recorded_at: str = ""
    replayed: bool = False
    kind: Literal["effect_recorded"] = "effect_recorded"


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
class ApprovalRequested:
    run_id: RunId
    seq: int
    at: str
    step: StepId
    question: str
    handle: Handle
    component: str | None = None
    """What the question is about: the component the step would invoke, and its inputs — so the
    person answering can see what they are consenting to. A step is judged before it is invoked,
    so without these the question named a step id and a policy's sentence and nothing else."""
    inputs: JsonValue | None = None
    kind: Literal["approval_requested"] = "approval_requested"


@dataclass(frozen=True)
class InputRequested:
    """The agent asked the person something — not for consent, for an answer (D61).

    Every product that ships an agent has this item (Codex `requestUserInput`, Claude Code's
    `AskUserQuestion`, OpenCode's `question`); ours wrote the question into its prose. On the
    record it is its own kind, answered with text through the host's handle.
    """

    run_id: RunId
    seq: int
    at: str
    step: StepId
    question: str
    handle: Handle
    kind: Literal["input_requested"] = "input_requested"


@dataclass(frozen=True)
class PlanAdmitted:
    """A whole plan admitted before it compiled (D108): its digest, the authority it was admitted
    under, the limits it fit — and whether it amended a plan already running (D116)."""

    run_id: RunId
    seq: int
    at: str
    plan_digest: str
    step: StepId = ""
    authority_digest: str = ""
    limits: PlanLimits = PlanLimits()
    asks: tuple[StepId, ...] = ()
    """The steps the policy will ask about when they run — named now, so a host can present the
    plan's questions as one card and keep rules for them, while each step still asks at its own
    invocation through the proven path (live, parked, or parked on purpose)."""
    refusals: tuple[StepId, ...] = ()
    """The steps the policy will refuse when they run — named now; the step's own refusal, at its
    invocation, is the refusal the planner is told, as it always was (BUG-012)."""
    amendment: bool = False
    kind: Literal["plan_admitted"] = "plan_admitted"


@dataclass(frozen=True)
class PlanRefused:
    """A whole plan refused before anything ran — every mismatch, in the stable order. The
    planner hears this as an observation and decides; nothing was trimmed (D111)."""

    run_id: RunId
    seq: int
    at: str
    plan_digest: str
    step: StepId = ""
    mismatches: tuple[PlanMismatch, ...] = ()
    amendment: bool = False
    kind: Literal["plan_refused"] = "plan_refused"


@dataclass(frozen=True)
class Spawned:
    run_id: RunId
    seq: int
    at: str
    child_run_id: RunId
    lease: Lease
    kind: Literal["spawned"] = "spawned"


@dataclass(frozen=True)
class UsageReported:
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
    kind: Literal["usage"] = "usage"


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


@dataclass(frozen=True)
class Reasoning:
    """What the model thought, on the record beside what it did (D45).

    The stream recorded what an agent did — invoked, observed, refused, asked, spent — and threw
    away what it thought. A model's reasoning is the one thing on a run a person most wants to
    read, and it was the one thing not there.

    Same rule `UsageReported` set: emitted only when there is something to say. A model that
    reports no reasoning emits none. `text` is the model's own words, unedited — the record is not
    the place to summarise.
    """

    run_id: RunId
    seq: int
    at: str
    step: StepId
    text: str
    kind: Literal["reasoning"] = "reasoning"


EndReason = Literal["completed", "lease_exhausted", "gave_up", "cancelled", "failed"]


@dataclass(frozen=True)
class WorkspaceChanged:
    """The thread's roots changed mid-thread (D76) — a directory added while the conversation
    ran — so a reader knows which turns could see which roots."""

    run_id: RunId
    seq: int
    at: str
    roots: tuple[Root, ...]
    kind: Literal["workspace_changed"] = "workspace_changed"


@dataclass(frozen=True)
class ModeChanged:
    """The host changed the run's mode mid-thread (D64) — the record says when, and to what, so a
    reader knows which policy judged the turns that follow."""

    run_id: RunId
    seq: int
    at: str
    mode: str
    kind: Literal["mode_changed"] = "mode_changed"


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
    | EffectRecorded
    | Observed
    | Proposed
    | Refused
    | ApprovalRequested
    | InputRequested
    | Spawned
    | PlanAdmitted
    | PlanRefused
    | Held
    | UsageReported
    | Reasoning
    | ModeChanged
    | WorkspaceChanged
    | Ended,
    Field(discriminator="kind"),
]
