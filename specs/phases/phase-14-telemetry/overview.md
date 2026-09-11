---
type: Phase
phase: 14
name: telemetry
epic: 0005-the-body
status: complete
topics: [telemetry, opentelemetry, observer, sink, durability, d28]
deps: [phase-13-effect-leases]
---

# Phase 14 — Telemetry

## Goal

Roadmap: *OpenTelemetry observer; file sink.* `09`'s build-versus-buy table has one row for it —
*exporting the event stream: OpenTelemetry* — and `adapters.md` has carried an `otel` observer
adapter against this phase since founding. Two things leave the runtime for people who run it:
**where time went and why a run stopped** (the trace), and **what the runtime proposed** (the
record). This phase gives each a home that needs no product: an observer over the OpenTelemetry
*API*, and a sink that appends JSON lines to a file and does not return until they are on disk.

## D28 — telemetry carries the shape of a run, never its payloads

An observer exports to wherever the deployment pointed it — a collector, a vendor, a file it does
not control. The event stream already carries everything: inputs, outputs, proposals, compositions,
the grounds of an act. A trace that copied them would make every export a second place customer
data and secrets live, subject to a vendor's attribute limits that truncate at a size nobody
chose, and it would tell an operator nothing a trace is for.

So a span carries the **shape**: run and step ids, the component, event kinds, the reason a step
was refused or a run ended, the question a step parked on, the lease and what was spent, and — for
an act — its receipt (foreign id, idempotency key, exit), because attribution is exactly what an
operator traces. It never carries `inputs`, an observation's output, a proposal's payload, a
composition, or an act's grounds. Attribute names are the events' own field names under `shadow_hdk.`;
nothing is invented.

**Rejected.** *Everything as attributes* — the obvious thing; attribute values must be primitives,
so nested payloads collapse to strings and the trace becomes a worse copy of the record. *A
per-deployment allowlist* — configuration nobody asked for, whose default would still be one of the
two. **Overturned by** a deployment that wants payloads in its traces: it wraps this observer, or
writes its own over `CallbackObserver` — the seam exists for that.

## The mechanism, and its recorded reasons

- **The API alone.** The adapter depends on `opentelemetry-api`, never the SDK or an exporter. A
  library that pins the SDK forces a provider on its host; the API with no provider is a no-op by
  design (`ProxyTracer` → `NonRecordingSpan`), which is the *unconfigured costs nothing* property
  this phase must prove rather than assert. **Measured 2026-09-10:** `opentelemetry-api` 1.44.0 is
  already in the lock, required by the MCP adapter, so declaring it adds no download.
- **One span per run, one per step.** `Started` opens the run span (a child's is parented on the
  parent's, from `parent_run_id`); `Invoked`/`Observed` bracket a step span; `Spent` sets usage on
  the open step span; `Refused`, `Asked`, `Spawned`, `Held` are span events with their fields;
  `Ended` closes with the reason and steps taken, status `ERROR` only for `failed`.
- **A stream this process did not see start.** A run that parked is resumed wherever the host
  chooses; the observer there sees `Observed` before any `Started`. Spans open lazily on first
  sight of a run or a step, so a resumed run still has a trace, joined to the first by `run_id`.
  A step that parks (`Asked`) ends its span with a `parked` event rather than staying open forever.
- **A provider that raises does not fail a run**, and the observer does not hide that it raised:
  the emitter counts it (D6). Tested by varying the environment, not by reading the code.
- **The file sink lives in `basic`.** It needs no dependency, and the package boundary follows the
  dependency boundary — `otel` exists because of one import. `FileSink` writes one JSON line per
  proposal and **fsyncs before it returns**; a reader tolerates a torn last line; a write that
  fails (disk full) **raises**, because a proposal that was not recorded must not be reported as
  recorded — the step that proposed it fails, which is D7's rule for a component.

## Not in this phase

Metrics and logs signals; a collector, an exporter, or any configuration of one; sampling; a
`RunContext` for propagating a trace context *into* a component (a component that wants the span
can ask the API for the current one). The environment epic follows this phase.

## Done when

- `tests/adapters/otel/`: every event kind reaches a span or a span event, through a **real run**
  with `Ports(observer=OpenTelemetryObserver(...))` and a test-local recording tracer over the API's
  abstract classes; a child run's span is parented; a resumed stream traces; no provider → no
  raise, no state left behind; a raising provider → the run ends as it would have and the emitter
  counted it; D28 held by a test that puts a secret in an input and finds it on no span
- `tests/adapters/basic/test_file_sink.py`: a line visible to a second reader before `propose`
  returns; `fsync` invoked on the file's own descriptor; a torn tail does not poison the next read;
  a failing write raises through a real run as the step's `Failed`
- gate: ruff 0, format 0, mypy 0, pytest 0; every mutation bites; no adapter imports another
