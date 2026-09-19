// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 3. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type Event = (Started | Composed | Invoked | EffectRecorded | Observed | Proposed | Refused1 | ApprovalRequested | InputRequested | Spawned | PlanAdmitted | PlanRefused | Held | UsageReported | Reasoning | ModeChanged | WorkspaceChanged | Ended)
export type At = string
export type Kind = "started"
export type MaxCostCents = (number | null)
export type MaxSteps = number
export type MaxWallSeconds = number
export type MinSteps = number
export type ParentRunId = (string | null)
export type RunId = string
export type Seq = number
export type At1 = string
export type Component = string
export type Id = string
export type Name = string
export type Ref = (string | null)
export type Inputs = Binding[]
export type Kind1 = "invoke"
export type Component1 = string
export type Id1 = string
export type Inputs1 = Binding[]
export type Kind2 = "await"
export type Id2 = string
export type Kind3 = "sequence"
export type Id3 = string
export type Kind4 = "fan_out"
export type JsonValue = unknown
export type Path = string
export type Id4 = string
export type Kind5 = "until"
export type MaxIterations = number
export type Step = (Invoke | Await | Sequence | FanOut | Until)
export type Steps2 = (Invoke | Await | Sequence | FanOut | Until)[]
export type Steps1 = (Invoke | Await | Sequence | FanOut | Until)[]
export type Steps = (Invoke | Await | Sequence | FanOut | Until)[]
export type Kind6 = "composed"
export type RunId1 = string
export type Seq1 = number
export type At2 = string
export type Component2 = string
export type Kind7 = "invoked"
export type RunId2 = string
export type Seq2 = number
export type Step1 = string
export type At3 = string
export type AttemptId = string
export type AuthorizationId = (string | null)
export type Kind8 = "effect_recorded"
export type RecordedAt = string
export type Replayed = boolean
export type RunId3 = string
export type Seq3 = number
export type StageDigest = string
export type Status = ("staged" | "authorized" | "executing" | "receipt" | "refused" | "failed" | "unknown" | "reconciled")
export type Step2 = string
export type At4 = string
export type Kind9 = "observed"
export type Observation = (Completed | Refused | ApprovalRequest | InputRequest | Failed | Pending | Acted)
export type Kind10 = "completed"
export type Kind11 = "refused"
export type Reason = string
export type Component3 = (string | null)
export type Handle = string
export type Kind12 = "approval_request"
export type Question = string
export type Handle1 = string
export type Kind13 = "input_request"
export type Question1 = string
export type Error = string
export type Kind14 = "failed"
export type Handle2 = string
export type Kind15 = "pending"
export type Exit = string
export type ForeignId = string
export type IdempotencyKey = string
export type Kind16 = "acted"
export type Posture = ("controlled" | "observed")
export type RunId4 = string
export type Seq4 = number
export type Step3 = string
export type At5 = string
export type Kind17 = "proposed"
export type Grounds = string[]
export type Kind18 = string
export type Adapter = string
export type At6 = string
export type Licence = (string | null)
export type Posture1 = ("controlled" | "observed")
export type RegisteredBy = string
export type Signature = (string | null)
export type SignedBy = (string | null)
export type RunId5 = string
export type Seq5 = number
export type At7 = string
export type Kind19 = "refused"
export type Reason1 = string
export type RunId6 = string
export type Seq6 = number
export type Step4 = string
export type At8 = string
export type Component4 = (string | null)
export type Handle3 = string
export type Kind20 = "approval_requested"
export type Question2 = string
export type RunId7 = string
export type Seq7 = number
export type Step5 = string
export type At9 = string
export type Handle4 = string
export type Kind21 = "input_requested"
export type Question3 = string
export type RunId8 = string
export type Seq8 = number
export type Step6 = string
export type At10 = string
export type ChildRunId = string
export type Kind22 = "spawned"
export type RunId9 = string
export type Seq9 = number
export type Amendment = boolean
export type Asks = string[]
export type At11 = string
export type AuthorityDigest = string
export type Kind23 = "plan_admitted"
export type Depth = (number | null)
export type FanOut1 = (number | null)
export type Steps3 = (number | null)
export type PlanDigest = string
export type Refusals = string[]
export type RunId10 = string
export type Seq10 = number
export type Step7 = string
export type Amendment1 = boolean
export type At12 = string
export type Kind24 = "plan_refused"
export type Axis = ("depth" | "fan_out" | "steps" | "component")
export type Found = string
export type Required = string
export type Step8 = string
export type Mismatches = PlanMismatch[]
export type PlanDigest1 = string
export type RunId11 = string
export type Seq11 = number
export type Step9 = string
export type At13 = string
export type ChildRunId1 = string
export type Handle5 = string
export type Kind25 = "held"
export type RunId12 = string
export type Seq12 = number
export type StepsSpent = number
export type At14 = string
export type Kind26 = "usage"
export type RunId13 = string
export type Seq13 = number
export type Step10 = string
export type CacheReadTokens = (number | null)
export type CacheWriteTokens = (number | null)
export type CostCents = (number | null)
export type InputTokens = (number | null)
export type OutputTokens = (number | null)
export type At15 = string
export type Kind27 = "reasoning"
export type RunId14 = string
export type Seq14 = number
export type Step11 = string
export type Text = string
export type At16 = string
export type Kind28 = "mode_changed"
export type Mode = string
export type RunId15 = string
export type Seq15 = number
export type At17 = string
export type Kind29 = "workspace_changed"
export type Name1 = string
export type Path1 = string
export type Roots = Root[]
export type RunId16 = string
export type Seq16 = number
export type At18 = string
export type Detail = (string | null)
export type Kind30 = "ended"
export type Reason2 = ("completed" | "lease_exhausted" | "gave_up" | "cancelled" | "failed")
export type RunId17 = string
export type Seq17 = number
export type StepsTaken = number

