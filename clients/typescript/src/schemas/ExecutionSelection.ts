// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 2. Regenerate with `npm run generate`; the invariant
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
export type Evidence = CapabilityEvidence[]
export type Network = ("denied" | "available" | "unknown")
export type Proven = boolean
export type Reads = ("none" | "workspace" | "machine" | "unknown")
export type Secrets = ("denied" | "ambient" | "unknown")
export type Writes = ("none" | "workspace" | "machine" | "unknown")
export type Evidence1 = CapabilityEvidence[]
export type Interrupt = ("native" | "terminate" | "none" | "unknown")
export type Reasoning = ("yes" | "no" | "unknown")
export type Session = ("resumable" | "process" | "none" | "unknown")
export type Streaming = ("live" | "final" | "none" | "unknown")
export type ToolPath = ("controlled" | "observed" | "uncontrolled" | "unavailable" | "unknown")
export type UsageCost = ("yes" | "no" | "unknown")
export type UsageTokens = ("yes" | "no" | "unknown")

/**
 * The provider/environment facts accepted at one construction boundary.
 */
export interface ExecutionSelection {
compatibility: Compatibility
environment: EnvironmentCapabilities
provider: ProviderCapabilities
}
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
 * What a provider can honestly offer to a host. Every omitted axis is unknown.
 */
export interface ProviderCapabilities {
evidence?: Evidence1
interrupt?: Interrupt
reasoning?: Reasoning
session?: Session
streaming?: Streaming
tool_path?: ToolPath
usage_cost?: UsageCost
usage_tokens?: UsageTokens
}
