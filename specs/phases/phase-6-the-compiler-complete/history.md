---
type: History
phase: 6-the-compiler-complete
---

# Phase 6 — history

Append only. Newest at the bottom.

### [DECISION] 2026-09-10 — D15: cancellation is a handle, checked where the lease is checked
Topics: cancellation, d15, runtime, leases
Affects-phases: phase-7
Affects-specs: specs/architecture/runtime.md#the-drive, specs/architecture/decisions.md

`errors.py` has had `Cancelled` and `EndReason` has had `"cancelled"` since Phase 0, with nothing
raising either. The question this phase had to answer was not whether a run can be cancelled but
**who asks, and where the question is asked.**

A run already stops for reasons of exactly one shape: the executor asks, before spending a step,
whether it may. The lease is asked that at the top of `invoke`. Cancellation is the same question
from a different asker, so it belongs in the same place — asked *first*, before the lease, because a
cancelled run should not spend the step it was about to be refused for.

*Rejected:* a `CancelPort`. A port is what the host implements **for** the runtime; this is the host
reaching **in**, which is what `Lease` already is. As a port the runtime would poll the host every
step for a value the host already knows.

*Rejected:* cancelling the asyncio task. It works and says nothing — no `Ended`, no reason, no
record, and a component mid-write cut in half.

*Overturned by:* a host needing to stop a run between two of its own awaits rather than at a step
boundary, which would mean step granularity is too coarse.

---
