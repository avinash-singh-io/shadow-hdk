---
type: Ad-hoc Record
---
# BUG-062 · BUG-063 — a fork is a fresh session with the transcript; cache tokens reach `Spent`

> **Type**: quick-task
> **Created**: 2026-09-20
> **Branch**: fix/BUG-062-063-fork-session-and-cache-tokens
> **Backlog**: BUG-062, BUG-063
> **Status**: at the gate

Two defects lane P measured on `v0.34.0` with kit-only reproductions (their BUG-224/225), each a
place where the kit's own decision (D139, D141) said one thing and the code did another. Both are
fixed in the kit, generically; nothing here takes the product's shape.

## Current Behavior

- `Thread.fork()` copied the record whole, `session_id` included — so the documented move after
  `session_gone` (D139: "a fresh provider session with the transcript") resumed the provider on the
  very session it no longer had and raised `SessionGone` again; `seeded_turns` stayed 0 on a fork,
  and on a `rollback` it said N while nobody seeded anything (the record has said "the first turn
  is seeded with the kept turns" since Phase 25).
- `runtime/step.py::_usage_of` read a step's `usage` back without `cache_read_tokens` /
  `cache_write_tokens`, and `LeaseMeter.settle` — the path a turn's calls take to a thread's meter —
  took no cache counters; so `Spent.cache_read_tokens` was 0 for every thread turn although every
  piece of D141 (the dialects, LangChain, `count_tokens`) was tested green.

## Expected Behavior

- `fork()` and `rollback()` produce a record with `session_id = ""` and `seeded_turns = len(turns)`;
  the first turn on such a record (a fresh provider session, no turn taken since) is told the kept
  turns ahead of its prompt — once, by the kit, from the record. After that turn the record carries
  the fresh session's own id and is never re-seeded.
- `Turn.usage` → the step's output → `_usage_of` → the meter, whole: `Spent.cache_read_tokens` and
  `cache_write_tokens` sum a thread's turns (and a child run's reach its parent through `settle`).

## Unchanged Behavior

The record's shape (`forked_from`, `seeded_turns`, `session_id` existed already); a fork's turns and
pending questions copied as before; `Turn`, `Usage`, `Spent` unchanged; the wire's `thread/fork` and
`thread/rollback` unchanged in signature — their results now show `session_id = ""` and
`seeded_turns`; `count_tokens` unchanged; protocol 3.

## Verification Evidence

Captured 2026-09-20 on the hotfix branch at the 0.34.1 bump (macOS 26; 3.14.6 and 3.12.13).

```
== uv run ruff check                       All checks passed!
== uv run ruff format --check              528 files already formatted
== uv run mypy                             Success: no issues found in 472 source files
== uv run pytest (3.14, non-live, benchmark included)
1851 passed, 20 skipped, 13 deselected, 85 warnings in 165.61s (0:02:45)
== pytest 3.12
1851 passed, 20 skipped, 13 deselected, 85 warnings in 167.29s (0:02:47)
== momentum okf check .                    ✓ specs/ is an OKF v0.1 conformant bundle (216 markdown file(s))
```

RED before the fix: `tests/runtime/test_a_fork_is_a_fresh_session_with_the_transcript.py` — the
fork carried `session_id == "s-1"` and the resume reopened it; `tests/runtime/test_the_meter_counts_cache_tokens.py`
— `_usage_of` returned `cache_read_tokens=None` and `Spent.cache_read_tokens == 0` after two turns
of 531. CI cannot run (GitHub billing, see status.md); the same gate ran locally on both Pythons.
