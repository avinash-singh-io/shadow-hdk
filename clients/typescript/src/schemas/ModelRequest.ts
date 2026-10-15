// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 3. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type Content = string
export type Data = string
export type MimeType = string
export type Images = Image[]
export type Role = ("system" | "user" | "assistant" | "tool")
export type ToolCallId = (string | null)
export type JsonValue = unknown
export type Id = string
export type Name = string
export type ToolCalls = ToolCall[]
export type Messages = Message[]
export type Model = (string | null)
export type Description = string
export type Name1 = string
export type Tools = Interface[]

export interface ModelRequest {
messages: Messages
model?: Model
tools?: Tools
}
/**
 * One turn in a transcript.
 *
 * `tool_calls` is what an **assistant** message asked for, and it is not optional decoration: a
 * tool result carries a `tool_call_id`, and every provider rejects a result whose call is in no
 * preceding message. Without it the model is also never shown which tool it called with what
 * arguments, so its next turn reasons about a step it cannot see.
 */
export interface Message {
content: Content
images?: Images
role: Role
tool_call_id?: ToolCallId
tool_calls?: ToolCalls
}
/**
 * An inline tool image: base64 bytes and their media type, never a local pathname.
 *
 * A coding tool, support desk and research assistant each consume visual observations.
 * The bytes cross checkpoints and model/MCP boundaries without becoming textual tokens.
 */
export interface Image {
data: Data
mime_type: MimeType
}
export interface ToolCall {
arguments: JsonValue
id: Id
name: Name
}
/**
 * What the agent can invoke: a name, a description, typed input, typed output.
 */
export interface Interface {
description: Description
input_schema?: InputSchema
name: Name1
output_schema?: OutputSchema
}
export interface InputSchema {
[k: string]: JsonValue
}
export interface OutputSchema {
[k: string]: JsonValue
}
