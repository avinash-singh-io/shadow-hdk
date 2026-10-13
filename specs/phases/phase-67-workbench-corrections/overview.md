---
type: Phase
status: in-progress
tags: [maintenance, socket, worktrees, search, snapshots]
---
# Phase 67 — Workbench corrections

Owner approved implementation and publication as 0.48.0 on 2026-10-13.
Latest published version stays 0.47.3 until publication is verified.

## Scope
N-W0: SocketOffer forwards the existing Narrowing interface; listing and calls narrow at open and mode switch.
N-W2: optional host-supplied branch with explicit creation ownership; old branch default and discovery preserved.
N-W3: ignore-aware search without a repository-size ceiling, including nested ignores and linked worktrees.
N-W4: reusable private snapshot index and targeted restore; no person-owned Git state changed.

## Decisions
- A tracked file stays searchable and snapshottable even if an ignore rule matches it, consistent with Git tracking.
- Non-Git roots honour nested .gitignore files; Git roots use Git's standard exclusion rules.
- Result caps stay bounded and announced; traversal has no silent file-count cap.
- Branch names are host data. Ownership is recorded by exact checkout identity, never inferred from an arbitrary custom prefix.
- Snapshot caching is private per worktree and serialized across histories; unchanged content is not deliberately rehashed on every turn. Metadata scanning remains necessary for external edits.
- Existing optional environment tools are maintained under D190; no new tool, kernel port or product policy added.

## Acceptance
Real socket listing, calls and mode switches enforce narrowing. Custom branch creation/list/removal preserve unrelated worktrees.
Nested exclusions and negations work; ignored folders are pruned; >100,000 files are searchable.
Snapshots capture external edits, additions, deletions and modes; restore preserves ignored data and HEAD/index/stash.
Benchmarks report cold/warm search, snapshot and restore with <3s/<2s/<5s budgets on the pinned large fixture; real repository evidence is recorded separately.
Full ruff/format/mypy/pytest, mutation controls, built-wheel regressions, CI, seven published artifacts and fresh installs pass before closure.

## Out
Product pins/UI/bridges, native implementation, background jobs, terminals and test parsing.