export interface Started {
at: At
kind?: Kind
lease: Lease
parent_run_id?: ParentRunId
run_id: RunId
seq: Seq
}
export interface Lease {
ceiling: Ceiling
floor?: Floor
}
export interface Ceiling {
max_cost_cents?: MaxCostCents
max_steps: MaxSteps
max_wall_seconds: MaxWallSeconds
}
export interface Floor {
min_steps?: MinSteps
}
/**
 * What the agent planned — emitted every time the composition changes, so plan-versus-actual
 * comes for free.
 */
export interface Composed {
at: At1
composition: Composition
kind?: Kind6
run_id: RunId1
seq: Seq1
}
/**
 * A first-class value: visible while it runs, changeable mid-flight, emitted as an event.
 */
export interface Composition {
steps?: Steps
}
export interface Invoke {
component: Component
id: Id
inputs?: Inputs
kind?: Kind1
}
/**
 * One input: either a literal value or a reference to an earlier step's output by handle.
 */
export interface Binding {
name: Name
ref?: Ref
value?: unknown
}
/**
 * Wait for something slow — a person, a job. Compiles to an interrupt.
 */
export interface Await {
component: Component1
id: Id1
inputs?: Inputs1
kind?: Kind2
}
export interface Sequence {
id: Id2
kind?: Kind3
steps?: Steps1
}
export interface FanOut {
id: Id3
kind?: Kind4
steps?: Steps2
}
/**
 * Loop with a stop: repeat ``step`` until ``condition`` holds, at most ``max_iterations``.
 */
export interface Until {
condition: Condition
id: Id4
kind?: Kind5
max_iterations: MaxIterations
step: Step
}
/**
 * A total, non-looping test over the last observation's output: ``output[path] == equals``.
 */
export interface Condition {
equals: JsonValue
path: Path
}
export interface Invoked {
at: At2
component: Component2
inputs: JsonValue
kind?: Kind7
run_id: RunId2
seq: Seq2
step: Step1
}
/**
 * One public fact from the append-only transaction history (D101-D104).
 *
 * This is deliberately a generic status event rather than one event class per transition. A
 * client can render the exact history—including an explicit ``unknown``—without reimplementing
 * transaction inference or receiving credentials, callbacks or hidden authorizer state.
 */
