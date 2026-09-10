---
type: Tasks
phase: 16-mqtt
---

# Phase 16 — tasks

## Group 0 — the package, the dependency, the contract below the adapters
- [x] `packages/adapters/mqtt/` at 0.8.0; `paho-mqtt` 2.1.0 and dev `amqtt` 0.12.0 fetched, licences recorded
- [x] contract moved to `runtime/devices.py`; `adapters/devices` re-exports; 659 tests still green
- [x] `Reading.stamped_by` — device or receiver, and `DeviceComponents` says which
- [x] Gate

## Group 1 — the link and the three roles
- [x] `MqttLink` (lazy or explicit connect, subscriptions applied at connect and acknowledged, routing with wildcards, a failed act breaks the link, a closed link stays closed, the DISCONNECT delivered before the thread is joined); `MqttSensor` (grace for a retained message), `MqttActuator` (QoS 1, `published` or the device's own ack by key), `MqttWitness`
- [x] broker fixture (`amqtt` on a free localhost port, stop/start, anonymous or not) and the device side (a second paho client; every wait awaited)
- [x] RED: retained reading with the device's stamp and age; no stamp is the receiver's; nothing yet; non-JSON text; command without ack is `published` at QoS 1; command with ack carries the device's id and exit; an ack for another key is not ours; no ack is `Failed` with no receipt; events one per ask as observed receipts with and without keys on a wildcard topic; a non-JSON event; a sensor registered after connect; a closed link; refused topics — 18 tests
- [x] Gate — 24 mutations, 23 bite; *the DISCONNECT is not delivered* survives and is named below

## Group 2 — the environment varied, and the epic closed
- [x] RED: broker not there (act `Failed` naming the refusal, `connect()` raises); broker refuses us; broker gone after a successful act (`Failed`, nothing sent when it is back, the next act's key is the only one seen); retained versus none is Group 1's first and third tests — 3 tests
- [x] Epic 0007: OPC-UA and ROS 2 `[~]` naming what settles them; criteria ticked where met; records, board, status, roadmap; roadmap re-checked — every numbered phase and every buildable row of the environment epic is built
- [x] Gate — ruff 0 / format 0 / mypy 0 (112 files) / pytest 680 passed, 9 deselected; 4 mutations bite
