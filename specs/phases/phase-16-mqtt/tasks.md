---
type: Tasks
phase: 16-mqtt
---

# Phase 16 — tasks

## Group 0 — the package, the dependency, the contract below the adapters
- [x] `packages/adapters/mqtt/` at 0.8.0; `paho-mqtt` 2.1.0 and dev `amqtt` 0.12.0 fetched, licences recorded
- [x] contract moved to `runtime/devices.py`; `adapters/devices` re-exports; 659 tests still green
- [ ] `Reading.stamped_by`
- [x] Gate

## Group 1 — the link and the three roles
- [ ] `MqttLink`; `MqttSensor`, `MqttActuator`, `MqttWitness`
- [ ] broker fixture and device-side helper
- [ ] RED: the Group 1 list in the plan
- [ ] Gate

## Group 2 — the environment varied, and the epic closed
- [ ] RED: broker not there; broker gone after connect and no delayed resend; retained versus none
- [ ] Epic 0007 `[~]` rows and criteria; records, board, status, roadmap; roadmap re-checked
- [ ] Gate