export interface EffectRecorded {
at: At3
attempt_id: AttemptId
authorization_id?: AuthorizationId
detail?: {
[k: string]: unknown
}
kind?: Kind8
recorded_at?: RecordedAt
replayed?: Replayed
run_id: RunId3
seq: Seq3
stage_digest: StageDigest
status: Status
step: Step2
}
/**
 * What a step observed, and the **posture** of what produced it (D30): `controlled` is *we
 * gated it before it happened*; `observed` is *evidence recorded after something else acted* —
 * attributable, never pre-authorised by us. Stamped by the runtime from the registration, so a
 * component cannot claim a posture it does not have.
 */
export interface Observed {
at: At4
kind?: Kind9
observation: Observation
posture?: Posture
run_id: RunId4
seq: Seq4
step: Step3
}
export interface Completed {
kind?: Kind10
output?: {
[k: string]: unknown
}
}
export interface Refused {
kind?: Kind11
reason: Reason
}
/**
 * The step paused; whoever implements governance decides what asking means.
 *
 * `component` and `inputs` say what the question is about (BUG-026) — an agent surfacing a
 * child's question passes on what that child was about to do, so the person sees it.
 */
export interface ApprovalRequest {
component?: Component3
handle: Handle
inputs?: unknown
kind?: Kind12
question: Question
}
/**
 * The step paused for the person's answer to a question of the agent's own (D61).
 */
export interface InputRequest {
handle: Handle1
kind?: Kind13
question: Question1
}
export interface Failed {
error: Error
kind?: Kind14
}
/**
 * The answer arrives later, under this handle.
 */
export interface Pending {
handle: Handle2
kind?: Kind15
}
/**
 * The receipt of a world-effect (`08` §249: `ActReceipt`). *The only place anything happens
 * outside the log* — so every one of them is attributed and re-checkable.
 *
 * `foreign_id` is what the world called it; `idempotency_key` is what we called it, so a retry
 * can be told from a second act; `exit` is how it ended in the world's own vocabulary; `grounds`
 * is what it was performed under — the argv, the lease remaining, the warrant — so an auditor can
 * ask not only *what happened* but *on whose authority at that moment*.
 */
export interface Acted {
exit: Exit
foreign_id: ForeignId
grounds?: {
[k: string]: unknown
}
idempotency_key: IdempotencyKey
kind?: Kind16
}
export interface Proposed {
at: At5
kind?: Kind17
proposal: Proposal
run_id: RunId5
seq: Seq5
}
/**
 * What the runtime hands to the sink. It proposes; it never commits anything anywhere.
 */
export interface Proposal {
grounds?: Grounds
kind: Kind18
payload: JsonValue
provenance: Provenance
}
/**
 * Who registered it, what adapter it came through, who signed it, when — and whether we could
 * have stopped it.
 *
 * ``at`` is whatever the registering side's clock said, as text — the kernel has no clock.
 * ``licence`` is recorded here because an open-source component is whatever it is, behind an
 * adapter, with its licence in provenance (09 §4).
 *
 * ``posture`` defaults to ``controlled`` because everything the runtime invokes, it gated. The
 * exception has to be explicit: an adapter that forgets to say produces a claim that is true of
 * everything the runtime does.
 */
export interface Provenance {
adapter: Adapter
at: At6
licence?: Licence
posture?: Posture1
registered_by: RegisteredBy
signature?: Signature
signed_by?: SignedBy
}
/**
 * Governance said no before the step ran.
 */
export interface Refused1 {
at: At7
kind?: Kind19
reason: Reason1
run_id: RunId6
seq: Seq6
step: Step4
}
export interface ApprovalRequested {
at: At8
component?: Component4
handle: Handle3
inputs?: unknown
kind?: Kind20
question: Question2
run_id: RunId7
seq: Seq7
step: Step5
}
/**
 * The agent asked the person something — not for consent, for an answer (D61).
 *
 * Every product that ships an agent has this item (Codex `requestUserInput`, Claude Code's
 * `AskUserQuestion`, OpenCode's `question`); ours wrote the question into its prose. On the
 * record it is its own kind, answered with text through the host's handle.
 */
export interface InputRequested {
at: At9
handle: Handle4
kind?: Kind21
question: Question3
run_id: RunId8
seq: Seq8
step: Step6
}
export interface Spawned {
at: At10
child_run_id: ChildRunId
kind?: Kind22
lease: Lease
run_id: RunId9
seq: Seq9
}
/**
 * A whole plan admitted before it compiled (D108): its digest, the authority it was admitted
 * under, the limits it fit — and whether it amended a plan already running (D116).
 */
