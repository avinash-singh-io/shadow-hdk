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

### [ARCH_CHANGE] 2026-09-10 — Group 2: `--stdio`, and a refusal that reaches the model
Topics: wire, stdio, refusal, j1, research
Affects-phases: none
Affects-specs: specs/architecture/wire.md, specs/architecture/refusal.md

The second transport: JSON-RPC over a pipe, the runtime as the child, proven against a real second
interpreter rather than a simulated one. Newline-delimited framing, so a host that already speaks to
an MCP or ACP server needs no second framing.

Alongside it, `specs/architecture/refusal.md` — the answer to J1, asked generically at the owner's
direction rather than as a coding-CLI question.

### [DISCOVERY] 2026-09-10 — a pipe read that blocks for a full buffer
Topics: stdio, pipes, wire
Affects-phases: none
Affects-specs: none

The child read its own stdin with `read(65536)`. `BufferedReader.read(n)` blocks until it has all n
bytes or the pipe closes, so the child answered nothing until its parent hung up — indistinguishable
from a hung child.

What made it expensive: piping a single frame in from a shell **hides it completely**, because the
shell closes the pipe and the read returns at end-of-file. The child looked perfect by hand and hung
under a live parent. A line-framed protocol reads lines.

### [DISCOVERY] 2026-09-10 — the research found a bug in our own refusal path
Topics: refusal, governance, j1, agent-adapter
Affects-phases: none
Affects-specs: specs/architecture/refusal.md

Two findings from the survey landed on our code. We already satisfied the harder one — every tool
call is answered, which the provider APIs require and which is the most commonly filed bug in
approval implementations. And our observation types already separate *you may not* from *it broke*,
which almost nothing surveyed does on the wire.

**That structure is what made the bug invisible.** `carry_out` collected only `observed` events, and
a refusal emits `refused` and no `observed` — the same fact Phase 5 recorded when the RecordingServer
fell into it. So a refused tool call reached the model as *"that step did not run"*: no reason, and
indistinguishable from a step that never happened. The governance decision reached the record and
never reached the model.

### [NOTE] 2026-09-10 — a gate run invalidated by a background mutation harness
Topics: process, gate, mutation-check
Affects-phases: none
Affects-specs: none

A full-suite run reported five stdio failures that were not real: a mutation harness was running in
the background, rewriting the very files the suite was importing. The harness restores each file
after each mutation, so nothing was corrupted — but for the minutes it ran, the source on disk was
not the source under test.

The gate means nothing unless it is the only thing touching the tree. Re-run clean, all four zero.

---

### [ARCH_CHANGE] 2026-09-10 — Group 3: `serve`, and Phase 5's debt paid
Topics: wire, serve, http, sse, sessions, phase-5-debt
Affects-phases: none
Affects-specs: specs/architecture/wire.md

The last transport wire.md names. Phase 5 found that the RecordingServer can only be connected to,
never launched — a server holding a live `RunContext` cannot be started fresh by somebody else — so
a child on another machine had no way in.

**The direction is the design.** The ports invert, but an HTTP server cannot call its client, so the
host POSTs its calls and replies while the runtime's callbacks *and* the run's events come back down
one SSE stream. `Channel` already hid both from the protocol, so `RuntimeSide` and `HostSide` are
untouched. That is the payoff for building the loopback first: the wire grew a transport rather than
a second implementation.

A **session per connection**, opened by the SSE stream. Without it a second client would join the
first's session and answer its callbacks.

### [SCOPE_CHANGE] 2026-09-10 — the run token is recorded, not invented
Topics: wire, authentication, run-token
Affects-phases: none
Affects-specs: specs/architecture/wire.md

wire.md specifies a run token: *short-lived, single-run, minted when a run opens, carrying the scope,
principal and lease.* What is built is a **session id** — unguessable, scoping one connection, and
proving a client is the one that opened the stream. That is connection identity, not a capability.

The gap is deliberate. A real run token has to be *minted* by something, and who mints it is an
authentication question that belongs to the host's identity system rather than to this package —
wire.md's own next sentence is that *the runtime never holds a host credential*, which it does not.
Inventing a token format here would be inventing the answer to somebody else's question.

Recorded with what is and is not true today, so the next reader does not mistake a session id for a
capability.

### [DISCOVERY] 2026-09-10 — a test bound that could never fire, and what it cost
Topics: tests, timeouts, mutation-check
Affects-phases: none
Affects-specs: none

The socket tests bounded themselves with `anyio.fail_after(120)`. The global pytest timeout is 60,
so that bound could never fire — it was decoration.

It was not free. A mutation run pays every bound **in full** on each broken variant, so eight
mutations against a transport took over ten minutes and had to be moved to the background, where it
then collided with nothing only because the lesson from the previous run was already learned. Thirty
seconds is generous for localhost and makes the same run finish in about one minute.

---
