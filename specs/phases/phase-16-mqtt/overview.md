---
type: Phase
phase: 16
name: mqtt
epic: 0007-the-environment
status: not-started
topics: [environment, mqtt, devices, broker, d32]
deps: [phase-15-environment-contract]
---

# Phase 16 — MQTT

## Goal

The first protocol adapter over the device contract: a subscribed topic is a `Sensor`, a command
topic is an `Actuator`, an event topic is a `Witness`, and `DeviceComponents` over them does the
act the Phase 13 way with the posture Phase 15 stamps. Proven against a broker on localhost that
the suite starts and stops — never a real broker, never a real device.

## What was measured before anything was decided

- No MQTT client or broker was resolvable here and `mosquitto` is not installed. `paho-mqtt`
  2.1.0 (EPL-2.0 OR BSD-3-Clause) is the adapter's dependency and `amqtt` 0.12.0 (MIT; its
  dependencies MIT and BSD-3) is a **dev** dependency for the suite's broker. Both are wheels,
  fetched with the reason recorded; `amqtt` pins `websockets==15.0.1`, which moved the dev
  resolution down from 16.1.1.
- The dev broker speaks **MQTT 3.1.1 only**: a v5 connect is refused with *unsupported protocol
  version*. QoS 1 round-trips, a retained message reaches a late subscriber, a dead port raises
  `ConnectionRefusedError`.
- A spike that polled with `time.sleep` on the loop the broker lived on hung for ten minutes and
  had to be killed: the broker is asyncio, and nothing in the suite may block its loop.

## D32 — the envelope is the payload; the transport's version is not the contract's business

The run's idempotency key, the device's own stamp, and the device's word for how a command ended
travel in a JSON object in the payload: a command is `{"key", "argv"}`; a reading may carry
`value`, `unit`, `at`; an ack `key`, `id`, `exit`; an event `id`, `what`, `at`, `exit`, `key`. A
payload that is not a JSON object is a reading whose value is its text. A reading with no `at` is
stamped with the **receive time by the adapter's clock** and says so (`stamped_by: receiver`), so
an agent can tell a device's measurement time from our arrival time.

**Rejected.** *MQTT v5 properties* (correlation data, user properties, response topic) — the
obvious and cleaner carrier, and the only broker this suite can run refuses v5; a contract proven
against nothing is a sentence. *A hybrid that uses v5 when the broker allows it* — two carriers is
two contracts, and a device would have to know which broker it is behind. **Overturned by** a
deployment on a v5 broker wanting properties: an adapter option, added when a broker exists to
prove it against.

## The act over MQTT, and what it cannot promise

- A command is published at QoS 1; the **PUBACK is the broker's word that it took it**, and with no
  ack topic the receipt says exactly that: `exit: published`. With an `ack_topic`, the adapter
  waits for a message whose `key` is the run's key and the receipt carries the device's `id` and
  `exit`. No PUBACK, or no ack within the timeout, is `TimeoutError` → `Failed` and no receipt —
  and the command may have gone out, which is what the key on the wire is for.
- **A command whose PUBACK never came is never re-sent by the adapter.** paho would re-send an
  in-flight QoS 1 message on reconnect, which would let a step that already failed change the
  world later; so a failed act breaks the link, and the next use opens a fresh clean session. A
  retry is a new act under the same key.
- The broker not being there is `ConnectionError` from the act → `Failed`, nothing published;
  `connect()` raises it at startup for a deployment that wants to fail fast.
- A sensor's `read` is the **last message seen** on its topic; nothing yet is `Failed` naming the
  topic, and a retained message is what makes a fresh subscriber's first read succeed.

## Done when

- `tests/adapters/mqtt/`: every claim above through a real run with `DeviceComponents` over the
  MQTT devices against the localhost broker; the environment varied — broker not there, broker
  dropped after connect (and no delayed resend once it is back), late reading, retained versus
  none, ack versus none, non-JSON payload, wildcard event topic
- gate: ruff 0, format 0, mypy 0, pytest 0; every mutation bites or is named equivalent; no
  adapter imports another
