// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 2. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type JsonValue = unknown
export type Principal = (string | null)
export type RunId = string
export type Step = string

/**
 * Opaque to the runtime. A product's adapter interprets it; the runtime only carries it.
 */
export interface Context {
attributes?: Attributes
principal?: Principal
run_id: RunId
step: Step
}
export interface Attributes {
[k: string]: JsonValue
}
