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

### [ARCH_CHANGE] 2026-09-10 — Group 0: a run can be stopped, and `Ended` grew `detail`
Topics: cancellation, d15, d9, contract, ended
Affects-phases: phase-7
Affects-specs: specs/architecture/runtime.md#the-drive, specs/architecture/decisions.md

`Cancellation` is a handle the host keeps and passes in `RunOptions`, asked at the top of `invoke`
before the lease. A child inherits its parent's unless handed its own. Cancellation lands on a step
boundary: a component already running is left to finish — the harness does not own other people's
code — and the next step does not start.

`Ended` grew `detail`, deliberately **general** rather than cancellation-only, because a host
reading the record should be able to tell "the user closed the tab" from a budget ceiling from a
port that broke. `_stop_reason` now carries the words up out of the exception chain with the reason.

A kernel field is a contract change: every package to **0.4.0** under D9, and a row under *Pins*.

### [DISCOVERY] 2026-09-10 — the test that proves a step is not *bought*
Topics: cancellation, mutation-check, leases

One mutation moved the cancellation check from above the meter to below it. Every assertion still
passed: nothing was `Invoked`, the reason was still `cancelled`. What the mutation actually broke
was that the run *paid* for a step it never took.

The test now asserts `Ended.steps_taken == 0` and not merely that nothing was invoked. Worth an
entry because the vacuity was in a test that looked complete — it checked the visible consequence
and not the one the design is about.

### [SCOPE_CHANGE] 2026-09-10 — "two scopes may reuse a step id" was wrong, and became its opposite
Topics: compiler, subgraphs, step-ids, state
Affects-phases: none
Affects-specs: specs/architecture/runtime.md#compiling-a-composition

The plan listed *two scopes may reuse a step id* as a thing subgraphs would buy. They cannot, and
should not. `RunState.handles` is one flat dict keyed by step id, and that flatness is exactly what
lets a `Binding` reach an earlier sibling in an outer scope. Scoping the keys would buy id reuse
nobody asked for and cost cross-scope references, which are a feature.

What the plan should have said is that a repeat is an **error** — because as it stood, two steps
sharing an id silently collapsed into one node with a self-edge. Measured rather than reasoned: the
first version of the test failed with `lease_exhausted`. The composition did not merely run the
wrong graph, it looped until its budget was gone.

`DuplicateStepId` is now raised at plan time and names the id. Which moved compilation inside the
drive's guard: a composition an agent authored badly is the agent's mistake, and D7 says no
exception from the runtime escapes `run()`, so it ends the run with a reason rather than a traceback
at the caller. `Ended.detail` from Group 0 carries it.

### [NOTE] 2026-09-10 — what subgraphs cost, in a number
Topics: d11, benchmark, subgraphs

D11 says a cost is a number, not a shrug. The same hundred steps, flat and then arranged as ten
nested scopes:

| shape | best of three | per step |
|---|---|---|
| 100 sequential steps | 53.0 ms | 0.530 ms |
| 100 steps in 10 nested subgraphs | 60.7 ms | 0.607 ms |

About fifteen per cent, against D11's budget of 1 ms a step. The nested arrangement is now a
benchmark case of its own, so the next change to the compiler is measured against it and not against
the flat shape alone.

### [DISCOVERY] 2026-09-10 — a shared thread id survived two tests before one caught it
Topics: checkpoints, resume, durability, mutation-check

The mutation was "the checkpoint thread is not the run id". It survived twice.

First because `FixedClock.new_id()` counts from one and each helper built a fresh clock, so a
counter-based id agreed across the park and the resume by coincidence. Then, with a constant thread
for every run, it survived again — because a fresh input **overwrites** a thread. Two identical
compositions cannot tell: a second run starting from the beginning proves nothing about isolation.

The test that catches it parks two runs at *different* steps and resumes the first. Under a shared
thread it wakes with nothing observed. The link between run id and checkpoint thread is now
load-bearing and tested, where a moment earlier it was neither.

### [NOTE] 2026-09-10 — durability was a claim until this phase
Topics: checkpoints, durability, hosts

`RunOptions.checkpointer` has been a parameter since Phase 0 and nothing had ever handed it a
checkpointer we do not ship. `langgraph-checkpoint-sqlite` is a dev dependency for exactly that: a
run parks on a **file**, the saver is closed and dropped, and a different saver over the same file
finishes it. Each resume test asserts it was resumed and not restarted — the step before the park is
not run again, so its work came back off the checkpoint rather than being redone.

---
