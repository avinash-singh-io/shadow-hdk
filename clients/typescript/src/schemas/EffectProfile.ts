// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 2. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type Contained = boolean
export type Costs = boolean
export type Reaches = boolean
export type Everything = boolean
export type Names = string[]
export type Reversible = boolean

/**
 * Six fields. Names open, effects closed.
 */
export interface EffectProfile {
contained?: Contained
costs?: Costs
reaches?: Reaches
reads?: ScopeSet
reversible?: Reversible
writes?: ScopeSet1
}
/**
 * A set of scopes that can also honestly say *everything*.
 * 
 * A component that will not declare what it reads or writes is registered as touching everything
 * (09 §2: a missing declaration means assume the worst, never assume nothing), and "everything"
 * over an open set of names cannot be spelled as a list.
 */
export interface ScopeSet {
everything?: Everything
names?: Names
}
/**
 * A set of scopes that can also honestly say *everything*.
 * 
 * A component that will not declare what it reads or writes is registered as touching everything
 * (09 §2: a missing declaration means assume the worst, never assume nothing), and "everything"
 * over an open set of names cannot be spelled as a list.
 */
export interface ScopeSet1 {
everything?: Everything
names?: Names
}
