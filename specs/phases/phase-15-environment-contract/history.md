---
type: History
phase: 15-environment-contract
---

# Phase 15 — history

### [DECISION] 2026-09-10 — D29, D30, D31 (Epic 0007)
Topics: environment, posture, devices, d29, d30, d31
Affects-phases: phase-16-mqtt
Affects-specs: specs/epics/0007-the-environment.md, specs/architecture/adapters.md

`09` does not speak on the environment; `10` §364–371 and `08` §4 do. D29: the world is a scope
and a device a component, not a port. D30: posture is stamped on every observation by the runtime
and put in front of governance — the record must not depend on a driver's honesty about its own
posture. D31: one device contract with three roles, the fake first. What was rejected is in the
overview beside each.

---

### [NOTE] 2026-09-10 — what this machine cannot prove, said before building
Topics: mqtt, opc-ua, ros2, environment
Affects-phases: phase-16-mqtt
Affects-specs: none

No MQTT, OPC-UA or ROS client is resolvable here and no broker is installed (`mosquitto`, `ros2`
absent). Phase 15 therefore proves the contract with fakes only. Phase 16's question is whether
`paho-mqtt` and a pure-Python broker for the suite can be added as wheels with a recorded reason;
OPC-UA and ROS 2 are `[~]` in the epic naming what settles them.

---

### [ARCH_CHANGE] 2026-09-10 — the executor's second catalogue computation is deleted
Topics: runtime, catalogue, visibility
Affects-phases: none
Affects-specs: specs/architecture/runtime.md#class-diagram, specs/architecture/runtime.md#modules

`StepExecutor.visible` duplicated `RunContext.visible` and was called by one test and nothing in
production. Group 1 found it the way duplication is usually found: a mutation in it survived
because nothing real ran it. Deleted; the test it served goes through a run. Two layers, one job.

---

### [NOTE] 2026-09-10 — three groups measured; one survivor was the fake being bland
Topics: posture, devices, mutation
Affects-phases: phase-16-mqtt
Affects-specs: none

Group 0: 3 tests, 3 mutations bite. Group 1: 7 tests, 10 bite, the catalogue judgement corrected
to see posture — the plan said *unchanged*, and building showed that would offer the model an
observed actuator it could never invoke. Group 2: 11 tests, 21 bite; the one survivor invented the
exit `done`, which was also the fake's word for everything — the fake now answers `acknowledged`,
because a device's own word is what the receipt carries. The spent-lease refusal is proven with a
catalogue that takes 601 s to answer between the step's admission and the act; a link that drops
after the command went out is `Failed` with no receipt while the fake shows the command was sent
— the world may have moved, and the key handed to the device is what a retry is for.

---
