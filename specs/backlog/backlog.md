---
type: Backlog
---

# Backlog

> **Last Updated**: 2026-09-10

---

## Priority Levels

| Level | Meaning |
|-------|---------|
| **P0** | Critical — blocks current phase |
| **P1** | High — address in current/next phase |
| **P2** | Medium — within 2 phases |
| **P3** | Low — nice to have |

**Status**: `open` | `in-progress` | `resolved` | `deferred` | `deprecated`

---

## Bugs

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| BUG-001 | A component named like an agent meta-tool is shadowed silently | P2 | open (found 2026-09-10) | 13 | A registration whose id matches a name in `Pattern.meta_tools` (`send`, `spawn`, `release`, `done`, …) never runs: the agent adapter builds the model-facing tools from the meta-tools by name (`adapters/agent/component.py:184`) and the meta-tool answers the call. Observed: a tool `send(to)` got *there is no helper ''; spawn one first*. Fix: refuse at the point the agent builds its tool list, naming both the registration and the meta-tool. |
| BUG-002 | `MqttLink`: concurrent first use opens N broker sessions; a witness sees each publish N times; `close()` leaks all but one | P1 | open (found 2026-09-10) | 16 | `_ensure` (`adapters/mqtt/link.py`) has no lock around drop-and-open: two callers both see no client and both open one; the last assignment wins and the rest stay connected, subscribed and routing into the same `_on_message`. Measured against the local broker: `gather(link.connect(), link.connect())` → 2 clients, one publish queued twice for a witness, one client still connected after `close()`. `FanOut` runs branches concurrently, so this is the ordinary case. Fix: an `asyncio.Lock` across `_ensure`'s open path and `close()`. See `specs/phases/phase-16-mqtt/design.md` F1. |
| BUG-003 | `MqttLink`: registration races paho's network thread; a raise inside `on_message` ends the thread while the link still reports connected | P1 | open (found 2026-09-10) | 16 | `sensor()/witness()/actuator()` mutate `_sensor_filters`/`_witness_filters`/`_ack_filters` (and `_first`/`_queues`) without `_lock`, while `_on_message` iterates them under the lock on paho's thread: `RuntimeError: Set changed size during iteration`, or a `KeyError` on `_first` (set after the filter is added), inside the callback. paho 2.1 re-raises callback exceptions by default (`suppress_exceptions=False`); `loop_forever` returns and the thread dies with `is_connected()` still true — deaf and mute. Same root: a device registered while `_open` is between its subscribe loop and `self._client = client` is never subscribed. Fix: mutate under `_lock`; set `_first`/`_queues` before adding the filter; in `_open` subscribe from a snapshot and re-check after assignment. Design F2. |

## Features

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| _(none)_ | | | | | |

## Tech Debt

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| TD-001 | Observations ride in graph state as our own classes | P2 | **closed 2026-09-10 (D19)** | 7 → 9 | LangGraph 1.2 warns on deserializing `shadow_hdk.kernel.observations.*` from a checkpoint and says a future version will block it. **Measured 2026-09-10:** `LANGGRAPH_STRICT_MSGPACK=true uv run pytest -q` is green over 353 tests, so nothing breaks today. Two remedies: a host builds its checkpointer's serializer with `allowed_msgpack_modules` naming our module — which pushes our internals into every host's setup — or `RunState.observations` holds plain JSON and the runtime loads it back, which keeps the state boundary honest. The second is the design answer; done in Phase 9 Group 0 as **D19** — a checkpoint *is* a wire, so the state holds JSON and the runtime loads at its edge. **Verified:** `LANGGRAPH_STRICT_MSGPACK=true uv run pytest -q -W default` now reports zero such lines across 406 tests. |
| TD-002 | `MqttLink`: the witness queue is unbounded | P2 | open (found 2026-09-10) | 16 | `_queues[filter]` is a `deque()` with no `maxlen`; a wildcard topic chattier than the agent's invocation rate grows memory for the life of the link. Proposed: a `maxlen` per witness and a dropped counter reported as data on the next `overheard` — a late reading is data, so is a lost event. Design F3. |

## Enhancements

| ID | Title | Priority | Status | Phase | Detail |
|----|-------|----------|--------|-------|--------|
| ENH-001 | A sensor over a wildcard filter cannot say which topic it read | P2 | open (found 2026-09-10) | 16 | `_latest` is keyed by the filter and `Reading` carries no topic, so `plant/+/temp` collapses N thermometers into one *latest* with no name. Either a sensor names one topic (as a command topic already must) or `Reading` grows a topic field — a contract change for every protocol. Design F4. |
| ENH-002 | TLS on `MqttLink` | P3 | open (found 2026-09-10) | `[~]` | The dev broker has no TLS listener, so it cannot be proven here; a `tls: ssl.SSLContext \| None` option on `_open` lands `[~]` naming a TLS broker as what settles it. Credentials stay R9's. Design F9. |
| ENH-003 | A protocol-adapter contract suite over the device contract | P2 | open (found 2026-09-10) | before OPC-UA / ROS 2 | The environment-varied claims in `tests/adapters/mqtt/test_environment.py` (not there, refuses, leaves and returns with nothing sent late) and the role claims in `test_mqtt.py` are what OPC-UA and ROS 2 must prove too. Parametrise them over a device factory plus an environment handle the way `tests/adapters/contract` does for ports, so each `[~]` row is a fixture rather than a rewrite. Design §7. |
