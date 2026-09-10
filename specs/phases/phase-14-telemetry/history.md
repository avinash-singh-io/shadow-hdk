---
type: History
phase: 14-telemetry
---

# Phase 14 — history

### [DECISION] 2026-09-10 — D28: telemetry carries the shape of a run, never its payloads
Topics: telemetry, d28, observer
Affects-phases: none
Affects-specs: specs/architecture/decisions.md, specs/architecture/adapters.md#otel

A span carries ids, kinds, reasons, the lease, usage and an act's receipt; never inputs, outputs,
proposals, compositions or grounds. An observer exports to wherever the deployment chose, and the
record already exists in the stream and the sink. Rejected: everything as attributes (a worse copy
of the record, truncated at a vendor's limit); a per-deployment allowlist (configuration nobody
asked for). Overturned by a deployment wrapping the observer.

---

### [NOTE] 2026-09-10 — the API alone, measured before it was declared
Topics: dependencies, opentelemetry
Affects-phases: none
Affects-specs: none

`opentelemetry-api` 1.44.0 was already in the lock, required by the MCP adapter. The `otel`
package declares it and nothing else beyond the kernel: no SDK, no exporter. With no provider the
API is a no-op by design, which is the property the tests must prove rather than assert. The file
sink goes to `basic`: it needs no dependency, and the package boundary follows the dependency
boundary.

---

### [NOTE] 2026-09-10 — Group 1: the trace, measured
Topics: telemetry, mutation, observer
Affects-phases: none
Affects-specs: none

Twenty-two RED-first tests, every kind through a real run where the runtime can produce it and by
hand where the environment is the point. Thirty-two mutations; three survived the first pass, all
of one shape: the property held *after* `Ended` swept whatever was open, not mid-run — an observed
step's release, and non-recording spans not being kept while a run is still open. A parked run is
never `Ended` in the process that parked it, so mid-run is where a leak would live; both are now
tested with the run still open. Two design corrections found by building: a refused step has no
step span (governance refuses before `Invoked`), so `Refused` and `Asked` are run-span events; and
a resumed step gets a second, lazily opened span rather than a re-used one, because LangGraph
re-runs the node and emits `Invoked` again.

---

### [NOTE] 2026-09-10 — Group 2: the record, measured; two equivalent mutants
Topics: durability, file-sink, mutation
Affects-phases: none
Affects-specs: none

Eight tests, each saying what it proves about durability without a crash. Twelve mutations; ten
bite and two are **equivalent**, recorded as such rather than tested around: `fsync` of a second
descriptor on the same file — POSIX flushes the *inode*, so that is a descriptor leak and not a
durability difference, and the test's claim was narrowed to *this file*; and `continue` for
`return` at a torn tail — a line without a newline can only be the last line, so the two cannot
differ. A write that fails is proven by closing the descriptor under the sink: from the sink's side
that is what a full disk is, an `OSError` from `write`, and through a run the step is `Failed`.

---

### [ARCH_CHANGE] 2026-09-10 — additive: `otel` exists; `basic` gains a file sink
Topics: adapters
Affects-phases: none
Affects-specs: specs/architecture/adapters.md#packages

Additive (Rule 10): the `otel` row the table carried since founding is now built, and `basic`
lists the file sink beside the stdout sink. Applied at the phase's end.

---
