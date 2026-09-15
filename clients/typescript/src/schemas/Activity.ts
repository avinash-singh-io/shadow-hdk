// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 3. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type At = string
export type Kind = string
export type RunId = string
export type Step = string
export type Text = string

export interface Activity {
at: At
kind: Kind
run_id: RunId
step: Step
text: Text
}
