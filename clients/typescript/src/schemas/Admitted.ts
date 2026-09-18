// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 3. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type AuthorityDigest = string
export type Depth = (number | null)
export type FanOut = (number | null)
export type Steps = (number | null)
export type PlanDigest = string

export interface Admitted {
authority_digest?: AuthorityDigest
limits?: PlanLimits
plan_digest: PlanDigest
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
