// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 1. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type Contained = boolean
export type Costs = boolean
export type Reaches = boolean
export type Everything = boolean
export type Names = string[]
export type Reversible = boolean
export type Description = string
export type JsonValue = unknown
export type Name = string
export type Labels = string[]
export type Adapter = string
export type At = string
export type Licence = (string | null)
export type Posture = ("controlled" | "observed")
export type RegisteredBy = string
export type Signature = (string | null)
export type SignedBy = (string | null)
export type Id = string

/**
 * ``register(Component) -> RegistrationId``, as a value. The registry is a set of these.
 */
export interface Registration {
component: Component
id: Id
}
export interface Component {
effects: EffectProfile
interface: Interface
labels?: Labels
provenance: Provenance
}
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
/**
 * What the agent can invoke: a name, a description, typed input, typed output.
 */
export interface Interface {
description: Description
input_schema?: InputSchema
name: Name
output_schema?: OutputSchema
}
export interface InputSchema {
[k: string]: JsonValue
}
export interface OutputSchema {
[k: string]: JsonValue
}
/**
 * Who registered it, what adapter it came through, who signed it, when — and whether we could
 * have stopped it.
 * 
 * ``at`` is whatever the registering side's clock said, as text — the kernel has no clock.
 * ``licence`` is recorded here because an open-source component is whatever it is, behind an
 * adapter, with its licence in provenance (09 §4).
 * 
 * ``posture`` defaults to ``controlled`` because everything the runtime invokes, it gated. The
 * exception has to be explicit: an adapter that forgets to say produces a claim that is true of
 * everything the runtime does.
 */
export interface Provenance {
adapter: Adapter
at: At
licence?: Licence
posture?: Posture
registered_by: RegisteredBy
signature?: Signature
signed_by?: SignedBy
}
