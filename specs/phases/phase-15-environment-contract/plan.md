---
type: Plan
phase: 15-environment-contract
---

# Phase 15 — plan

```
# Sequential: Group 0 → 1 → 2. Group 0 is the contract; 1 is governance; 2 the devices.
```

## Group 0 — posture on the record (the contract change)

- `Observed.posture: Posture = "controlled"`; every package to **0.8.0** (D9); `test_versions`
  says why; schemas republished and their test green
- `StepExecutor` stamps the posture from the registration at `_observe`; a step that failed before
  a registration was resolved is `controlled` — the runtime refused it, which is control
- RED: through a real run, observed and controlled; the observation cannot override it; round-trip;
  the Event schema has the field with its default

**Commit:** `feat(kernel)!: every observation carries the posture of what produced it`

## Group 1 — governance sees posture

- `Context.attributes["posture"]` and `["component"]` set by the executor before `judge`
- `basic.Controlled(inner)`: refuses an observed component whose effects write or reach, naming the
  posture; defers to `inner` otherwise
- RED: refusal names the posture; observed read admitted; controlled write admitted; the inner
  policy's refusal survives; the catalogue judgement (no step) is unchanged

**Commit:** `feat(adapters): only controlled satisfies consent-before-effect`

## Group 2 — the devices

- `packages/adapters/devices/` at 0.8.0, kernel + runtime: `Sensor`, `Actuator`, `Witness`
  protocols; `Reading`, `Ack`, `Overheard`; `DeviceComponents(devices, *, clock)` a `ComponentPort`
  with D29's effects, the device's posture, and Phase 13's act; `testing.py` with
  `FakeSensor(value, unit, at)`, `FakeActuator(world)` that can be told to `disconnect_after(n)`,
  `FakeWitness(overheard)`
- RED (Epic 0007's criteria): receipt with the lease at the act; spent lease refuses and the world
  is untouched; disconnect mid-act is `Failed` and no receipt; a witness's act is an observed
  receipt naming the device; a reading's age by the runtime's clock, moving the clock; the
  effects of each role; a device that is both is refused at registration
- records, board (*Pins* row), status, roadmap

**Commit:** `feat(adapters): sensors read the world, actuators write it, a witness reports it`
