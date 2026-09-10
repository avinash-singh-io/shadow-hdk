---
type: History
phase: 11-contained-sandboxes
---

# Phase 11 — history

Append only. Newest at the bottom.

### [DECISION] 2026-09-10 — D25: containment is proven at construction, and refused if it cannot be
Topics: sandbox, contained, proof, gvisor, firecracker, d25
Affects-phases: none
Affects-specs: specs/architecture/decisions.md, specs/architecture/adapters.md

Phase 3 made `contained` a deployment fact with no default and trusted the deployment's word. The
obvious next step — `ContainedSandbox(backend=GVisor())` sets `contained: true` because the caller
said gVisor — is the same design with a nicer name and the same hole.

So a backend proves itself. Each knows one thing that is true inside it and false on the host, the
sandbox runs that probe *through the backend* before registering anything, and a probe that fails or
a binary that is absent **raises at construction** with the reason. No fallback to an uncontained
subprocess: the person who asked for containment must be told, not quietly handed a leash.

At construction rather than call time because the claim is read by governance when the *catalogue*
is computed (Phase 3: a mode requiring containment hides what cannot provide it), so it has to be
true before the first catalogue, not discovered on the first call.

*Rejected:* trusting the name; falling back with a warning (a log line is not the same severity as
a false governance input); probing per call. *Overturned by:* a backend whose proof cannot be seen
from inside, which would want an attestation port — D22's kind of seam, and its own decision.

### [NOTE] 2026-09-10 — what this machine cannot do, decided before building
Topics: sandbox, macos, linux, scope
Affects-phases: none
Affects-specs: none

macOS, no gVisor, no Firecracker, no container runtime, and a standing rule against installing any.
The contract, the seam, the fake backend and the two real backends *as code* are buildable here;
running either real backend and observing its proof is not. The second half is `[~]` with the
command that settles it, and a backend that has never run is not called done.

---

### [ARCH_CHANGE] 2026-09-10 — the leash moves below both sandboxes
Topics: sandbox, leash, invariants, runtime
Affects-phases: none
Affects-specs: specs/architecture/runtime.md, specs/architecture/adapters.md

`ContainedSandbox` first subclassed `SubprocessSandbox`, and `test_no_adapter_imports_another`
refused it. That invariant is what lets a host install any subset of adapters, so the leash the
two share — timeout, output cap, scrubbed environment — moved into `runtime/leash.py` and each
sandbox wraps it its own way. Phase 3's sandbox delegates and is otherwise unchanged.

### [DISCOVERY] 2026-09-10 — a timed-out child was never checked dead, again
Topics: sandbox, timeout, mutation-check, vacuous-tests
Affects-phases: none
Affects-specs: none

Deleting the kill on timeout left every test green. The existing timeout test asserts the error
text and the elapsed time, and both are identical whether the child was killed or merely
abandoned: `wait_for` returns on the deadline either way and the orphan carries on. Phase 4
recorded exactly this gap. A new test asks the child to leave a marker if it survives; the
mutation now bites.

### [NOTE] 2026-09-10 — the two real backends exist as code and have never run
Topics: gvisor, firecracker, live-tests, linux
Affects-phases: none
Affects-specs: none

Shape tests pass; live tests skip naming what they need; the commands that settle them are in
tasks.md. Firecracker has no single-command mode, so the deployment supplies a launcher and the
backend prefixes it — recorded rather than faked.

---
