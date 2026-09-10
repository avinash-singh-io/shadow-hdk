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
