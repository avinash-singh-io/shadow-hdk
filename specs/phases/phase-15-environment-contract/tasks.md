---
type: Tasks
phase: 15-environment-contract
---

# Phase 15 — tasks

## Group 0 — posture on the record
- [x] `Observed.posture`; every package to 0.8.0 (sixteen); `test_versions` reason; schemas republished
- [x] the executor stamps posture from the registration — a step that never reached a component is `controlled`
- [x] RED: observed/controlled through a run; a step failed before a component is controlled; round-trip and default — 3 tests
- [x] Gate — 3 mutations bite

## Group 1 — governance sees posture
- [x] `Context.attributes["posture"]`, `["component"]` — through `Session.context_for(step, registration)` at the step and at the catalogue
- [x] `basic.Controlled`
- [x] RED: names the posture; observed reach refused; observed read admitted; controlled write is the inner policy's; governance told posture and component; the catalogue omits what Controlled would always refuse; a refusal is a refusal — 7 tests. **The catalogue judgement is not unchanged**: it sees posture too, or the model is offered what it can never invoke
- [x] Gate — 10 mutations bite; the eleventh, in `StepExecutor.visible`, survived because nothing real ran it — deleted (two layers, one job)

## Group 2 — the devices
- [x] `adapters/devices` at 0.8.0: `Sensor`/`Actuator`/`Witness`, `Reading`/`Ack`/`Overheard`, `DeviceComponents`, `testing.FakeSensor/FakeActuator/FakeWitness`
- [x] RED: each role's effects and posture; one id one role; a reading's age by the runtime's clock (moved); a stamp that cannot be read; a receipt with the lease at the act; a spent lease via a catalogue that takes 601 s; a link that drops mid-act; a witnessed act as an observed receipt naming the device; the device's own key kept; Controlled admits witness and actuator alike; an actuator outside a run — 11 tests
- [x] records, board (*Pins* row 0.7.0 → 0.8.0), status, roadmap
- [x] Gate — ruff 0 / format 0 / mypy 0 (109 files) / pytest 659 passed, 9 deselected; 21 mutations bite, one after the fake stopped answering the same word the mutant invents
