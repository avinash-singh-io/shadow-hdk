---
type: History
phase: 16-mqtt
---

# Phase 16 — history

### [DECISION] 2026-09-10 — D32: the envelope is the payload
Topics: mqtt, d32, envelope
Affects-phases: none
Affects-specs: specs/epics/0007-the-environment.md, specs/architecture/adapters.md

Measured before decided: the only broker this suite can run speaks MQTT 3.1.1 and refuses v5, so
the key, the stamp and the exit travel in a JSON envelope in the payload. v5 properties rejected
as a contract proven against nothing; a hybrid rejected as two contracts. What was learned the hard
way: a spike that polled with `time.sleep` on the broker's own loop hung for ten minutes.

---

### [NOTE] 2026-09-10 — the dependency, measured then recorded
Topics: dependencies, licences
Affects-phases: none
Affects-specs: none

`paho-mqtt` 2.1.0 is EPL-2.0 OR BSD-3-Clause; `amqtt` 0.12.0 MIT with MIT/BSD-3 dependencies; both
wheels fetched. `amqtt` pins `websockets==15.0.1`, moving the dev resolution down from 16.1.1 —
a dev-only cost, recorded so nobody later wonders why.

---

### [DISCOVERY] 2026-09-10 — the dev broker stalls its shutdown on a clean goodbye mid-delivery
Topics: amqtt, broker, testing
Affects-phases: none
Affects-specs: none

`amqtt` 0.12's `shutdown()` waits up to forever when a client sends a clean DISCONNECT while a
QoS 1 delivery to it — a retained message, typically — is still in flight; its broadcast loop
waits on a PUBACK that will never come. A client that simply vanishes is handled fine — which is
why the mutation *the DISCONNECT is not delivered* survives: the hygiene it performs is invisible
to this broker, and equivalent for this suite. Deterministic, found on the closed-link test, which
now waits for the retained message before closing; the fixture caps a stalled shutdown at three
seconds with a warning naming the cause. Not our adapter's defect; recorded so nobody re-finds it.

---

### [NOTE] 2026-09-10 — three groups measured; what this machine cannot prove, named
Topics: mqtt, mutation, environment
Affects-phases: none
Affects-specs: none

Group 1: 18 tests, 23 of 24 mutations bite. Group 2: 3 tests, 3 of 4 mutations bite — the
fourth, *a failed connect keeps the client*, is a network thread not joined rather than anything a
run can see (the next use finds the session closed and reopens), so it is equivalent for the suite
and kept as hygiene in the code. Two races were
the tests' own, not the adapter's: a first read on a fresh subscription must wait a short grace
for a retained message (3.1.1 has no end marker — the adapter now does), and a publish right after
connect must wait for the SUBACK (the link now tracks them and offers `subscribed()`). Two claims
are design statements this suite cannot prove and says so: a PUBACK that never comes with the
broker alive but silent (`_break` and `reconnect_on_failure=False`, so nothing in flight is
re-sent) — `amqtt` always acks — and MQTT v5 properties, which no broker here can carry (D32).

---

### [NOTE] 2026-09-10 — a system-design pass over the adapter as built
Topics: mqtt, link, concurrency, backpressure, design
Affects-phases: none
Affects-specs: none
Detail: `design.md` in this phase draws the adapter as built at `5025679` — requirements, the
three-actor concurrency model, the link's state machine, the failure table, the trade-offs behind D32
and the one-link topology — and ranks what a review of it finds. Two findings were reproduced against
the local broker rather than read from the code.

---

### [DISCOVERY] 2026-09-10 — two P1 races in `MqttLink`, and four smaller gaps
Topics: mqtt, link, concurrency, backpressure, wildcards, tls
Affects-phases: none
Affects-specs: none
Detail: BUG-002 — two concurrent first uses of one link open two sessions (measured: a witness
queues one publish twice; `close()` leaves one client connected). BUG-003 — registration mutates the
filter sets without the lock the network thread iterates under, and paho re-raises callback
exceptions, which ends its thread with the link still reporting connected. TD-002 (unbounded witness
queue), ENH-001 (a wildcard sensor cannot say which topic it read), ENH-002 (TLS option, `[~]`),
ENH-003 (a protocol-adapter contract suite for the `[~]` rows). The two bugs belong before this
phase's gate.

