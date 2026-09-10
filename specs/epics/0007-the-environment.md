---
type: Epic
id: "0007"
slug: the-environment
status: planned
owner: Avinash
started: "2026-09-10"
phases: [phase-15-environment-contract, phase-16-mqtt]
policy_release: per-phase
policy_push: per-phase
policy_tdd: strict
---

# Epic 0007 — the-environment

## Objective

The harness reaches the physical world through devices as it reaches everything else — through
components it governs by their effects: a sensor reads the world, an actuator writes it
irreversibly, a witness reports what happened out there without us. Every act carries its control
posture on the record, and only `controlled` ever satisfies consent-before-effect (`08` §4). The
roadmap's row: *protocol adapters for devices — MQTT, OPC-UA, ROS 2 — sensors as `reads: {world}`,
actuators as irreversible writes; controlled vs observed posture.* `09` does not speak on it;
`10` §364–371 (the environment seam, read/write/run/call, controlled versus observed on every run
and every act) and `08` §4 (the posture table) do, and the decisions below are derived from those.

## Decisions

> Settled once; never re-asked. Per-phase specs are derived from this table. The reasoning and what
> was rejected are in each phase's overview (D29–D31 in Phase 15).

| # | Decision | Rationale |
|---|---|---|
| D29 | **The world is a scope, and a device is a component with a posture — not a port.** A sensor's effects are `reads: {world}`; an actuator's are `writes: {world}, reversible: false`; a witness reads the world's own log and reports acts as `Acted` receipts it did not command | D22 adds a port only for a gap, and there is none: a device is something the runtime invokes and governs by its effects, like every other component. One named scope, `world`, is what lets a rule narrow it |
| D30 | **Posture is on the record and in front of governance.** `Observed` carries the posture of the component that produced it (contract 0.8.0), stamped by the runtime from the registration; the executor puts `posture` and `component` before governance in `Context.attributes`; `basic.Controlled` refuses an observed component for any effect that writes or reaches | The record must not depend on a driver's honesty about its own posture; a policy that cannot see posture cannot enforce *only controlled satisfies consent-before-effect*; and observed is refused nowhere by default, because an observed run is the adoption wedge (`08` §4) |
| D31 | **One device contract, three roles, the fake first; protocols are adapters over it.** `Sensor.read`, `Actuator.command`, `Witness.overheard`; `DeviceComponents` turns a set of devices into a component port that reuses Phase 13's lease-at-the-act and receipt; fakes ship in the package (D8) | Three protocols would otherwise carry three copies of the act; a fake device is the only device this machine has, and the contract it exercises is the one every protocol adapter must meet |

## Phases

| phase | builds | proves here |
|---|---|---|
| 15 — the environment contract | D29, D30, D31: `Observed.posture` (0.8.0); the runtime stamps and exposes posture; `Controlled`; `adapters/devices` with the three roles, `DeviceComponents`, and fakes | everything, with fake devices: disconnect mid-act, a late reading, a witness's act as an observed receipt |
| 16 — MQTT | the first protocol adapter over D31 | with a localhost broker the tests start and stop, if the wheels can be added with a recorded reason; live tests skip naming what they need otherwise |
| `[~]` OPC-UA | the second, over D31 | needs `asyncua` (LGPL-3.0 — conditional under the licence allowlist) and a server; not on this machine |
| `[~]` ROS 2 | the third, over D31 | needs a ROS distribution, which is not a wheel; not on this machine |

## Completion criteria

> Checkable. "It works" is not a criterion.

- [ ] Through a real run, an observed component's observation carries `posture: observed` on the event stream and a controlled one's carries `controlled`, stamped by the runtime and not by the component
- [ ] `Controlled(AllowAll())` refuses an observed actuator with a reason naming the posture, admits an observed sensor, admits a controlled actuator
- [ ] A fake actuator commanded through a run leaves an `Acted` receipt with the lease read at the act; commanded on a spent lease it refuses and the fake world is untouched; disconnected mid-act it is `Failed` and no receipt exists
- [ ] A fake witness's overheard act arrives as an `Acted` with `posture: observed` and grounds that name the device, never as a proposal we made
- [ ] A reading carries the device's own stamp and its age by the runtime's clock, tested by moving the clock
- [ ] Contract 0.7.0 → 0.8.0 across every package, schemas republished, a *Pins* row on the board
- [ ] The MQTT adapter's tests run against a broker on localhost that the suite starts and stops, or skip naming what they need
- [ ] `tests/invariants` green: no adapter imports another; the kernel stays pure
- [ ] Gate: ruff 0, format 0, mypy 0, pytest 0; every mutation bites or is named equivalent

## Non-goals

Device discovery and provisioning; firmware; safety interlocks — a safety PLC is not the harness's
job, the harness refuses and does not brake; credentials for brokers and servers, which is R9's
credential story (`10` §454); the OPC-UA and ROS 2 adapters beyond their `[~]` rows.

## Amendments

> Operator changes made during the run land here, newest last.

_(none yet)_
