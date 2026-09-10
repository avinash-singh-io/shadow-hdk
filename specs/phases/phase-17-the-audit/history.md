---
type: History
phase: 17-the-audit
---

# Phase 17 — history

### [DISCOVERY] 2026-09-10 — BUG-004 reproduced exactly as filed
Topics: leases, resume, durability
Affects-phases: none
Affects-specs: none

Five sequential steps under `Ceiling(max_steps=3)` with an Ask on step 3: the first leg invoked
two, the resume invoked three more, the run ended `completed` with `steps_taken=3` while five had
run, and `seq` ran 0–6 twice for one run id. `run` and `resume` both build a fresh `Session`,
`LeaseMeter` and `Emitter`, and `RunState` holds nothing about spend. An Ask is the ordinary way a
governed run pauses, so this is the lease failing in its commonest case.

---

### [DECISION] 2026-09-10 — D33: what a run has spent rides in the checkpoint; parked time is not spent
Topics: d33, leases, durability, resume
Affects-phases: none
Affects-specs: specs/architecture/decisions.md, specs/architecture/runtime.md

The meter's counters and the emitter's sequence ride in `RunState` as JSON (D19) and are read back
on resume. Elapsed seconds accumulate across legs rather than being measured from the first start,
because a run waiting for a human is not running and a person who takes a day to answer must not
find the budget gone. Rejected: a durable meter behind a port (state the runtime owns, which `09`
§6 refuses); passing the meter back in `RunOptions` (every host reimplements the accounting, and a
host that forgets gets the bug back silently); counting a re-run node once (the node really does
run again — BUG-010 — and hiding that would lie in the other direction).

---