---

### [NOTE] 2026-09-10 — Group 3: the review's P1s fixed; a stress test that proved nothing
Topics: mqtt, concurrency, mutation, review
Affects-phases: none
Affects-specs: none

The review arrived uncommitted in the working tree between two ticks and was committed unchanged
before anything else (`008f417`). Its two P1s were reproduced first — three concurrent connects
opened three sessions; a registration table set after its filter — then fixed: one `asyncio.Lock`
across the open path and `close()`, registration under the thread lock with tables before filters,
a re-check in `_open` for a device registered while it opened (the window is hit deterministically
by injecting the registration on the opening thread), and a routing fault counted rather than fatal.
Four mutations survived the first pass because the test meant to catch them — two threads racing
registration against routing for three thousand iterations — passed with and without the lock:
under the GIL the window is too small to hit on purpose. A stress test that cannot fail is not a
test; it was replaced by the claims themselves (a recording lock; a filter set that refuses an add
whose table does not exist yet) and by the one fault the try/except does not wrap, in
`on_subscribe`, which is what keeps `suppress_exceptions` from being dead code. Fourteen mutations
bite. TD-002 and ENH-001 were small enough to land beside them; ENH-002 is `[~]` for a TLS broker;
ENH-003 stays open as the first step of OPC-UA or ROS 2.

---

### [DISCOVERY] 2026-09-10 — a whole-harness architecture review: eleven bugs and seven debts filed
Topics: runtime, resume, leases, wire, agent, transcript, sandbox, workspace, mypy, ci, derivation, sinks, posture, spec-drift, landing
Affects-phases: phase-0-the-runtime, phase-1-real-adapters, phase-3-workspace-and-code, phase-4-the-acp-bridge, phase-6-the-compiler-complete, phase-7-sub-agents, phase-8-patterns-skills-replay, phase-9-the-wire, phase-11-contained-sandboxes, phase-12-derivation, phase-14-telemetry, phase-15-environment-contract
Affects-specs: specs/architecture/runtime.md#the-drive, specs/architecture/runtime.md#the-governed-step, specs/architecture/wire.md#rules-already-fixed, specs/architecture/adapters.md#the-workspace-and-code-adapters, specs/architecture/file-structure.md, specs/architecture/testing.md#layers, specs/status.md, specs/planning/roadmap.md
Detail: A design-lead read of the whole harness at `1b91815` — specs in full, kernel and the governed
step by hand, five reviewers over runtime, wire, core adapters, environment adapters and process —
with the headline claims reproduced by execution. The architecture holds: the lattice is a GLB with
an order, one step judges everything, layering is a test, refusal is its own kind. Four things the
design says are not true in the code and were filed P0: the lease and `seq` reset on every resume
(BUG-004, reproduced: five steps under a three-step lease), the transcript drops the assistant's
tool calls so a strict provider rejects turn two (BUG-005), `resume` over the wire always raises and
`serve` has no trust boundary (BUG-006), and mypy strict silently skips three packages with nine
live errors in `wire` (BUG-007, reproduced). CI has never run on a phase commit — zero PRs, two runs
at founding — so every green gate so far is a local run reported by the session that wrote the code
(TD-009). BUG-008–014 and TD-003–008 carry the rest. The review recommends fixing the gate first,
one PR from this branch to `main` for a single CI run over the linear stack, and landing once: the
Rule 6 landing order is for concurrent lanes and this stack never diverged. Published as
*shadow-hdk Architecture Review*; nothing in the repository was changed by the review itself.

---

### [NOTE] 2026-09-10 — five diagrams of the adapter, one question each
Topics: mqtt, link, envelope, diagrams, design
Affects-phases: none
Affects-specs: none
Detail: `diagrams/` beside `design.md`: an architecture map (who talks to whom, and the package
boundary), the act as a sequence (what happens in time, the two words for *done*), the link's
lifecycle (which states it can be in, and that lost reopens while closed does not), the envelope as
a dataflow (where each payload lands: latest per sensor filter, deque per witness filter, waiter per
key), and the act's outcomes as a workflow (every observation an actuator step can produce). Sources
are the `.json` files; every HTML passed the showcase gate with zero errors and warnings. Automated
browser evidence is `skipped` — no Chrome on this machine.

---
