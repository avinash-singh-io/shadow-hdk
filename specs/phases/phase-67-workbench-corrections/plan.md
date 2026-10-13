# Sequential: Group 0 → Group 1 → Group 2 → Group 3 → Group 4 → Group 5

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
## Group 5 — acceptance and publication
**Sequential.** Dependencies: GitHub Actions/PyPI. Commit: docs: verify and release workbench corrections.
Mutation-check assertions and restored controls, benchmark, full gate, package/install checks, migration notes, staging → main, tag/release, seven artifacts/fresh install, cleanup.

Reference specs: project-rules.md D190; planning/what-moves-to-shadow.md D184; prior D164/D165 workspace guarantees; config.md release lifecycle.
