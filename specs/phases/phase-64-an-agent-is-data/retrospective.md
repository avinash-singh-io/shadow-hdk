---
type: Retrospective
status: complete
---

# Phase 64 — an agent is data, like everything else — Retrospective

> The last asymmetry in the plugin boundary, and the two debts the phase agreed to carry. v0.43.0.

## What was delivered

- **`store_patterns`** over an `agents` collection (D174): version-gated, a malformed row skipped
  rather than fatal, `skipped` saying why, a product's agent shadowing a shipped one by name.
- **`ModeSpec.agent`** (D175): a mode names which agent runs it, so switching goes through the
  governed `set_mode`; `thread/start {agent}` overrides it for one thread.
- **An unknown name is refused, naming what exists** (D176) — before an environment is opened or a
  model asked.
- **`agents/list`** and the **resolved agent on the thread** (D177).
- **TD-017 decided**: `docs` joins `specs` in ruff's exclude, on the precedent already in the config.
- **ENH-026 closed**: the product doc current for 0.43.0, with the store-CRUD chapter it never had.

## What went well

- **`pattern_from` already took a dict**, so the phase was a missing source rather than a new
  mechanism — the cheapest possible shape for closing a gap this consequential.
- **Putting the selector on the mode** reused a governed door instead of inventing one.
- **The repo's own invariant stated the argument first.** `test_every_registry_has_a_store_source`
  went red the moment `PatternRegistry` existed; the gap had escaped it only because there was no
  registry to catch.

## What did not

- **Three mutation passes were wrong before one was right**, and the second was the dangerous kind:
  a shell helper that never passed its arguments, so nothing was mutated and all seven cases
  reported success. A pass that silently applies nothing is worse than no pass, because it reports
  green. The helper is now a script that exits non-zero on a missing anchor.
- **TD-019**: a failing test that stands up a `ServeHost` hangs instead of failing — five
  reproductions. The logic under test was extracted into pure functions to get around it.
- **The wire first passed `agent=` unconditionally**, breaking 22 host doubles — exactly what D14
  forbids. Passed only when given now.
- A **documentation failure of ours** surfaced: full plugin CRUD had worked for a long time and was
  written down nowhere, so a product asked us for a capability it already had.

## Verification Evidence

Captured 2026-10-02 on `staging` with phase 64 merged (the release tree for **v0.43.0**), macOS 26
(Darwin 27.0.0), Python 3.14.6. `pytest`'s exit code read directly rather than through a pipe, and
this retrospective was written **before** the gate below was run against the tree that carries it —
the v0.41.0 failure was caused by doing it the other way round.

### `uv sync --all-packages --all-extras` (the build command)

```
 + shadow-hdk-linux-sandbox==0.43.0 (from file:///…/native/sandbox)
```

### `uv run ruff check` · `uv run ruff format --check` · `uv run mypy`

```
All checks passed!
530 files already formatted
Success: no issues found in 499 source files
```

530, down from 562: `docs` is excluded now (TD-017).

### `uv run pytest`

```
2058 passed, 20 skipped, 23 deselected, 85 warnings in 196.73s (0:03:16)
pytest exit=0
```

Phase 63 left the suite at 2021; this phase adds 37.

### Mutation checks — eighteen, all biting

Six in G1 (no version gate, a stale cache, a fatal malformed row, an unreported skip, an unstable
order, the wrong collection), eight in G2 (the mode's agent ignored, the override losing, a silent
`single`, a refusal that names nothing, an arbitrary agent for an unnamed mode, a handed agent
overridden, the document's key unread, shipped shadowing the product) and four in G3 (an empty
listing, a dropped description, an unrecorded agent, an unsorted listing).

**Three needed their test fixed before they would bite** — the ordering test asserted stability
where reversal is also stable; the shadowing test could not tell shadowing from the shipped library
being absent; and the mode document's `agent` key had no test at all.

### What is not covered here

The `ServeHost` paths are covered behaviourally and **not** mutation-checked, because a failing test
that builds one hangs (TD-019). What is mutation-checked is the logic extracted out of them —
`agent_recorded`, `PatternRegistry`, `mode_from_document`. That is a real limit on this phase's
evidence and it is named rather than papered over.
