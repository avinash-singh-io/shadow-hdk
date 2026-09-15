// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 3. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type Reasoning = string
export type Text = string
export type JsonValue = unknown
export type Id = string
export type Name = string
export type ToolCalls = ToolCall[]
export type CostCents = (number | null)
export type InputTokens = (number | null)
export type OutputTokens = (number | null)

export interface ModelResponse {
reasoning?: Reasoning
text?: Text
tool_calls?: ToolCalls
usage?: (Usage | null)
}
export interface ToolCall {
arguments: JsonValue
id: Id
name: Name
}
/**
 * What the call cost. A model adapter that cannot say reports ``None`` for the field it does
 * not know — *unknown*, never zero (10 §5 R2).
 */
export interface Usage {
cost_cents?: CostCents
input_tokens?: InputTokens
output_tokens?: OutputTokens
}
