---
type: Plan
phase: 14-telemetry
---

# Phase 14 — plan

```
# Sequential: Group 0 → 1 → 2. Group 0 is the package; 1 the trace; 2 the record.
```

## Group 0 — the package, on the API alone

- `packages/adapters/otel/` — `shadow-hdk-adapters-otel` 0.7.0, depends on the kernel and
  `opentelemetry-api` only; MIT; wired into the workspace, ruff and mypy
- `tests/test_versions.py` and `tests/invariants` green over the new package

**Commit:** `chore(adapters): the otel package exists, on the API alone`

## Group 1 — the trace

- `adapters/otel/observer.py`: `OpenTelemetryObserver(tracer=None)` — `None` is
  `trace.get_tracer("shadow_hdk", <version>)`, resolved through the API's proxy so a provider
  configured later is honoured; per-run state keyed by `run_id`, per-step by `(run_id, step)`
- The mapping of D28, with attribute names from the events' fields under `shadow_hdk.`
- `tests/adapters/otel/conftest.py`: a recording `TracerProvider`/`Tracer`/`Span` over the API's
  abstract classes — test-local, because the SDK is not a dependency and must not become one
- RED: run span brackets `Started`/`Ended` with lease, reason, steps; step span parented on the
  run span with component; `Spent` on the step span; `Refused` as a run-span event with the
  reason; `Asked` ends the step span `parked`; `Spawned`/`Held` as parent events; a child run's
  span parented on the parent's; `Observed(Acted)` carries the receipt and not the grounds; a
  secret in an input appears on no span; a resumed stream (no `Started`) traces; no provider → no
  raise and nothing left in the observer; a raising tracer → `Ended` as it would have been and
  `observer_failures == 1`; every kind, through a real run

**Commit:** `feat(adapters): the run's shape as a trace, over the OpenTelemetry API alone`

## Group 2 — the record

- `adapters/basic/sinks.py`: `FileSink(path)` — append, one JSON line per proposal,
  `os.write` then `os.fsync` before returning; `proposals_in(path)` reads back, stopping at a torn
  tail
- RED: visible to a second descriptor before return; `fsync` on the file's own fd; a torn tail
  yields the whole lines and nothing else, and the completed line on the next read; a failing
  write raises, and through a real run the step is `Failed`; round-trip through the contract

**Commit:** `feat(adapters): a file sink that does not return until the line is on disk`

## Records

- tasks, history, status, roadmap, board (no *Pins* row: no contract changed)
