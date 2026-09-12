// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 1. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type Judgement = (Allow | Ask | Refuse)
export type Kind = "allow"
export type Kind1 = "ask"
export type Question = string
export type Kind2 = "refuse"
export type Reason = string

export interface Allow {
kind?: Kind
}
export interface Ask {
kind?: Kind1
question: Question
}
export interface Refuse {
kind?: Kind2
reason: Reason
}
