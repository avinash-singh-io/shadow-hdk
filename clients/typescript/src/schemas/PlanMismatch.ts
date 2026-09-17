// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 3. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type Axis = ("depth" | "fan_out" | "steps" | "component" | "effect")
export type Found = string
export type Required = string
export type Step = string

/**
 * One way a plan does not fit, as data a host or a planner can act on.
 */
export interface PlanMismatch {
axis: Axis
found: Found
required: Required
step: Step
}
