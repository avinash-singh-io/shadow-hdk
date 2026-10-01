---
type: Retrospective
status: complete
---

# Phase 61 — undo, and an agent's own workspace — Retrospective

> Lane P's asks 3 and 7, and the epic's one new port. v0.40.0.

## What was delivered

- **`WorkspaceHistoryPort`** (D161): `snapshot`/`restore`/`snapshots`, with `GitHistory` shipped and
  attached wherever a local root has a `.git` — a **linked worktree included**, where `.git` is a
  file rather than a directory. A port because *cheap on a work tree and expensive otherwise* is
  exactly what a port is for, and an environment without one refuses rather than crashing.
- **A restore is itself an act** (D163): `delete`-class, irreversible, and the shipped `ask` mode
  stops a person before an undo. "An undo that bypasses governance is a hole" was our own answer to
  lane P, and this is it kept.
- **When to snapshot stays the product's** (D162): its per-turn checkpoint goes through the port
  directly as its own act, which is what makes automatic checkpointing viable at all.
- **A snapshot holds what git would track** (D164): ignored files are neither captured nor removed.
- **Nothing touches the product's git state** (D165): a scratch index into a parentless commit under
  `refs/shadow-hdk/snapshots/*` — never HEAD, a branch, the index or the stash.
- **A worktree per agent** (ask 7): host-side, each on a `shadow-hdk/<name>` branch it can open a
  pull request from; a developer's own worktrees are unreachable from it.

## What went well

- **Lane P narrowed the design question and that was the right call.** We had asked whether the kit
  should ship one mechanism, a port with a git adapter, or only a record of what would be restored;
  their answer made the choice obvious and the phase small.
- **D165 shaped the whole adapter rather than being bolted on.** The plumbing route — scratch index,
  `write-tree`, `commit-tree`, own ref namespace — follows directly from "never touch their git",
  and the test compares HEAD, branch, branch list, stash list, staged names and log before and after.
- **D164 is tested in both directions**, because deleting somebody's `node_modules` and resurrecting
  their rotated `.env` are both real bugs and only one of them is the obvious one.

## What did not

- **Two assertions were weaker than they looked, and the mutation pass said so.**
  `test_a_root_that_is_not_a_repository_refuses_rather_than_crashing` accepted any message
  mentioning git, so deleting the guard still passed — a raw `git add` failure refuses too, just
  uselessly. And the read-only restore test used a made-up snapshot name, so it was refused for the
  wrong reason and passed with the mode guard deleted. Both tightened.
- **G3's tests followed its implementation**, so all nine passed first run; five mutations carry it.
- A migration note's fenced Python was left unformatted and the landing gate caught it, not the
  phase's own.

## Verification Evidence

Captured 2026-10-01 on `staging` with phase 61 merged (the release tree for **v0.40.0**), macOS 26
(Darwin 27.0.0), Python 3.14.6. `pytest`'s exit code read directly rather than through a pipe.

### `uv sync --all-packages --all-extras` (the build command)

```
 + shadow-hdk-linux-sandbox==0.40.0 (from file:///…/native/sandbox)
```

### `uv run ruff check` · `uv run ruff format --check` · `uv run mypy`

```
All checks passed!
551 files already formatted
Success: no issues found in 490 source files
```

The format check first reported `1 file would be reformatted` — `docs/migrations/0.40.md`'s fenced
Python. Rewritten format-stably rather than left to ruff to collapse, and re-checked above.

### `uv run pytest`

```
1986 passed, 20 skipped, 21 deselected, 85 warnings in 180.68s (0:03:00)
pytest exit=0
```

Phase 60 left it at 1957; this phase adds 29.

### Mutation checks — eighteen, all biting

Seven in G1 (snapshotting HEAD instead of the tree, not removing files created since, using the
product's index, removing ignored files, snapshots under `refs/heads`, the missing-repository guard,
the date sort), six in G2 (a reversible restore, a read-class checkpoint, read-only, `Failed` instead
of `Refused`, a history on a non-repository, a lost listing order) and five in G3 (no branch prefix,
an unfiltered listing, dropping the branch by default, an escaping name, `.git` tested as a
directory). Two of those needed their assertion tightened before they would bite, described above.

### What is not covered here

No schema moved — `WorkspaceHistoryPort` is a Protocol, not a published contract — so the wire is
untouched by this phase and the TypeScript client regenerated with no drift.
