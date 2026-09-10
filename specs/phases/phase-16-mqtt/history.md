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
