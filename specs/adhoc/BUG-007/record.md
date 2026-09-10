---
type: Ad-hoc Record
---

# Ad-hoc Work Record: BUG-007

> **Type**: quick-task
> **Created**: 2026-09-10
> **Branch**: fix/BUG-001-meta-tool-shadowing (this branch carries BUG-001 and BUG-007)
> **Backlog**: BUG-007
> **Status**: shipped

## Current Behavior

`[tool.mypy] mypy_path` omitted `packages/wire/src`, `packages/adapters/contained/src` and
`packages/adapters/derivation/src`. All three ship `py.typed`, so mypy resolved them through the
editable install's `.pth` entries and treated them as clean site-packages. The gate reported
*Success: no issues found in 115 source files* while nine errors sat in the wire. **Every mypy-0
this lane reported from Phase 9 (when the wire was written) to Phase 16 excluded that package.**

## Expected Behavior

Every package under `packages/` is on the path and checked. A gate that silently narrows is worse
than no gate, so the configuration is asserted by a test over the *set* of packages — a package
added later fails on the day it is added rather than being quietly skipped — for ruff's `src` too,
which decides first-party and would otherwise sort an omitted package's imports as third-party.

Eight of the nine errors had one cause: `contracts.load` was typed `as_type: type[T]`, which no
union satisfies, so every `load(text, Event | Observation | Judgement)` in the wire was an
`arg-type` error and three `type: ignore`s were themselves unused. `load` is now overloaded — a
concrete type gives back that type; a union caller annotates what it expects, and `TypeAdapter` is
what makes the annotation true rather than a hope. The ninth was a real `no-any-return`.

**Rejected.** *Silence the three with `ignore_missing_imports`* — that is the bug, written down.
*Leave `load` as `Any`* — it would push `no-any-return` onto twenty call sites that are correct.

## Unchanged Behavior

No runtime behaviour: the suite is 695 → 697 (the two new invariants) with no change to any
existing test. `dump`, `round_trip` and every concrete `load` call site are untouched.

## Verification Evidence

```
Before (the claim under test):
$ MYPYPATH=packages/wire/src:packages/adapters/contained/src:packages/adapters/derivation/src \
    uv run mypy --no-incremental
Found 9 errors in 3 files (checked 116 source files)
  wire/remote.py:62,136 arg-type · wire/context.py:95 no-any-return
  wire/sides.py:233 var-annotated + arg-type · wire/sides.py:75-77,249 unused-ignore

After:
$ uv run mypy; echo $?              → 0   (Success: no issues found in 116 source files)
$ uv run ruff check -q; echo $?     → 0
$ uv run ruff format --check -q     → 0
$ uv run pytest -q; echo $?         → 0   (697 passed, 9 deselected)
```

Three mutations on the invariant, all bite: a package dropped from `mypy_path`; one dropped from
ruff's `src`; the compared path corrupted.
