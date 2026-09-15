// GENERATED from schemas/*.json by clients/typescript/generate.mjs — do not edit.
// protocol_version 2. Regenerate with `npm run generate`; the invariant
// tests/invariants/test_the_typescript_client_is_current.py diffs these files.
/* eslint-disable */
export type ModeRevision = string
export type PolicyRevision = string
export type Principal = (string | null)
export type ProviderRevision = string
export type RegistryRevision = string
export type WorkspaceRevision = string

/**
 * The host-controlled revisions that are relevant at one act.
 */
export interface AuthoritySnapshot {
mode_revision: ModeRevision
policy_revision: PolicyRevision
principal: Principal
provider_revision: ProviderRevision
registry_revision: RegistryRevision
workspace_revision: WorkspaceRevision
}
