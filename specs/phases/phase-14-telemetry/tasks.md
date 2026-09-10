---
type: Tasks
phase: 14-telemetry
---

# Phase 14 — tasks

## Group 0 — the package, on the API alone
- [x] `packages/adapters/otel/` at 0.7.0, kernel + `opentelemetry-api` only; workspace, ruff, mypy — no download: the API was already in the lock via `mcp`
- [x] `test_versions` and `tests/invariants` green — 8 passed
- [x] Gate

## Group 1 — the trace
- [x] `OpenTelemetryObserver` — the D28 mapping; `open_runs`/`open_steps` for what it holds
- [x] test-local recording tracer over the API's abstract classes — `tests/adapters/otel/conftest.py`
- [x] RED: every kind through a real run; child parented; resumed stream; no provider; raising provider; D28 held — 22 tests
- [x] Gate — 32 mutations bite; three held only after `Ended` swept and now hold mid-run

## Group 2 — the record
- [x] `FileSink`, `proposals_in` — in `basic`, exported
- [x] RED: visible before return; fsync of this file; torn tail; corruption names the line; failing write raises as the step's `Failed`; append across instances; mode 0600; refuses to exist unwritable — 8 tests
- [x] records, board, status, roadmap — no *Pins* row: no contract changed
- [x] Gate — ruff 0 / format 0 / mypy 0 (105 files) / pytest 638 passed, 9 deselected; 10 mutations bite, 2 equivalent (named in history)
