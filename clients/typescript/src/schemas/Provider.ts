// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 2. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type AuthFailurePatterns = string[]
export type AuthProbe = string[]
export type BackfillEnv = string[]
export type Bin = string
export type BinEnvKey = (string | null)
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
export type AllowArg = string
export type AllowOverride = string
export type AllowToolPrefix = string
export type Field = string
export type Flag = string
export type BehaviourArgs = BehaviourArg[]
export type CostUsdAt = string
export type DeltaKindAt = string
export type DeltaOn = string[]
export type At1 = string
export type Kind1 = string
export type On = string
export type Deltas = Delta[]
export type Disallow = string[]
export type DisallowArg = string
export type DoneAt = string
export type DoneOn = string[]
export type FailedAt = string
export type FailedTextAt = string
export type InputTokensAt = string
export type InterruptLine = string
export type McpConfigArg = string
export type McpConfigShape = string
export type McpStrictArgs = string[]
export type OutputTokensAt = string
export type PromptShape = string
export type Resident = boolean
export type ResumeArgs = string[]
export type SayAt = string
export type SayOn = string[]
export type SessionIdAt = string
export type StopReasonAt = string
export type SubtypeKey = string
export type ThinkAt = string
export type ThinkOn = string[]
export type TypeKey = string
export type FallbackBins = string[]
export type Id = string
export type InjectsTools = (string | null)
export type InstallHint = string
export type Kind2 = ("model" | "agent")
export type LaunchArgs = string[]
export type MinimumVersion = (string | null)
export type Name = string
export type Name1 = string
export type Value = string
export type SetEnv = EnvVar[]
export type StripEnv = string[]
export type Transport = (string | null)
export type VersionProbe = string[]

/**
 * One provider, as read from its file.
 *
 * Every field that encodes a quirk is here rather than in a code path, and the file that carries
 * it also carries the measurement that found it.
 */
export interface Provider {
auth_failure_patterns?: AuthFailurePatterns
auth_probe?: AuthProbe
backfill_env?: BackfillEnv
bin: Bin
bin_env_key?: BinEnvKey
capabilities?: ProviderCapabilities
dialect?: (Dialect | null)
fallback_bins?: FallbackBins
id: Id
injects_tools?: InjectsTools
install_hint?: InstallHint
kind: Kind2
launch_args?: LaunchArgs
minimum_version?: MinimumVersion
name?: Name
set_env?: SetEnv
strip_env?: StripEnv
transport?: Transport
version_probe?: VersionProbe
}
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
/**
 * How to read one CLI's line-delimited JSON event stream (D40).
 *
 * Claude Code and Codex both answer on stdout as newline-delimited JSON. They disagree about every
 * *name* — which key holds the event type, which type carries assistant text, where the text sits,
 * what ends a turn — and about nothing else. The shape is shared; only the names differ. So the
 * names are data.
 *
 * **This is not a query language and must not become one.** Ten fields, each a literal event name
 * or a dotted path where `[]` means *each element of this list*. No expressions, no conditionals,
 * no arithmetic. A CLI whose stream does not fit gets code — the same cut the reference makes with
 * its `streamFormat` enum, except these are fields where those are hand-written parsers.
 *
 * Every default is the conservative one. A dialect that named no event reads nothing rather than
 * matching something by accident: a stream nobody described is a stream nobody can read, and
 * saying so is better than inventing a reading of it.
 */
export interface Dialect {
allow_arg?: AllowArg
allow_override?: AllowOverride
allow_tool_prefix?: AllowToolPrefix
behaviour_args?: BehaviourArgs
cost_usd_at?: CostUsdAt
delta_kind_at?: DeltaKindAt
delta_on?: DeltaOn
deltas?: Deltas
disallow?: Disallow
disallow_arg?: DisallowArg
done_at?: DoneAt
done_on?: DoneOn
failed_at?: FailedAt
failed_text_at?: FailedTextAt
input_tokens_at?: InputTokensAt
interrupt_line?: InterruptLine
mcp_config_arg?: McpConfigArg
mcp_config_shape?: McpConfigShape
mcp_strict_args?: McpStrictArgs
output_tokens_at?: OutputTokensAt
prompt_shape?: PromptShape
resident?: Resident
resume_args?: ResumeArgs
say_at?: SayAt
say_on?: SayOn
session_id_at?: SessionIdAt
stop_reason_at?: StopReasonAt
subtype_key?: SubtypeKey
think_at?: ThinkAt
think_on?: ThinkOn
type_key?: TypeKey
}
/**
 * One behaviour field, and the flag the CLI takes it as (D64).
 */
export interface BehaviourArg {
field: Field
flag: Flag
}
/**
 * One kind of streamed piece a CLI emits (D63): which value of the delta-kind field it is,
 * what activity kind it becomes, and where its text sits in the event.
 */
export interface Delta {
at: At1
kind: Kind1
on: On
}
/**
 * One name and one value, for the environment a provider is launched with.
 */
export interface EnvVar {
name: Name1
value: Value
}
