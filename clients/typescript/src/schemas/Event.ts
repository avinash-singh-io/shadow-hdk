// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 2. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type Event = (Started | Composed | Invoked | Observed | Proposed | Refused1 | ApprovalRequested | InputRequested | Spawned | Held | UsageReported | Reasoning | ModeChanged | WorkspaceChanged | Ended)
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
export type Kind8 = "observed"
export type Observation = (Completed | Refused | ApprovalRequest | InputRequest | Failed | Pending | Acted)
export type Kind9 = "completed"
export type Kind10 = "refused"
export type Reason = string
export type Component3 = (string | null)
export type Handle = string
export type Kind11 = "approval_request"
export type Question = string
export type Handle1 = string
export type Kind12 = "input_request"
export type Question1 = string
export type Error = string
export type Kind13 = "failed"
export type Handle2 = string
export type Kind14 = "pending"
export type Exit = string
export type ForeignId = string
export type IdempotencyKey = string
export type Kind15 = "acted"
export type Posture = ("controlled" | "observed")
export type RunId3 = string
export type Seq3 = number
export type Step2 = string
export type At4 = string
export type Kind16 = "proposed"
export type Grounds = string[]
export type Kind17 = string
export type Adapter = string
export type At5 = string
export type Licence = (string | null)
export type Posture1 = ("controlled" | "observed")
export type RegisteredBy = string
export type Signature = (string | null)
export type SignedBy = (string | null)
export type RunId4 = string
export type Seq4 = number
export type At6 = string
export type Kind18 = "refused"
export type Reason1 = string
export type RunId5 = string
export type Seq5 = number
export type Step3 = string
export type At7 = string
export type Component4 = (string | null)
export type Handle3 = string
export type Kind19 = "approval_requested"
export type Question2 = string
export type RunId6 = string
export type Seq6 = number
export type Step4 = string
export type At8 = string
export type Handle4 = string
export type Kind20 = "input_requested"
export type Question3 = string
export type RunId7 = string
export type Seq7 = number
export type Step5 = string
export type At9 = string
export type ChildRunId = string
export type Kind21 = "spawned"
export type RunId8 = string
export type Seq8 = number
export type At10 = string
export type ChildRunId1 = string
export type Handle5 = string
export type Kind22 = "held"
export type RunId9 = string
export type Seq9 = number
export type StepsSpent = number
export type At11 = string
export type Kind23 = "usage"
export type RunId10 = string
export type Seq10 = number
export type Step6 = string
export type CostCents = (number | null)
export type InputTokens = (number | null)
export type OutputTokens = (number | null)
export type At12 = string
export type Kind24 = "reasoning"
export type RunId11 = string
export type Seq11 = number
export type Step7 = string
export type Text = string
export type At13 = string
export type Kind25 = "mode_changed"
export type Mode = string
export type RunId12 = string
export type Seq12 = number
export type At14 = string
export type Kind26 = "workspace_changed"
export type Name1 = string
export type Path1 = string
export type Roots = Root[]
export type RunId13 = string
export type Seq13 = number
export type At15 = string
export type Detail = (string | null)
export type Kind27 = "ended"
export type Reason2 = ("completed" | "lease_exhausted" | "gave_up" | "cancelled" | "failed")
export type RunId14 = string
export type Seq14 = number
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
 * What a step observed, and the **posture** of what produced it (D30): `controlled` is *we
 * gated it before it happened*; `observed` is *evidence recorded after something else acted* —
 * attributable, never pre-authorised by us. Stamped by the runtime from the registration, so a
 * component cannot claim a posture it does not have.
 */
export interface Observed {
at: At3
kind?: Kind8
observation: Observation
posture?: Posture
run_id: RunId3
seq: Seq3
step: Step2
}
export interface Completed {
kind?: Kind9
output?: {
[k: string]: unknown
}
}
export interface Refused {
kind?: Kind10
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
kind?: Kind11
question: Question
}
/**
 * The step paused for the person's answer to a question of the agent's own (D61).
 */
export interface InputRequest {
handle: Handle1
kind?: Kind12
question: Question1
}
export interface Failed {
error: Error
kind?: Kind13
}
/**
 * The answer arrives later, under this handle.
 */
export interface Pending {
handle: Handle2
kind?: Kind14
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
kind?: Kind15
}
export interface Proposed {
at: At4
kind?: Kind16
proposal: Proposal
run_id: RunId4
seq: Seq4
}
/**
 * What the runtime hands to the sink. It proposes; it never commits anything anywhere.
 */
export interface Proposal {
grounds?: Grounds
kind: Kind17
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
at: At5
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
at: At6
kind?: Kind18
reason: Reason1
run_id: RunId5
seq: Seq5
step: Step3
}
export interface ApprovalRequested {
at: At7
component?: Component4
handle: Handle3
inputs?: unknown
kind?: Kind19
question: Question2
run_id: RunId6
seq: Seq6
step: Step4
}
/**
 * The agent asked the person something — not for consent, for an answer (D61).
 *
 * Every product that ships an agent has this item (Codex `requestUserInput`, Claude Code's
 * `AskUserQuestion`, OpenCode's `question`); ours wrote the question into its prose. On the
 * record it is its own kind, answered with text through the host's handle.
 */
export interface InputRequested {
at: At8
handle: Handle4
kind?: Kind20
question: Question3
run_id: RunId7
seq: Seq7
step: Step5
}
export interface Spawned {
at: At9
child_run_id: ChildRunId
kind?: Kind21
lease: Lease
run_id: RunId8
seq: Seq8
}
/**
 * A child parked instead of ending, and its parent is keeping it (D16).
 *
 * Without this a host would have to infer holding from the *absence* of `Ended` — which a child
 * that died silently also looks like. `steps_spent` is what the child cost on the way in; it is
 * not a reservation, because a parked run settles what it did not use back to its parent.
 */
export interface Held {
at: At10
child_run_id: ChildRunId1
handle: Handle5
kind?: Kind22
run_id: RunId9
seq: Seq9
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
at: At11
kind?: Kind23
run_id: RunId10
seq: Seq10
step: Step6
usage: Usage
}
/**
 * What the call cost. A model adapter that cannot say reports ``None`` for the field it does
 * not know — *unknown*, never zero (10 §5 R2).
 */
export interface Usage {
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
at: At12
kind?: Kind24
run_id: RunId11
seq: Seq11
step: Step7
text: Text
}
/**
 * The host changed the run's mode mid-thread (D64) — the record says when, and to what, so a
 * reader knows which policy judged the turns that follow.
 */
export interface ModeChanged {
at: At13
kind?: Kind25
mode: Mode
run_id: RunId12
seq: Seq12
}
/**
 * The thread's roots changed mid-thread (D76) — a directory added while the conversation
 * ran — so a reader knows which turns could see which roots.
 */
export interface WorkspaceChanged {
at: At14
kind?: Kind26
roots: Roots
run_id: RunId13
seq: Seq13
}
/**
 * One directory a thread works on, and the name it is addressed by.
 */
export interface Root {
name: Name1
path: Path1
}
export interface Ended {
at: At15
detail?: Detail
kind?: Kind27
reason: Reason2
run_id: RunId14
seq: Seq14
steps_taken: StepsTaken
}