export interface PlanAdmitted {
amendment?: Amendment
asks?: Asks
at: At11
authority_digest?: AuthorityDigest
kind?: Kind23
limits?: PlanLimits
plan_digest: PlanDigest
refusals?: Refusals
run_id: RunId10
seq: Seq10
step?: Step7
}
/**
 * How much plan a host, a mode or a parent admits. `None` is unbounded.
 *
 * Order-bearing, like an effect profile: `meet` takes the narrower of each field, so limits
 * compose without a review and the narrowing proof covers them.
 */
export interface PlanLimits {
depth?: Depth
fan_out?: FanOut1
steps?: Steps3
}
/**
 * A whole plan refused before anything ran — every mismatch, in the stable order. The
 * planner hears this as an observation and decides; nothing was trimmed (D111).
 */
export interface PlanRefused {
amendment?: Amendment1
at: At12
kind?: Kind24
mismatches?: Mismatches
plan_digest: PlanDigest1
run_id: RunId11
seq: Seq11
step?: Step9
}
/**
 * One way a plan does not fit, as data a host or a planner can act on.
 */
export interface PlanMismatch {
axis: Axis
found: Found
required: Required
step: Step8
}
/**
 * A child parked instead of ending, and its parent is keeping it (D16).
 *
 * Without this a host would have to infer holding from the *absence* of `Ended` — which a child
 * that died silently also looks like. `steps_spent` is what the child cost on the way in; it is
 * not a reservation, because a parked run settles what it did not use back to its parent.
 */
export interface Held {
at: At13
child_run_id: ChildRunId1
handle: Handle5
kind?: Kind25
run_id: RunId12
seq: Seq12
steps_spent: StepsSpent
}
/**
 * What a step cost, said out loud (D20).
 *
 * Phase 1 asked that tokens reach the observer. They did not: an adapter *reports* usage inside a
 * `Completed` observation's output dict, by convention, and anyone wanting to know what a run cost
 * had to know that convention and parse somebody else's payload. Reporting and recording are
 * different jobs, and this is the record.
 *
 * Emitted only when there is something to say — a step that cost nothing emits none, because a
 * kind that appears when there is nothing to report is a kind readers learn to skip.
 */
export interface UsageReported {
at: At14
kind?: Kind26
run_id: RunId13
seq: Seq13
step: Step10
usage: Usage
}
/**
 * What the call cost. A model adapter that cannot say reports ``None`` for the field it does
 * not know — *unknown*, never zero (10 §5 R2).
 */
export interface Usage {
cache_read_tokens?: CacheReadTokens
cache_write_tokens?: CacheWriteTokens
cost_cents?: CostCents
input_tokens?: InputTokens
output_tokens?: OutputTokens
}
/**
 * What the model thought, on the record beside what it did (D45).
 *
 * The stream recorded what an agent did — invoked, observed, refused, asked, spent — and threw
 * away what it thought. A model's reasoning is the one thing on a run a person most wants to
 * read, and it was the one thing not there.
 *
 * Same rule `UsageReported` set: emitted only when there is something to say. A model that
 * reports no reasoning emits none. `text` is the model's own words, unedited — the record is not
 * the place to summarise.
 */
export interface Reasoning {
at: At15
kind?: Kind27
run_id: RunId14
seq: Seq14
step: Step11
text: Text
}
/**
 * The host changed the run's mode mid-thread (D64) — the record says when, and to what, so a
 * reader knows which policy judged the turns that follow.
 */
export interface ModeChanged {
at: At16
kind?: Kind28
mode: Mode
run_id: RunId15
seq: Seq15
}
/**
 * The thread's roots changed mid-thread (D76) — a directory added while the conversation
 * ran — so a reader knows which turns could see which roots.
 */
export interface WorkspaceChanged {
at: At17
kind?: Kind29
roots: Roots
run_id: RunId16
seq: Seq16
}
/**
 * One directory a thread works on, and the name it is addressed by.
 */
export interface Root {
name: Name1
path: Path1
}
export interface Ended {
at: At18
detail?: Detail
kind?: Kind30
reason: Reason2
run_id: RunId17
seq: Seq17
steps_taken: StepsTaken
}
