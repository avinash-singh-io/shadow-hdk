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

### [NOTE] 2026-09-10 — Group 1 measured; the record's numbering needed a second durable place
Topics: leases, resume, seq, mutation
Affects-phases: none
Affects-specs: none

The meter was the easy half: counters into `RunState.spent`, read back in `_stream`. The record's
numbering was not. The state's mark is written when a node **returns**, and a parking step emits
its `Asked` or `Observed(Pending)` *after* that — so restoring from the state alone handed the
resumed leg a number the parked leg had already used (`[0,1,2,3,4,5,6,6,7,…]`). The fix uses what
was already in the same checkpoint: the interrupt the step raised is ours, so it carries
`resume_seq`. Two tests hold it — no seq is reused across an ask, none across an await — and they,
not the arithmetic, are what guards it.

Seventeen mutations, three survivors, none of them a wrong line: `run` starting fresh on a reused
thread had no test; the reducer's commutativity was only ever exercised through a `FanOut`, whose
branch order cannot be forced — the Phase 16 lesson, so it is asserted directly; and
`Emitter.restore`'s floor had no caller that could break it, so it is tested at the method rather
than deleted. One transient failure in `test_benchmark` while seventeen mutation runs were still
settling; green twice immediately after, and it is the flake its own docstring records.

---

### [DISCOVERY] 2026-09-10 — BUG-015: a held child does not survive its parent's park
Topics: children, resume, durability
Affects-phases: none
Affects-specs: none

Deliberately not fixed in Group 1, because it is a design question rather than a field. A
`HeldChild` carries a `Composition`, a checkpointer and a `Cancellation` — two of those are
objects, not JSON, so D19 cannot carry them. **Reproduced:** a parent that spawns a child, parks
on an Ask, and resumes comes back with `children.held == ()`, spawns a *second* child
(`id-0002`), and leaves the first (`id-0001`) parked forever with no handle and no reachable
checkpointer. Filed P1 with this evidence so somebody decides it rather than a phase mentioning it.

---

### [NOTE] 2026-09-10 — Group 2 measured; the double that never looked
Topics: transcript, tool-calls, testing, mutation
Affects-phases: none
Affects-specs: none

The fix is three lines in three packages. What is worth recording is why it survived seventeen
phases: **every agent test used `ScriptedModel`, and a scripted model never checks the pairing
rule.** A green suite proved nothing about a real second turn, because the only party that would
have objected — a provider — was never in the room. So the tests added here are of two kinds: the
pairing rule asserted over the whole transcript rather than at one message, and one **live**
multi-turn test behind `-m live` which is the only place the bug could actually have been seen.
The same shape as BUG-007: a check that silently narrows is worse than none.

One mutation survived and was **equivalent**: `_calls_for` wrote `"type": "tool_call"`, and
`AIMessage` stamps that itself with a wrong value or with none. A literal no test could tell from
its absence is deleted, not tested around — the test asserts LangChain's output shape instead.

---

### [DECISION] 2026-09-10 — D34: a wire session owns a checkpointer; the callback timeout is the wire's
Topics: wire, resume, timeouts, d34
Affects-phases: none
Affects-specs: specs/architecture/wire.md

A `RuntimeSide` owns a checkpointer for its session — defaulting to one that lives as long as the
session, and replaceable by a host that wants a parked run to outlive the process, exactly as
`Children.spawn` already allows. Rejected: threading a checkpointer through every `run` message
(the host would have to describe an object across JSON), and dropping `resume` from the protocol
(an Ask that crosses the wire is the case the wire exists for).

The callback timeout belongs to the **wire**, not the lease. A lease bounds a run; a run waiting on
a peer that will never answer is not running, so it can never notice its own ceiling. The runtime's
peer therefore gives up on a callback and names the method in the message, so the record says which
end stopped answering. The host's peer has no timeout: a host waiting for a run to finish is
waiting exactly as long as that run's lease allows.

---

### [NOTE] 2026-09-10 — Group 3 measured; and what is not built is now said where it was claimed
Topics: wire, serve, trust, mutation
Affects-phases: none
Affects-specs: specs/architecture/wire.md

Four failures under one row, each reproduced over the loopback first. The one worth naming is the
handshake: `initialized` was set and never read, and an omitted `protocol_version` **defaulted to
this build's own** — so a peer that said nothing counted as agreeing, in a protocol whose stated
rule is *refuse, never degrade*. Silence is not agreement.

`wire.md` listed a run token under **rules already fixed** and it is not built. Rather than build a
credential design nobody has decided, `served_over_http` is loopback-only by default and refuses
any other host without a `token=` — a deployment-wide stop-gap, said to be one, and the spec now
carries the correction where the false claim was. Fifteen mutations, three survivors, all missing
coverage rather than wrong lines: `resume`'s door was untested while `run`'s was; the **default**
timeout was untested because the hang test passes its own, so `None` there would have restored the
hang for everyone who did not pass a number; and the token check had only ever been sent the right
credential or none, so a check for mere presence would have admitted anyone who sent anything.

---
