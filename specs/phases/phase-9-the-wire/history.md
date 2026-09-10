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

### [ARCH_CHANGE] 2026-09-10 — Group 0: TD-001 settled, and Phase 1's debt paid
Topics: state, checkpoints, td-001, spent, usage, d9, d19, d20
Affects-phases: none
Affects-specs: specs/architecture/runtime.md, specs/architecture/decisions.md

`RunState.observations` holds JSON (D19) and `Spent` is the eleventh event kind (D20). Every package
to **0.6.0**, and a *Pins* row: the event union is now eleven wide, so anything matching
exhaustively on `Event` sees a new arm.

**Measured, not asserted.** `LANGGRAPH_STRICT_MSGPACK=true uv run pytest -q -W default` reports
**zero** "Deserializing unregistered type" lines across 406 tests, where before this change it
reported them. TD-001 moves to closed.

### [DISCOVERY] 2026-09-10 — `ports` already imports `events`, so `Usage` had to move
Topics: kernel, imports, usage
Affects-phases: none
Affects-specs: none

`Spent` carries a `Usage`, which lived in `ports.py` — and `ports` imports `events` for
`ObserverPort`, so the reach back would have been a cycle.

`Usage` is now `kernel/usage.py`: a value type shared by two modules that cannot import each other
belongs beneath both. It is re-exported from `ports` with an explicit `as`, so every existing
`from ...ports import Usage` still works and mypy still calls it an export.

Small, but worth recording because it is the first time the kernel's own layering pushed back — and
the answer was to move the value down rather than to weaken a boundary.

---

### [DECISION] 2026-09-10 — D21: a component that crosses still needs a context, and the host binds one
Topics: wire, current-run, contextvar, propose, d21
Affects-phases: none
Affects-specs: specs/architecture/wire.md

Found by a test, not by reading. When the ports invert, a component **executes on the host** — that
is what `components.invoke` means. But `current_run()` is a contextvar set by the runtime's own loop
in the runtime's own task, so a component that crossed found `None` there and every idiom built on
it broke at once. `09`'s principle 3 is *act through components; record through the sink*, and the
way a component records is `current_run().propose(...)`.

The host now binds a `WireRunContext` for the duration of the call. What it can answer locally it
does — `ports` is the host's own bundle, and the model and the sink genuinely live there. What
belongs to the run it **crosses back for**, because there is exactly one meter and exactly one event
stream and neither is the host's.

`propose` is the interesting case: it could have written straight to the host's sink one hop
cheaper. It does not, because `RunContext.propose` emits `Proposed` *and* calls the sink, and an
event emitted host-side lands on a stream nobody reads. A mutation taking the cheap path kills the
test.

*Not across the wire yet, and saying so out loud:* `children`, `visible()` and `spawn_options()`
raise `NotAcrossTheWire` with a message naming the reason. Spawning across a wire is a real question
— which side does the child's run live on? — and it deserves its own decision rather than an
accident.

### [DISCOVERY] 2026-09-10 — the live context was captured in the wrong task
Topics: wire, contextvar, tasks
Affects-phases: none
Affects-specs: none

`RuntimeSide` first captured the running context from the loop consuming the event stream. That loop
is a different task from the one `run()` sets the contextvar in, so it read `None` every time and
nothing a component proposed ever reached the sink.

It is now captured inside `RemoteComponents.invoke`, which is called from within the step, in the
run's own task — the one place it exists.

### [DISCOVERY] 2026-09-10 — a guard deleted rather than tested
Topics: wire, d7, mutation-check, redundancy
Affects-phases: none
Affects-specs: none

`RemoteComponents.invoke` caught `RemoteError` and returned `Failed` — D7, a component is untrusted
and its raising is data. A mutation deleting the catch left every test green, and the reason is that
`step.py` already observes any exception out of a component port as `Failed`. A second catch could
not change an outcome.

So it is gone rather than pinned by a test. A guard that cannot change an outcome is a claim that
something is handled where nothing is, and a test written to defend it would have made the claim
harder to remove later.

### [SCOPE_CHANGE] 2026-09-10 — the whole suite through the wire is named, not done
Topics: wire, acceptance, testing
Affects-phases: phase-9
Affects-specs: specs/architecture/wire.md

wire.md's acceptance rule is *the wire passes the in-process runtime suite through a loopback
transport, or the wire is not done*. What exists is `drive()` with `run()`'s exact signature, so a
test moves across by changing one word, and a representative set — sequence, governance refusal,
model inversion, sink inversion, port failure — is proven both ways.

Switching all 417 needs a conftest hook and a second pytest pass, and two idioms have to cross
first: `children` (a real design question — which side does a spawned child live on?) and
`visible()`. Recorded as `[~]` with the mechanism named, so the remaining work is a task rather
than a rediscovery.

---
