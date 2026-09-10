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
