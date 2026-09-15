// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 3. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type MaxCostCents = (number | null)
export type MaxSteps = number
export type MaxWallSeconds = number
export type MinSteps = number

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
