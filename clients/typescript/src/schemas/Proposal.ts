// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 3. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type Grounds = string[]
export type Kind = string
export type JsonValue = unknown
export type Adapter = string
export type At = string
export type Licence = (string | null)
export type Posture = ("controlled" | "observed")
export type RegisteredBy = string
export type Signature = (string | null)
export type SignedBy = (string | null)

/**
 * What the runtime hands to the sink. It proposes; it never commits anything anywhere.
 */
export interface Proposal {
grounds?: Grounds
kind: Kind
payload: JsonValue
provenance: Provenance
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
