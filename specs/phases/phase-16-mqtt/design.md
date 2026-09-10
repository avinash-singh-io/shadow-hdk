---
type: Design
phase: 16-mqtt
status: review of the adapter as built at cd24bdc, plus the in-flight Group 2 (2026-09-10)
topics: [mqtt, d32, link, envelope, concurrency, backpressure, wildcards, tls]
---

# Phase 16 — the MQTT adapter: system design, and what a review of it finds

> **2026-09-10, after the review:** F1–F4 landed as Group 3 (`c0224e4`, tests in
> `tests/adapters/mqtt/test_review_findings.py`); F6 and F8 are in the docstrings; F5 and F7 stand
> as notes; F9 is `[~]`. Received unchanged in `2c1fd6f`.

> The adapter drawn from the code as built (`cd24bdc`; 18 tests green in this session, and Group
> 2's three environment tests green in the working tree), with the consequences of D29–D32 made
> explicit, the trade-offs named, and the findings ranked — two of them reproduced against the local
> broker rather than read from the code. The decisions themselves are not re-asked here.

## 0. The five diagrams

Prose says one thing at a time; so does a diagram. [`diagrams/`](diagrams/README.md) holds five,
each answering one question this document also answers in words: the architecture (who talks to
whom), the act as a sequence (what happens in order), the link's lifecycle (which states reopen),
the envelope as a dataflow (where each payload lands), and the act's outcomes as a workflow (every
observation a step can produce).

## 1. Requirements

### Functional

| # | Requirement | Met by |
|---|---|---|
| F1 | A subscribed topic is a `Sensor`: `read()` is the last message seen, with the device's stamp or the receiver's | `MqttSensor.read` |
| F2 | A command topic is an `Actuator`: `command(argv, key)` publishes `{"key", "argv"}` at QoS 1 and returns an `Ack` — the broker's (`published`) or the device's (from `ack_topic`, matched by `key`) | `MqttActuator.command` |
| F3 | An event topic — wildcards allowed — is a `Witness`: `overheard()` hands over one queued event per call | `MqttWitness.overheard` |
| F4 | The envelope is D32's: a JSON object in the payload; anything else is a reading of its text | `_decode`, the three roles |
| F5 | `DeviceComponents` over these does the act the Phase 13 way with the posture Phase 15 stamps — nothing MQTT-specific in the act | `adapters/devices/components.py`, unchanged |
| F6 | A failed act is never re-sent by the adapter; a retry is a new act under the same key | `MqttLink._break` |
| F7 | The broker's absence is `ConnectionError` → `Failed`; `connect()` raises for a deployment that wants to fail at startup | `_ensure`, `_open` |
| F8 | A closed link stays closed | `_closed` |

### Non-functional

| # | Requirement | Source |
|---|---|---|
| N1 | Nothing blocks an asyncio loop — every blocking wait goes to a worker thread | overview: the ten-minute hang |
| N2 | No adapter imports another; the contract lives in `runtime/devices.py` | `tests/invariants`, project rules |
| N3 | Proven against a broker the suite starts and stops on localhost; never a real broker or device | epic 0007 |
| N4 | Every wait is bounded: CONNACK, PUBACK, ack, first-read grace | `timeout`, `grace` |
| N5 | Gate: ruff 0, format 0, mypy strict 0, pytest 0; every mutation bites | project rules |

### Constraints

- **MQTT 3.1.1 only**, because the only broker this suite can run (`amqtt` 0.12) refuses v5, so v5
  properties are not available as a carrier (D32).
- **paho-mqtt 2.1 is threaded**: it owns a network thread and delivers callbacks on it. The adapter
  is therefore a three-actor system (§3.4), not a pure-asyncio one.
- **Out of scope by the epic**: credentials (R9), discovery, provisioning, safety interlocks. TLS is
  not named either way — finding F9.
- A team of one; the suite must stay fast (18 broker-per-test cases run in about two seconds).

## 2. High-level design

### Components

