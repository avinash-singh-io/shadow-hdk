# Sequential: Group 0 → Group 1 → Group 2 → Group 3 → Group 4 → Groups 5–8 → Group 9

## Group 0 — scope and release contract
**Sequential.** Dependencies: Git, uv, momentum. Commit: docs: start Phase 67 — workbench corrections.
Record approved scope and semantic defaults. Reserve phase/version; start branch.
## Group 1 — socket narrowing
**Sequential.** Dependencies: authenticated socket. Commit: fix(recording): forward socket offer narrowing.
Write failing socket/thread controls, forward existing interface, prove listing/call/mode switch and mutations.
## Group 2 — host-named branches
**Sequential.** Dependencies: Git. Commit: feat(environment): let hosts name owned worktree branches.
Write failing custom branch/ownership/collision controls; preserve defaults and record exact ownership.
## Group 3 — ignore-aware search
**Sequential.** Dependencies: Git and pathspec. Commit: fix(environment): search ignored-aware repositories without silent ceilings.
Git-backed enumeration plus portable nested-ignore traversal; preserve matcher/response contracts and confinement.
## Group 4 — efficient history
**Sequential.** Dependencies: Git. Commit: fix(environment): reuse private snapshot indices and target restore changes.
Benchmark baseline; private persistent index, safe locking/recovery and targeted checkout/removal. External edits and ignored paths stay correct.
## Group 5 — optional pack contracts and image/lifecycle plumbing
**Sequential.** Dependencies: existing component, observation and model ports. Record ADR and primary-source engine comparison. Preserve defaults and JSON roundtrips; screenshots must reach model and MCP as images.
## Group 6 — browser pack
**Sequential.** Dependencies: optional Playwright engine. Per-action governed registrations, isolated headless contexts, enforced origin policy including redirects and subresources, lazy binary installation, navigation/accessibility/interactions/tabs/debugging and run cleanup. Real local application controls and mutation proofs.
## Group 7 — host workbench primitives
**Sequential.** Dependencies: existing environment command driver and standard report parser. Background jobs with independent readers, direct host command/file door, service-address reporting and structured test reports; no mandatory product integration.
## Group 8 — Codex audited reads
**Sequential.** Dependencies: installed Codex and official configuration contract. Disable native reading paths, preserve offered tools, verify actual CLI catalog/behaviour plus audit; refuse unsupported configuration rather than silently allowing bypass.
## Group 9 — acceptance and publication
**Sequential.** Dependencies: GitHub Actions/PyPI. Commit: docs: verify and release workbench corrections.
Mutation-check assertions and restored controls, benchmark, full gate, package/install checks, migration notes, staging → main, tag/release, seven artifacts/fresh install, cleanup.

Reference specs: project-rules.md D190; planning/what-moves-to-shadow.md D184; prior D164/D165 workspace guarantees; config.md release lifecycle.
