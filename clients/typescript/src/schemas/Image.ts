// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 3. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type Data = string
export type MimeType = string

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