```
  run() ─ executor ─ governance (posture, effects) ─ DeviceComponents          adapters/devices
                                                        │  Sensor.read · Actuator.command · Witness.overheard
                                                        │  runtime/devices.py — the contract, no I/O
            ┌───────────────────────────────────────────┴───────────────────────────────────────┐
            │  adapters/mqtt                                                                    │
            │    MqttSensor ──┐                                                                 │
            │    MqttActuator ┼── MqttLink ──── one paho Client (3.1.1 · clean session · QoS 1)  │
            │    MqttWitness ─┘      filters · latest · queues · waiters · one lock              │
            └────────────────────────┼──────────────────────────────────────────────────────────┘
                                     │ TCP
                                  broker   (amqtt in the suite; any 3.1.1 broker in a deployment)
                                     │
                            the device side: publishes readings and events, answers commands
```

Layering is the project's: kernel ← runtime ← adapters. The MQTT package imports `kernel.ports`
(the clock) and `runtime.devices` (the contract) and nothing from `adapters/devices`, so the
no-adapter-imports-another invariant holds without a special case.

### Data flow, per role

```
 sensor    device ─PUBLISH(topic, envelope, retain?)─▶ broker ─▶ paho thread ─▶ _on_message ─▶ _latest[filter]
           read(): _ensure → (grace wait on a first read) → _latest → Reading(value, unit, at, stamped_by)

 actuator  command(): _ensure → [expect waiter (ack_topic, key)] → PUBLISH qos1 {"key", "argv"}
             ─▶ wait PUBACK (timeout) ─▶ no ack_topic: Ack("topic#mid", "published")
                                       ─▶ ack_topic:   wait for the waiter (timeout) → Ack(id, exit)
             no PUBACK → _break() → TimeoutError → Failed, no receipt
             no ack    →            TimeoutError → Failed, no receipt; the link is kept — the command was taken

 witness   device ─PUBLISH(event)─▶ broker ─▶ paho thread ─▶ _on_message ─▶ _queues[filter].append
           overheard(): _ensure → popleft or None → Overheard(id, what, at, exit, key)
```

### Contracts

The wire contract is the envelope (§3.1). The Python contract is the three protocols and three
dataclasses in `runtime/devices.py`, which the MQTT classes satisfy structurally. Nothing new crosses
a port: a `Reading` becomes a `Completed` dict, an `Ack` an `Acted`, an `Overheard` an observed
`Acted` — JSON at the boundary, as every contract here must be.

### Storage

None. The link's state is in-memory and per process: the last message per sensor filter, a deque per
witness filter, an ack waiter per `(ack_topic, key)`. A restart forgets everything; a retained message
on the broker is what lets a fresh subscriber's first read succeed. The record of what happened is
the run's event stream through the sink and observer, never the adapter.

## 3. Deep dive

### 3.1 The envelope (D32)

