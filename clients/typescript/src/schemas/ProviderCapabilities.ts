// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 2. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type At = string
export type Axis = string
export type Kind = ("measured" | "derived" | "declared" | "unknown")
export type Source = string
export type Evidence = CapabilityEvidence[]
export type Interrupt = ("native" | "terminate" | "none" | "unknown")
export type Reasoning = ("yes" | "no" | "unknown")
export type Session = ("resumable" | "process" | "none" | "unknown")
export type Streaming = ("live" | "final" | "none" | "unknown")
export type ToolPath = ("controlled" | "observed" | "uncontrolled" | "unavailable" | "unknown")
export type UsageCost = ("yes" | "no" | "unknown")
export type UsageTokens = ("yes" | "no" | "unknown")

/**
 * What a provider can honestly offer to a host. Every omitted axis is unknown.
 */
export interface ProviderCapabilities {
evidence?: Evidence
interrupt?: Interrupt
reasoning?: Reasoning
session?: Session
streaming?: Streaming
tool_path?: ToolPath
usage_cost?: UsageCost
usage_tokens?: UsageTokens
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
