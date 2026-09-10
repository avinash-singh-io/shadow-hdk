---
type: History
phase: 9-the-wire
---

# Phase 9 — history

Append only. Newest at the bottom.

### [DECISION] 2026-09-10 — D19: the graph's state holds JSON, not our classes
Topics: state, checkpoints, serde, td-001, d19, wire
Affects-phases: none
Affects-specs: specs/architecture/runtime.md#compiling-a-composition, specs/architecture/decisions.md

`RunState.observations` held `Observation` objects — convenient in-process, and wrong at every
boundary they actually cross.

**A checkpoint is a wire.** It crosses a process (Phase 6 measured a run resuming from a file after
the saver that wrote it was gone), it crosses a version (a run parked by one build, resumed by the
next), and it crosses into a store the host chose. LangGraph already warns it will stop deserialising
types it does not recognise, and the remedy it offers — a host naming
`shadow_hdk.kernel.observations` in its serializer's allowlist — pushes our internals into every
host's configuration, which is backwards for a package whose claim is that the host owns the durable
side.

So the state holds JSON and the runtime loads observations back at its own edge. This settles TD-001.

*Rejected:* the allowlist — it makes our module names part of somebody else's deployment, and a
rename then breaks it. *Rejected:* waiting until it breaks — it is green today under
`LANGGRAPH_STRICT_MSGPACK=true`, which is the window in which to move rather than the reason not to.

### [DECISION] 2026-09-10 — D20: `Spent`, the eleventh event kind
Topics: events, usage, observer, d20, phase-1-debt
Affects-phases: none
Affects-specs: specs/architecture/runtime.md, specs/architecture/decisions.md

Phase 1's exit criterion was *tokens reach the observer*, and they did not. `_usage_of` digs them out
of a `Completed` observation's output dict by convention and charges the meter; an observer wanting
to know what a run cost had to know that convention and parse somebody else's payload.

`Spent(step, usage)` is emitted where the meter is charged, so a meter, a UI and a bill read one
event kind instead of reverse-engineering an output.

*Rejected:* a field on `Observed` — most observations cost nothing, and an optional field usually
absent teaches a reader to ignore it. *Rejected:* leaving it in the output dict — that convention
stays, because it is how an adapter *reports* cost, but reporting and recording are different jobs.

---
