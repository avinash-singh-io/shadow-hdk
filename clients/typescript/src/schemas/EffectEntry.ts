// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 2. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type At = string
export type AttemptId = string
export type AuthorizationId = (string | null)
export type Kind = ("staged" | "authorized" | "executing" | "receipt" | "refused" | "failed" | "unknown" | "reconciled")
export type Sequence = number
export type StageDigest = string

/**
 * One immutable fact in an effect attempt's append-only history.
 */
export interface EffectEntry {
at: At
attempt_id: AttemptId
authorization_id?: AuthorizationId
detail?: {
[k: string]: unknown
}
kind: Kind
sequence: Sequence
stage_digest: StageDigest
}
