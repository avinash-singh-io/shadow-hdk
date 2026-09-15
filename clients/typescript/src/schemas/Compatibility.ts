// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 3. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type Available = string
export type Axis = string
export type At = string
export type Axis1 = string
export type Kind = ("measured" | "derived" | "declared" | "unknown")
export type Source = string
export type Required = string
export type Subject = ("provider" | "environment")
export type Mismatches = CapabilityMismatch[]

export interface Compatibility {
mismatches?: Mismatches
}
export interface CapabilityMismatch {
available: Available
axis: Axis
evidence: CapabilityEvidence
required: Required
subject: Subject
}
/**
 * Why one capability value may be believed, without carrying a secret or probe output.
 */
export interface CapabilityEvidence {
at?: At
axis: Axis1
kind?: Kind
source?: Source
}
