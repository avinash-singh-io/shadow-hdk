---
type: Plan
phase: 16-mqtt
---

# Phase 16 — plan

```
# Sequential: Group 0 → 1 → 2. Group 0 is the package and the moved contract; 1 the link and the
# three roles; 2 the environment varied, and the epic closed.
```

## Group 0 — the package, the dependency, the contract below the adapters

- `packages/adapters/mqtt/` at 0.8.0 on kernel + runtime + `paho-mqtt`; `amqtt` in dev
- `runtime/devices.py` holds the contract; `adapters/devices` re-exports it
- `Reading.stamped_by` (device | receiver)

**Commit:** `chore(adapters): the mqtt package exists; the device contract moves into the runtime`

## Group 1 — the link and the three roles

- `MqttLink(host, port, *, clock, timeout)`: one paho 3.1.1 client, lazy connect on first use,
  explicit `connect()`/`close()`, subscriptions kept and applied at connect, routing by topic with
  wildcards, a failed act breaks the link
- `MqttSensor(link, id, topic)`, `MqttActuator(link, id, topic, ack_topic=None)`,
  `MqttWitness(link, id, topic)` — D32's envelope
- `tests/adapters/mqtt/conftest.py`: a broker per test on a free localhost port; a *device side*
  helper — a second paho client that publishes readings and events and answers commands
- RED: reading with the device's stamp and its age; reading with no stamp is the receiver's; no
  message yet; non-JSON payload; command without ack (`published`); command with ack (the
  device's id and exit); no ack within the timeout; witness events with and without keys, on a
  wildcard topic; close then use

**Commit:** `feat(adapters): MQTT topics as sensors, actuators and witnesses`

## Group 2 — the environment varied, and the epic closed

- RED: broker not there (act `Failed`, `connect()` raises); broker dropped after connect (act
  `Failed`, and once the broker is back nothing is re-sent); retained versus none
- Epic 0007: OPC-UA and ROS 2 rows `[~]` naming what settles them; completion criteria ticked
  where met; records, board, status, roadmap; re-check the roadmap for anything left buildable

**Commit:** `test(adapters): the broker that is not there, and the one that leaves`
