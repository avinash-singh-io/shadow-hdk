// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 3. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type Observation = (Completed | Refused | ApprovalRequest | InputRequest | Failed | Pending | Acted)
export type Kind = "completed"
export type Kind1 = "refused"
export type Reason = string
export type Component = (string | null)
export type Handle = string
export type Kind2 = "approval_request"
export type Question = string
export type Handle1 = string
export type Kind3 = "input_request"
export type Question1 = string
export type Error = string
export type Kind4 = "failed"
export type Handle2 = string
export type Kind5 = "pending"
export type Exit = string
export type ForeignId = string
export type IdempotencyKey = string
export type Kind6 = "acted"

export interface Completed {
kind?: Kind
output?: {
[k: string]: unknown
}
}
export interface Refused {
kind?: Kind1
reason: Reason
}
/**
 * The step paused; whoever implements governance decides what asking means.
 *
 * `component` and `inputs` say what the question is about (BUG-026) — an agent surfacing a
 * child's question passes on what that child was about to do, so the person sees it.
 */
export interface ApprovalRequest {
component?: Component
handle: Handle
inputs?: unknown
kind?: Kind2
question: Question
}
/**
 * The step paused for the person's answer to a question of the agent's own (D61).
 */
export interface InputRequest {
handle: Handle1
kind?: Kind3
question: Question1
}
export interface Failed {
error: Error
kind?: Kind4
}
/**
 * The answer arrives later, under this handle.
 */
export interface Pending {
handle: Handle2
kind?: Kind5
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
kind?: Kind6
}