| message | direction | fields | when absent |
|---|---|---|---|
| command | adapter → device | `key` (the run's idempotency key), `argv` | always sent |
| reading | device → adapter | `value`, `unit`, `at` | no `at` → receive time, `stamped_by: receiver`; no `value` → the whole object is the value; not a JSON object → its text is the value |
| ack | device → adapter | `key`, `id`, `exit` | no `id` → `topic#mid`; no `exit` → `acknowledged`; a `key` that is not ours → ignored |
| event | device → adapter | `id`, `what`, `at`, `exit`, `key` | no `id` → `topic#n`; no `at` → receive time; no `exit` → `reported`; no `key` → the runtime keys it `witness/id` |

Two clocks are visible on every reading: the device's (`at`, when `stamped_by: device`) and the
runtime's (`age_seconds`, computed in `DeviceComponents`). A receiver-stamped reading is honest that
its time is an arrival time.

### 3.2 The link as a state machine

```
  unopened ──_ensure()──▶ open ──act fails before PUBACK──▶ broken ──next _ensure()──▶ open (a fresh clean session)
     │                     │                                  ▲
     │                     └── broker gone, noticed by the network thread ──┘
     └──close()──▶ closed ◀──close()── from any state         closed is terminal: _ensure raises ConnectionError
```

*Broken* reopens and *closed* does not, on purpose: reopening is what makes a retry possible — a new
act under the same key — while a close is the caller's decision and must not be undone behind their
back. *Broken* exists at all because paho keeps an unacked QoS 1 message in `_out_messages` and, on
reconnect, `_messages_reconnect_reset_out` marks it `dup` and sends it again (paho 2.1
`client.py:3712`); a publish attempted while disconnected is likewise queued "to be sent after a
connection is made" (`client.py:1806`). A step that already returned `Failed` would then change the
world later. Dropping the client — DISCONNECT delivered, network thread joined — is the only way to be
sure the queue dies with it.

### 3.3 The act, in sequence

```
 runtime          MqttActuator             MqttLink / paho               broker              device
   │ invoke           │                         │                           │                   │
   │─────────────────▶│ _ensure()               │                           │                   │
   │                  │────────────────────────▶│ CONNECT · SUBSCRIBE(ack)  │                   │
   │                  │ _expect(ack_topic, key) │◀──── CONNACK · SUBACK ────│                   │
   │                  │────────────────────────▶│ PUBLISH qos1 {key, argv}  │                   │
   │                  │                         │──────────────────────────▶│──── deliver ─────▶│
   │                  │  wait_for_publish       │◀──────── PUBACK ──────────│                   │
   │                  │  (to_thread, timeout)   │                           │◀── PUBLISH ack ───│
   │                  │  waiter.arrived.wait    │◀───── deliver (key) ──────│                   │
   │◀─ Ack(id, exit) ─│  (to_thread, timeout)   │                           │                   │
   │ Acted: receipt, lease read at the act, posture controlled              │                   │
```

The SUBSCRIBE for the ack topic precedes the PUBLISH on the same TCP session and the broker handles
packets in order, so the subscription exists before the device's answer can be delivered — no SUBACK
wait is needed for correctness.

### 3.4 The concurrency model — three actors, one lock

| actor | runs | touches |
|---|---|---|
| the asyncio loop (the runtime) | `read` / `command` / `overheard`, `_ensure`, registration | reads `_latest` and `_queues` under `_lock`; **mutates the filter sets and the `_first` / `_queues` dicts without it** |
| worker threads (`asyncio.to_thread`) | `_open`, `_drop`, `wait_for_publish`, `Event.wait` | the paho client; one worker per blocking wait, held up to `timeout` or `grace` |
| paho's network thread | `_on_message`, `on_connect`, `on_disconnect` | iterates the filter sets and writes `_latest` / `_queues` / `_waiters` under `_lock`; calls `clock.now()` |

The intended invariant is that every read or write of routing state happens under `_lock`, and that
one client exists per link. Two places break it today — F1 and F2.

### 3.5 Error handling — what each failure becomes

| failure | raised | observation | link after | what the world saw |
|---|---|---|---|---|
| broker not there, or refuses us | `ConnectionError` from `_open` | `Failed` | unopened | nothing |
| no CONNACK within `timeout` | `TimeoutError` | `Failed` | unopened | nothing |
| no PUBACK within `timeout` | `TimeoutError` | `Failed`, no receipt | **broken** — the queue destroyed | perhaps the command; the key on the wire is for exactly this |
| PUBACK, then no ack within `timeout` | `TimeoutError` | `Failed`, no receipt | open | the command, certainly |
| an ack for another key | ignored, then the timeout | `Failed` | open | the command |
| nothing on a sensor topic after `grace` | `LookupError` naming the topic | `Failed` | open | — |
| the link was closed | `ConnectionError` | `Failed` | closed | nothing |
| the lease is spent | — | `Refused`, before the adapter runs | unchanged | nothing |

No exception crosses `run()`: each of these is caught by the executor into `Failed`, as the project
requires. Retry is the runtime's and the agent's decision, never the adapter's.

## 4. Scale and reliability

- **Load.** One link is one TCP session, one network thread, and a routing pass of O(sensor +
  witness + ack filters) per inbound message, each a `topic_matches_sub`. Hundreds of topics per link
  is fine.
- **Blocking waits and the executor.** Every wait holds one default-executor worker (a pool of about
  min(32, cpu + 4)). A `FanOut` across many actuators against a slow broker occupies a worker per
  branch for up to `timeout`; the loop is never blocked, but throughput is bounded by the pool. An
  explicit executor is the fix if a deployment ever fans out that wide.
- **Silent partitions.** The keepalive is 30 s, so a broker that vanishes without a FIN is noticed by
  the network thread after about 45 s. Until then `connected` is true and a sensor `read` returns the
  last message. A device-stamped reading's `age_seconds` still tells the truth; a receiver-stamped
  one cannot distinguish a quiet device from a dead link.
- **Backpressure.** None on the witness path: a chatty wildcard topic queues without bound between
  invocations (F3).
- **Failover.** None inside the adapter, by design: no reconnect behind the caller's back and no
  resend. Availability is the deployment's (a broker cluster) and the agent's (a new act). Given
  the rule on failed acts, this is the right place for it.
- **Observability.** The link emits nothing itself; the run's observer and tracer (Phase 14) see the
  act's receipt or its failure. The only probes are `connected`, `seen(topic)`, `pending(topic)` —
  enough for the suite, thin for operations: nothing counts messages routed, dropped, acks
  unmatched, or links broken.

## 5. The trade-offs, explicit

| decision | chosen | alternative | why — and what would overturn it |
|---|---|---|---|
| carrier for key, stamp, exit | a JSON envelope in the payload | MQTT v5 properties | only a 3.1.1 broker can be proven here, and a hybrid is two contracts. Overturned by a v5 broker in a deployment → an adapter option (D32) |
| a failed act before PUBACK | break the link; the next use is a fresh clean session | let paho resend on reconnect | a resend lets a `Failed` step change the world later. The cost is one reconnect per failure |
| topology | one link per broker, shared by many devices | a client per device | one session, subscriptions applied once, shared routing. The cost is that shared state needs lock discipline — F1, F2 |
| a sensor read | the last message seen, with a grace wait on the first read | request/response per read | MQTT is push; a read is a look at what arrived. Staleness is data (`age_seconds`), not a failure |
| QoS | 1 for everything | 0, or 2 | 1 gives the PUBACK as the broker's word; exactly-once is already the key's job on the device side |
| async model | paho's thread plus `to_thread` | an asyncio-native client | paho is the deployed, licence-clean choice; the cost is three actors and a lock |
| retained messages on a first read | `grace` (0.5 s) | no wait | 3.1.1 sends retained messages after the SUBACK with no end marker; without a wait *nothing yet* is wrong half the time |
| wildcards | sensors and witnesses may use `+` and `#`; a command topic may not | sensors single-topic only | a wildcard sensor collapses N topics into one *latest* with no way to say which — F4 |

## 6. Findings — the review of the code as built

Ranked. F1 and F2 were reproduced against the local broker in this session; the rest are read from
the code. Backlog ids are filed for each that needs work.

**F1 — BUG-002 (P1; fix before this phase's gate).** Two concurrent first uses of one link open two
broker sessions. `_ensure` has no lock around its drop-and-open: two callers both see no client and
both `to_thread(_open)`; the last assignment to `_client` wins and the other client stays connected,
subscribed, and routing into the same `_on_message`. Measured: `gather(link.connect(),
link.connect())` opened two clients; a single publish was queued **twice** for a witness; after
`close()` one client was still connected with its thread alive. `FanOut` compiles to parallel
branches, so concurrent invocations on one link are the ordinary case. Fix: an `asyncio.Lock` held
across `_ensure`'s open path and across `close()`, so the second caller finds the first's client.

**F2 — BUG-003 (P1; fix before the gate).** Registration races the network thread. `sensor()`,
`witness()` and `actuator()` mutate `_sensor_filters` / `_witness_filters` / `_ack_filters` — and
`_first`, `_queues` — without `_lock`, while `_on_message` iterates the sets under the lock on paho's
thread. A message arriving during a registration is `RuntimeError: Set changed size during
iteration` (or a `KeyError` on `_first`, which is set *after* the filter is added) inside the
callback; paho 2.1 re-raises callback exceptions by default (`suppress_exceptions = False`), which
returns from `loop_forever` and ends the thread while `is_connected()` stays true — the link looks
connected and is deaf and mute. Same root: a device registered while `_open` is between its subscribe
loop and `self._client = client` is never subscribed. Fix: mutate under `_lock`; set `_first` /
`_queues` before adding the filter; in `_open`, subscribe from a snapshot and re-check after the
assignment.

**F3 — TD-002 (P2).** The witness queue is unbounded: `deque()` with no `maxlen`. A wildcard topic
chattier than the agent's invocation rate grows memory for the life of the link. Proposed: a
`maxlen` per witness with a dropped counter reported as data on the next `overheard` — a late reading
is data; so is a lost event.

**F4 — ENH-001 (P2).** A sensor over a wildcard filter cannot say which concrete topic it read:
`_latest` is keyed by the filter and `Reading` carries no topic. Either a sensor names one topic, as a
command topic already must — the cheap, honest answer — or `Reading` grows a field, which is a
contract change for every protocol.

**F5 — note.** Staleness across a silent partition is invisible for up to about 45 s, and forever for
a receiver-stamped reading from a device that stopped talking. Expose `keepalive` as an option; leave
any *too old* refusal to policy or the agent, which is where `age_seconds` already goes.

**F6 — note.** `_latest` survives a break and a reconnect: a read after the broker returns yields the
pre-break message until a new one arrives. That is *last message seen* taken literally and is
defensible; the docstring should say it.

**F7 — note.** `clock.now()` is called on paho's thread. `ClockPortContract` promises a monotone
`now()` and unique ids, not thread safety. True of the shipped clocks; worth a line in the contract,
or a stamp taken on the thread and converted on the loop.

**F8 — note.** The no-ack `foreign_id` is `topic#mid`; paho's `mid` is per session and 16-bit, so it
is neither stable across breaks nor unique for long. Harmless on the record — the key is the stable
identity — but it must not be read as one.

**F9 — ENH-002 (P3).** No TLS and no username/password on the link. Credentials are R9's by the
epic; transport security is not named. A `tls: ssl.SSLContext | None` option on `_open` is small,
but the dev broker has no TLS listener to prove it against, so it lands `[~]`.

## 7. What to revisit as it grows

1. **A protocol-adapter contract suite (ENH-003).** The environment-varied claims in
   `test_environment.py` — not there, refuses, leaves and returns with nothing sent late — and the
   role claims in `test_mqtt.py` are exactly what OPC-UA and ROS 2 must prove too. Parametrise them
   over a device factory plus an environment handle (start / stop), the way `tests/adapters/contract`
   does for ports, so each `[~]` row is a fixture rather than a rewrite. The MQTT tests are the draft.
2. **v5 properties as an option**, when a v5 broker exists to prove it against — D32's own escape
   hatch.
3. **Links described in data.** Today a link is built and handed to each device; a registry keyed by
   `(host, port)` would let a deployment describe its devices in a file, as patterns and rules are,
   without wiring links by hand.
4. **QoS 2** where a device asks for it; the key already gives idempotence, so this is a device's
   preference, not a correctness need.
5. **Operational counters** on the link — routed, dropped, acks unmatched, breaks — surfaced through
   the observer when Phase 14's tracer wants them.
6. **An explicit executor** for the blocking waits, if a deployment fans out wider than the default
   pool.

## Assumptions

- The deployment broker speaks 3.1.1 and accepts anonymous or R9-supplied credentials; nothing here
  needs v5.
- A device de-duplicates by `key` when it matters. The adapter guarantees the key is on the wire, not
  that the device honours it.
- One `MqttLink` per process per broker; nothing shares a link across processes.
- `Composition` steps run one at a time and `FanOut` steps run concurrently; the adapter must be safe
  under both.
