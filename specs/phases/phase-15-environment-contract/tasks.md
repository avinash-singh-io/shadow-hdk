---
type: Tasks
phase: 15-environment-contract
---

# Phase 15 — tasks

## Group 0 — posture on the record
- [ ] `Observed.posture`; every package to 0.8.0; `test_versions` reason; schemas republished
- [ ] the executor stamps posture from the registration
- [ ] RED: observed/controlled through a run; the observation cannot override it; round-trip; schema
- [ ] Gate

## Group 1 — governance sees posture
- [ ] `Context.attributes["posture"]`, `["component"]`
- [ ] `basic.Controlled`
- [ ] RED: names the posture; observed read admitted; controlled write admitted; inner survives; catalogue unchanged
- [ ] Gate

## Group 2 — the devices
- [ ] `adapters/devices`: three roles, `DeviceComponents`, fakes
- [ ] RED: the epic's criteria that name a fake
- [ ] records, board (*Pins* row), status, roadmap
- [ ] Gate
