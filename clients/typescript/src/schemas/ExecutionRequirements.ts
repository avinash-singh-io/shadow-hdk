// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 2. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type Network = ("denied" | null)
export type Proven = boolean
export type ReadsWithin = (("none" | "workspace" | "machine") | null)
export type Secrets = ("denied" | null)
export type WritesWithin = (("none" | "workspace" | "machine") | null)
export type Interrupt = (("native" | "terminate") | null)
export type Reasoning = boolean
export type Session = (("resumable" | "process") | null)
export type Streaming = (("live" | "final") | null)
export type ToolPath = (("controlled" | "observed") | null)
export type UsageCost = boolean
export type UsageTokens = boolean

export interface ExecutionRequirements {
environment?: EnvironmentRequirements
provider?: ProviderRequirements
}
/**
 * Maximum reach a host accepts from the effective environment.
 */
export interface EnvironmentRequirements {
network?: Network
proven?: Proven
reads_within?: ReadsWithin
secrets?: Secrets
writes_within?: WritesWithin
}
/**
 * Minimum provider properties a host requires. `None`/`False` means no requirement.
 */
export interface ProviderRequirements {
interrupt?: Interrupt
reasoning?: Reasoning
session?: Session
streaming?: Streaming
tool_path?: ToolPath
usage_cost?: UsageCost
usage_tokens?: UsageTokens
}
