---
type: Phase
phase: 15
name: environment-contract
epic: 0007-the-environment
status: complete
topics: [environment, devices, posture, world, sensors, actuators, witness, d29, d30, d31]
deps: [phase-14-telemetry]
---

# Phase 15 — The environment contract

## Goal

Make the world reachable the way everything else is: through components governed by their effects,
with the control posture of every act on the record. Epic 0007's first phase; the protocol
adapters come after it and are shaped by it.

## D29 — the world is a scope; a device is a component with a posture, not a port

A sensor is a component whose effects are `reads: {world}`. An actuator's are
`writes: {world}, reversible: false` — a valve opened is not un-opened by a rollback — and its
observation is the `Acted` receipt Phase 13 gave every world-effect, under a lease read at the
moment of the act. A witness reads the world's own log — *the operator opened the valve at 10:02*
— and reports it as an `Acted` it did not command.

**Rejected.** *A `DevicePort`* — D22 adds a port only for a gap, and a device is something the
runtime invokes and governs like any component; a port is what the host implements *for* the
runtime. *A device observation kind* — the receipt exists. *The world as `everything`* — one named
scope is what lets a rule permit reading it without permitting writing it.

## D30 — posture is on the record and in front of governance

`Provenance.posture` has been in the kernel since Phase 0 and only the ACP adapter sets it. `08` §4
says what it must mean: `controlled` is *we gated it before it happened*; `observed` is *mechanical
evidence recorded after an external executor acted* — attributable and reconcilable, never
pre-authorised by us — and an observed run *must render as a degraded posture and never satisfy the
consent-before-effect claim*. Two things follow, and both are the runtime's, not the driver's:

1. **`Observed.posture`** — every observation on the stream carries the posture of the component
   that produced it, stamped by the runtime from the registration. A contract change, 0.7.0 →
   0.8.0 (D9), with a *Pins* row. Default `controlled`, so every existing consumer still reads.
2. **Governance sees it.** The executor puts `posture` and `component` into `Context.attributes`
   before asking; `basic.Controlled(inner)` refuses an observed component for any effect that
   writes or reaches, with a reason that names the posture, and admits an observed read — a
   sensor's reading is evidence, not an effect.

**Rejected.** *Posture in `grounds` by driver convention* — a driver could omit it, and the record
must not depend on a driver's honesty about its own posture. *Posture on the run rather than the
act* — a run's posture is derivable from its acts, and the act is what a claim is about. *Refusing
observed components at the registry* — an observed run is the adoption wedge (`08` §4); degraded is
not forbidden, it is on the record.

## D31 — one device contract, three roles, the fake first

`adapters/devices`: `Sensor.read() -> Reading`, `Actuator.command(argv) -> Ack`,
`Witness.overheard() -> list[Overheard]`; `DeviceComponents(devices)` registers each as a component
with D29's effects and the device's posture, and does the act the Phase 13 way — `exhausted` before,
`grounds` in the receipt, `idempotency_key` from the run. A reading carries the device's own stamp
**and its age by the runtime's clock**, because a late reading is the ordinary failure of a sensor
and the agent should see it as data. Fakes ship in `shadow_hdk.adapters.devices.testing` (D8),
and they are the first devices: a fake actuator can be told to disconnect mid-act, a fake sensor
to answer late.

**Rejected.** *A component port per protocol* — three copies of the act. *One component that is
both sensor and actuator* — its effects would be the union and no rule could permit reading without
permitting commanding.

## Not in this phase

Any protocol (16 and the `[~]` rows); credentials; discovery; safety interlocks. Which effects need a
warrant beyond a lease is still ADR-1's (Phase 13 `[~]`).

## Done when

- `tests/runtime/test_posture.py`: through a real run, an observed component's `Observed.posture`
  is `observed` and a controlled one's `controlled`; a component that lies in its own observation
  cannot change it; the contract round-trips it; the Event schema carries it
- `tests/adapters/basic/test_controlled.py`: refusal names the posture; an observed read is
  admitted; a controlled write is admitted; the inner policy still runs
- `tests/adapters/devices/`: the completion criteria of Epic 0007 that name a fake
- every package at 0.8.0; schemas republished; `test_versions` says why; a *Pins* row
- gate: ruff 0, format 0, mypy 0, pytest 0; every mutation bites or is named equivalent
