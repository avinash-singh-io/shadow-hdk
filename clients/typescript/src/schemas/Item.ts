// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 3. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type At = (string | null)
export type Children = Item[]
export type Component = (string | null)
export type At1 = string
export type AttemptId = string
export type AuthorizationId = (string | null)
export type Kind = "effect_recorded"
export type RecordedAt = string
export type Replayed = boolean
export type RunId = string
export type Seq = number
export type StageDigest = string
export type Status = ("staged" | "authorized" | "executing" | "receipt" | "refused" | "failed" | "unknown" | "reconciled")
export type Step = string
export type Observation = ((Completed | Refused | ApprovalRequest | InputRequest | Failed | Pending | Acted) | null)
export type Kind1 = "completed"
export type Kind2 = "refused"
export type Reason = string
export type Component1 = (string | null)
export type Handle = string
export type Kind3 = "approval_request"
export type Question = string
export type Handle1 = string
export type Kind4 = "input_request"
export type Question1 = string
export type Error = string
export type Kind5 = "failed"
export type Handle2 = string
export type Kind6 = "pending"
export type Exit = string
export type ForeignId = string
export type IdempotencyKey = string
export type Kind7 = "acted"
export type Outcome = ("running" | "completed" | "refused" | "approval_requested" | "input_requested" | "failed" | "pending" | "acted")
export type Parent = ([unknown, unknown] | null)
export type Plan = (PlanAdmitted | PlanRefused | null)
export type Amendment = boolean
export type Asks = string[]
export type At2 = string
export type AuthorityDigest = string
export type Kind8 = "plan_admitted"
export type Depth = (number | null)
export type FanOut = (number | null)
export type Steps = (number | null)
export type PlanDigest = string
export type Refusals = string[]
export type RunId1 = string
export type Seq1 = number
export type Step1 = string
export type Amendment1 = boolean
export type At3 = string
export type Kind9 = "plan_refused"
export type Axis = ("depth" | "fan_out" | "steps" | "component")
export type Found = string
export type Required = string
export type Step2 = string
export type Mismatches = PlanMismatch[]
export type PlanDigest1 = string
export type RunId2 = string
export type Seq2 = number
export type Step3 = string
export type Reason1 = (string | null)
export type Reasoning = string
export type RunId3 = string
export type Step4 = string
export type CostCents = (number | null)
export type InputTokens = (number | null)
export type OutputTokens = (number | null)

/**
 * One thing the agent did, with what it thought first and what it cost.
 *
 * `children` are the steps of every run spawned while this step was executing, in order, each
 * with children of its own. `observation` is the whole observation — a projection is not the
 * place to summarise; the offloading rule (Group 4) is where size is handled, before it gets here.
 */
export interface Item {
at?: At
children?: Children
component?: Component
effect?: (EffectRecorded | null)
inputs?: {
[k: string]: unknown
}
observation?: Observation
outcome?: Outcome
parent?: Parent
plan?: Plan
reason?: Reason1
reasoning?: Reasoning
run_id: RunId3
step: Step4
usage?: (Usage | null)
}
/**
 * One public fact from the append-only transaction history (D101-D104).
 *
 * This is deliberately a generic status event rather than one event class per transition. A
 * client can render the exact history—including an explicit ``unknown``—without reimplementing
 * transaction inference or receiving credentials, callbacks or hidden authorizer state.
 */
export interface EffectRecorded {
at: At1
attempt_id: AttemptId
authorization_id?: AuthorizationId
detail?: {
[k: string]: unknown
}
kind?: Kind
recorded_at?: RecordedAt
replayed?: Replayed
run_id: RunId
seq: Seq
stage_digest: StageDigest
status: Status
step: Step
}
export interface Completed {
kind?: Kind1
output?: {
[k: string]: unknown
}
}
export interface Refused {
kind?: Kind2
reason: Reason
}
/**
 * The step paused; whoever implements governance decides what asking means.
 *
 * `component` and `inputs` say what the question is about (BUG-026) — an agent surfacing a
 * child's question passes on what that child was about to do, so the person sees it.
 */
export interface ApprovalRequest {
component?: Component1
handle: Handle
inputs?: unknown
kind?: Kind3
question: Question
}
/**
 * The step paused for the person's answer to a question of the agent's own (D61).
 */
export interface InputRequest {
handle: Handle1
kind?: Kind4
question: Question1
}
export interface Failed {
error: Error
kind?: Kind5
}
/**
 * The answer arrives later, under this handle.
 */
export interface Pending {
handle: Handle2
kind?: Kind6
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
kind?: Kind7
}
/**
 * A whole plan admitted before it compiled (D108): its digest, the authority it was admitted
 * under, the limits it fit — and whether it amended a plan already running (D116).
 */
export interface PlanAdmitted {
amendment?: Amendment
asks?: Asks
at: At2
authority_digest?: AuthorityDigest
kind?: Kind8
limits?: PlanLimits
plan_digest: PlanDigest
refusals?: Refusals
run_id: RunId1
seq: Seq1
step?: Step1
}
/**
 * How much plan a host, a mode or a parent admits. `None` is unbounded.
 *
 * Order-bearing, like an effect profile: `meet` takes the narrower of each field, so limits
 * compose without a review and the narrowing proof covers them.
 */
export interface PlanLimits {
depth?: Depth
fan_out?: FanOut
steps?: Steps
}
/**
 * A whole plan refused before anything ran — every mismatch, in the stable order. The
 * planner hears this as an observation and decides; nothing was trimmed (D111).
 */
export interface PlanRefused {
amendment?: Amendment1
at: At3
kind?: Kind9
mismatches?: Mismatches
plan_digest: PlanDigest1
run_id: RunId2
seq: Seq2
step?: Step3
}
/**
 * One way a plan does not fit, as data a host or a planner can act on.
 */
export interface PlanMismatch {
axis: Axis
found: Found
required: Required
step: Step2
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
