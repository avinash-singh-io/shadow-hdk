---
type: Ad-hoc Record
---

# Ad-hoc Work Record: 2026-09-13-sync-specs-to-0.25

> **Type**: quick-task
> **Created**: 2026-09-13
> **Branch**: docs/sync-specs-to-0.25
> **Backlog**: none (BUG-034 filed and closed here)
> **Status**: shipped

## Current Behavior

The architecture specs described the tree as it stood before Phase 28 and the two patches after
it: three modes, one root per thread, `AgentPort.open(tools, workspace)`, fourteen event kinds,
the `workspace` and `sandbox_subprocess` adapters of Phase 3 still on the map, no `wire`/
`serve`/`providers` packages in the file structure, `Fourteen event kinds` and `Seventeen
distributions at 0.16.0` in the README. Reading them for this sync found a real defect:
`[environment] mode` in `harness.toml`, `--mode`, `Settings.mode` and `Harness(mode=)` were
typed and checked as an *environment* name (the three), although since D76 the thread's mode is
a *mode id* (`ask` included, or a file's or a row's) and the sandbox mode follows from it — so
`mode = "ask"` in the file was refused (BUG-034). And underneath, `requires(isolation, mode)`
accepted any name that was not `full` when the isolation was confined, so an unknown mode reached
the sandbox as a confined one.

## Expected Behavior

Every architecture document describes the tree at 0.25.2: the workspace as roots, the four
modes and the environment mode each names, the thread and its methods on the wire (`tools/list`,
`skills/list`, `thread/add_root`, `roots`, `environment`), `start_held` and `LineBuffer` as the
one place each, `KeepingSink`, `serve[providers]`, the ports table with `ThreadStore` and `Store`,
fifteen event kinds, eighteen distributions, the file structure regenerated from the tree. The
mode in settings and on the CLI is a mode id, refused at `open` by name with the known ones
(read from the registry then — D66); an unknown environment mode name is refused by `requires`.

## Unchanged Behavior

No wire method, schema or port changes; every shipped mode behaves as it did; a `harness.toml`
that named one of the three environment names still works and means the same. The documents
invariant still holds every path named to one that exists.

## Verification Evidence

Captured fresh 2026-09-13 on the branch:

- `uv run ruff check -q` → 0 · `uv run ruff format --check -q` → 0 · `uv run mypy` → 0 (249 files)
- `uv run pytest -q -p no:cacheprovider -m 'not live'` → `1407 passed, 2 skipped, 12 deselected`
- RED first: `harness.toml: mode 'ask' is not read-only, workspace-write or full`; `default mode 'nope'` refused by governance only after the sandbox had accepted it; `requires(CONFINED, "nope")` did not raise
- `tests/invariants/test_the_documents_describe_this_tree.py` → 7 passed after the file-structure rewrite (the adapter block read exactly; one adapter per line)
