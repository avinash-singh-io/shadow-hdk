---
type: Tasks
phase: 14-telemetry
---

# Phase 14 — tasks

## Group 0 — the package, on the API alone
- [ ] `packages/adapters/otel/` at 0.7.0, kernel + `opentelemetry-api` only; workspace, ruff, mypy
- [ ] `test_versions` and `tests/invariants` green
- [ ] Gate

## Group 1 — the trace
- [ ] `OpenTelemetryObserver` — the D28 mapping
- [ ] test-local recording tracer over the API's abstract classes
- [ ] RED: every kind through a real run; child parented; resumed stream; no provider; raising provider; D28 held
- [ ] Gate

## Group 2 — the record
- [ ] `FileSink`, `proposals_in`
- [ ] RED: visible before return; fsync on the fd; torn tail; failing write raises as the step's `Failed`
- [ ] records, board, status, roadmap
- [ ] Gate
