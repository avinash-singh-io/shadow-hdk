// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 2. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type AuthorityDigest = string
export type AuthorizationId = string
export type ExpiresAt = string
export type IdempotencyKey = string
export type Principal = (string | null)
export type RunId = string
export type StageDigest = string
export type Step = string

/**
 * A host grant for one stage under one authority snapshot; data, never executable power.
 */
export interface EffectAuthorization {
authority_digest: AuthorityDigest
authorization_id: AuthorizationId
expires_at: ExpiresAt
idempotency_key: IdempotencyKey
principal: Principal
run_id: RunId
stage_digest: StageDigest
step: Step
}
