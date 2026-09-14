// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 2. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type At = string
export type Axis = string
export type Kind = ("measured" | "derived" | "declared" | "unknown")
export type Source = string
export type Evidence = CapabilityEvidence[]
export type Network = ("denied" | "available" | "unknown")
export type Proven = boolean
export type Reads = ("none" | "workspace" | "machine" | "unknown")
export type Secrets = ("denied" | "ambient" | "unknown")
export type Writes = ("none" | "workspace" | "machine" | "unknown")

/**
 * The effective environment boundary for one mode, established by proof or an honest no.
 */
export interface EnvironmentCapabilities {
evidence?: Evidence
network?: Network
proven?: Proven
reads?: Reads
secrets?: Secrets
writes?: Writes
}
/**
 * Why one capability value may be believed, without carrying a secret or probe output.
 */
export interface CapabilityEvidence {
at?: At
axis: Axis
kind?: Kind
source?: Source
}
