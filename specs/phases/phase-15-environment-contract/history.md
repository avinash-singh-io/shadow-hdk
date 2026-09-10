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
