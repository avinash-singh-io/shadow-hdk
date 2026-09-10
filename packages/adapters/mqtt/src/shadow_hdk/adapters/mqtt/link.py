"""One link to a broker, and topics as the three roles (D32).

`MqttLink` owns one paho client on MQTT 3.1.1: it connects on first use or when asked, keeps the
subscriptions its devices need and applies them at connect, routes every message by topic — with
wildcards — to the sensor that keeps the latest, the witness that queues it, or the actuator
waiting on an ack. **A failed act breaks the link.** paho would re-send an in-flight QoS 1 message
on reconnect, which would let a step that already failed change the world later; so the next use
opens a fresh clean session, and a retry is a new act under the same key. A closed link stays
closed: nothing reopens it behind the caller's back.

Nothing here blocks an event loop. paho's network thread does the socket work; every wait the
runtime performs is handed to a worker thread with `asyncio.to_thread`.

Three actors, two locks (design.md §3.4). The event loop's callers share one `asyncio.Lock` across
the open path and `close()`, so two concurrent first uses — `FanOut` makes that the ordinary case —
open **one** session. paho's network thread and every registration share one `threading.Lock`
around the filter sets and their tables, and a fault in routing is counted rather than allowed to
end the thread, which paho would otherwise do while `is_connected()` stayed true.
"""

from __future__ import annotations

import asyncio
import json
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from pydantic import JsonValue

from shadow_hdk.kernel.ports import ClockPort
from shadow_hdk.runtime.devices import Ack, Overheard, Reading


@dataclass
class _Waiter:
    arrived: threading.Event = field(default_factory=threading.Event)
    ack: dict[str, Any] | None = None


class MqttLink:
    def __init__(
        self,
        host: str,
        port: int,
        *,
        clock: ClockPort,
        timeout: float = 5.0,
        grace: float = 0.5,
        client_id: str = "",
    ) -> None:
        """`timeout` bounds a PUBACK, an ack and a CONNACK; `grace` is how long a first read on a
        fresh subscription waits for a retained message — MQTT 3.1.1 sends them after the SUBACK
        with no end marker, so *nothing yet* can only be said after a short wait."""
        self._host, self._port, self._clock = host, port, clock
        self._timeout, self._grace, self._client_id = timeout, grace, client_id
        self._client: mqtt.Client | None = None
        self._closed = False
        self._lock = threading.Lock()
        self._opening = asyncio.Lock()
        self.opened = 0
        """How many sessions this link has opened — one, until a break or a close-and-reuse."""
        self.faults = 0
        """Routing faults on the network thread, counted instead of fatal."""
        self._sensor_filters: set[str] = set()
        self._witness_filters: set[str] = set()
        self._ack_filters: set[str] = set()
        self._latest: dict[str, tuple[Any, str]] = {}
        self._first: dict[str, threading.Event] = {}
        self._queues: dict[str, deque[tuple[str, Any, str]]] = {}
        self._counts: dict[str, int] = {}
        self._dropped: dict[str, int] = {}
        self._waiters: dict[tuple[str, str], _Waiter] = {}
        self._subscribed: dict[str, threading.Event] = {}
        self._suback_for: dict[int, str] = {}

    # ------------------------------------------------------------------ the three roles

    def sensor(self, id: str, topic: str) -> MqttSensor:
        """A sensor names **one** topic: the latest is kept per filter, and a wildcard could not
        say which device it read (ENH-001)."""
        _check_one_topic(topic, "a sensor")
        with self._lock:
            self._first.setdefault(topic, threading.Event())  # before the filter, never after
            self._sensor_filters.add(topic)
        self._subscribe_if_open(topic)
        return MqttSensor(self, id, topic)

    def actuator(self, id: str, topic: str, *, ack_topic: str | None = None) -> MqttActuator:
        _check_one_topic(topic, "a command topic")
        if ack_topic is not None:
            _check_filter(ack_topic)
            with self._lock:
                self._ack_filters.add(ack_topic)
            self._subscribe_if_open(ack_topic)
        return MqttActuator(self, id, topic, ack_topic)

    def witness(self, id: str, topic: str, *, keep: int = 1000) -> MqttWitness:
        """`keep` bounds the queue (TD-002): past it the oldest is dropped and counted, and the
        count rides on the next act handed over — a lost event is data."""
        _check_filter(topic)
        if keep < 1:
            raise ValueError("a witness keeps at least one event")
        with self._lock:
            self._queues.setdefault(topic, deque(maxlen=keep))  # before the filter, never after
            self._dropped.setdefault(topic, 0)
            self._witness_filters.add(topic)
        self._subscribe_if_open(topic)
        return MqttWitness(self, id, topic)

    # ------------------------------------------------------------------ lifecycle

    async def connect(self) -> None:
        """Open the link now — raising `ConnectionError` here rather than inside a step, for a
        deployment that wants to fail at startup."""
        await self._ensure()

    async def close(self) -> None:
        async with self._opening:
            self._closed = True
            await asyncio.to_thread(self._drop)

    async def __aenter__(self) -> MqttLink:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    @property
    def connected(self) -> bool:
        """Whether the link currently holds a live session — false once the broker has gone,
        as soon as the network thread notices."""
        client = self._client
        return client is not None and client.is_connected()

    def seen(self, topic: str) -> bool:
        """Whether a sensor topic has had a message yet."""
        with self._lock:
            return topic in self._latest

    def pending(self, topic: str) -> int:
        """How many events a witness topic holds, not yet reported."""
        with self._lock:
            return len(self._queues.get(topic, ()))

    def dropped(self, topic: str) -> int:
        """How many events a witness topic has lost to its bound since the last one reported."""
        with self._lock:
            return self._dropped.get(topic, 0)

    async def _ensure(self) -> mqtt.Client:
        if self._closed:
            raise ConnectionError(
                "the link was closed; it is not reopened behind the caller's back"
            )
        client = self._client
        if client is not None and client.is_connected():
            return client
        async with self._opening:
            # Whoever got here second finds the first caller's session (BUG-002).
            client = self._client
            if client is not None and client.is_connected():
                return client
            if self._closed:
                raise ConnectionError("the link was closed while a session was being opened")
            await asyncio.to_thread(self._drop)
            return await asyncio.to_thread(self._open)

    def _open(self) -> mqtt.Client:
        client = mqtt.Client(
            CallbackAPIVersion.VERSION2,
            client_id=self._client_id,
            protocol=mqtt.MQTTv311,
            reconnect_on_failure=False,
        )
        connected = threading.Event()
        outcome: dict[str, Any] = {}

        def on_connect(_c: mqtt.Client, _u: Any, _f: Any, reason_code: Any, _p: Any = None) -> None:
            outcome["rc"] = reason_code
            connected.set()

        gone = threading.Event()

        def on_disconnect(*_: Any) -> None:
            gone.set()

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = self._on_message
        client.on_subscribe = self._on_subscribe
        client.suppress_exceptions = True  # a callback fault must never end the network thread
        client.user_data_set(gone)
        client.connect(self._host, self._port, keepalive=30)  # a dead port raises here
        client.loop_start()
        if not connected.wait(self._timeout):
            client.loop_stop()
            raise TimeoutError(f"no CONNACK from {self._host}:{self._port} within {self._timeout}s")
        if outcome["rc"].is_failure:
            client.loop_stop()
            raise ConnectionError(f"the broker refused the connection: {outcome['rc']}")
        for topic in self._filters():
            self._subscribe(client, topic)
        self._client = client
        self.opened += 1
        # A device registered between the snapshot above and the assignment saw no live client
        # and left its subscription to us (BUG-003); nothing registered is left unsubscribed.
        while missing := [t for t in self._filters() if t not in self._subscriptions_made()]:
            for topic in missing:
                self._subscribe(client, topic)
        return client

    def _filters(self) -> set[str]:
        with self._lock:
            return self._sensor_filters | self._witness_filters | self._ack_filters

    def _subscriptions_made(self) -> set[str]:
        with self._lock:
            return set(self._subscribed)

    def _subscribe(self, client: mqtt.Client, topic: str) -> None:
        with self._lock:
            self._subscribed[topic] = threading.Event()
        _, mid = client.subscribe(topic, qos=1)
        with self._lock:
            self._suback_for[mid] = topic

    def _subscribe_if_open(self, topic: str) -> None:
        client = self._client
        if client is not None and client.is_connected():
            self._subscribe(client, topic)

    def _on_subscribe(self, _c: mqtt.Client, _u: Any, mid: int, *_: Any) -> None:
        with self._lock:
            topic = self._suback_for.pop(mid, None)
            event = self._subscribed.get(topic) if topic is not None else None
        if event is not None:
            event.set()

    async def subscribed(self, topic: str) -> bool:
        """Whether the broker has acknowledged a subscription — what a caller waits on before
        expecting a non-retained message to be seen."""
        with self._lock:
            event = self._subscribed.get(topic)
        if event is None:
            return False
        return await asyncio.to_thread(event.wait, self._timeout)

    def _drop(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            _hang_up(client)

    def _break(self) -> None:
        """A failed act: the session is abandoned so nothing in flight is ever re-sent."""
        self._drop()

    # ------------------------------------------------------------------ routing

    def _on_message(self, _c: mqtt.Client, _u: Any, message: mqtt.MQTTMessage) -> None:
        # On paho's thread. paho 2.1 re-raises what a callback raises, which returns from
        # `loop_forever` and ends the thread while `is_connected()` stays true — a link that looks
        # connected and hears nothing (BUG-003). A fault is counted; the thread lives.
        try:
            self._route(message)
        except Exception:  # noqa: BLE001 — counted, never fatal on the network thread
            with self._lock:
                self.faults += 1

    def _route(self, message: mqtt.MQTTMessage) -> None:
        body = _decode(message.payload)
        received_at = self._clock.now()
        with self._lock:
            for topic in self._sensor_filters:
                if mqtt.topic_matches_sub(topic, message.topic):
                    self._latest[topic] = (body, received_at)
                    self._first[topic].set()
            for topic in self._witness_filters:
                if mqtt.topic_matches_sub(topic, message.topic):
                    queue = self._queues[topic]
                    if queue.maxlen is not None and len(queue) == queue.maxlen:
                        self._dropped[topic] += 1
                    queue.append((message.topic, body, received_at))
            for topic in self._ack_filters:
                if mqtt.topic_matches_sub(topic, message.topic) and isinstance(body, dict):
                    key = body.get("key")
                    waiter = self._waiters.get((topic, key)) if isinstance(key, str) else None
                    if waiter is not None:
                        waiter.ack = body
                        waiter.arrived.set()

    def _expect(self, ack_topic: str, key: str) -> _Waiter:
        waiter = _Waiter()
        with self._lock:
            self._waiters[(ack_topic, key)] = waiter
        return waiter

    def _forget(self, ack_topic: str, key: str) -> None:
        with self._lock:
            self._waiters.pop((ack_topic, key), None)


class MqttSensor:
    """The last message seen on a topic. Nothing yet is an error naming the topic; a retained
    message is what makes a fresh subscriber's first read succeed. *Last seen* is literal: it
    survives a break and a reconnect, so a read after the broker returns is the pre-break message
    until a new one arrives — its `at` and `age_seconds` say how old that is."""

    def __init__(self, link: MqttLink, id: str, topic: str) -> None:
        self._link, self.id, self.topic = link, id, topic

    async def read(self) -> Reading:
        link = self._link
        await link._ensure()
        with link._lock:
            latest = link._latest.get(self.topic)
        if latest is None:
            # A fresh subscription is still receiving what the broker retained for it.
            await asyncio.to_thread(link._first[self.topic].wait, link._grace)
            with link._lock:
                latest = link._latest.get(self.topic)
        if latest is None:
            raise LookupError(f"nothing has been published on {self.topic} yet")
        body, received_at = latest
        if isinstance(body, dict):
            at = body.get("at")
            unit = body.get("unit")
            return Reading(
                value=body.get("value", body),
                unit=unit if isinstance(unit, str) else None,
                at=at if isinstance(at, str) else received_at,
                stamped_by="device" if isinstance(at, str) else "receiver",
            )
        return Reading(value=body, unit=None, at=received_at, stamped_by="receiver")


class MqttActuator:
    """A command published at QoS 1. The PUBACK is the broker's word that it took it, and with no
    ack topic the receipt says exactly that, with `topic#mid` as its foreign id — paho's `mid` is
    per session and 16-bit, so that id is neither stable across breaks nor unique for long; the
    key is the identity. With an ack topic, the receipt carries the device's own answer — the
    message whose `key` is the run's key."""

    def __init__(self, link: MqttLink, id: str, topic: str, ack_topic: str | None) -> None:
        self._link, self.id, self.topic, self.ack_topic = link, id, topic, ack_topic

    async def command(self, argv: JsonValue, *, key: str) -> Ack:
        link = self._link
        client = await link._ensure()
        waiter = link._expect(self.ack_topic, key) if self.ack_topic is not None else None
        try:
            info = client.publish(self.topic, json.dumps({"key": key, "argv": argv}), qos=1)
            await asyncio.to_thread(info.wait_for_publish, link._timeout)
            if not info.is_published():
                link._break()
                raise TimeoutError(
                    f"no PUBACK from the broker for {self.topic} within {link._timeout}s"
                )
            if waiter is None or self.ack_topic is None:
                return Ack(foreign_id=f"{self.topic}#{info.mid}", exit="published")
            if not await asyncio.to_thread(waiter.arrived.wait, link._timeout):
                raise TimeoutError(
                    f"no ack on {self.ack_topic} for key {key} within {link._timeout}s"
                )
            ack = waiter.ack or {}
            return Ack(
                foreign_id=str(ack.get("id", f"{self.topic}#{info.mid}")),
                exit=str(ack.get("exit", "acknowledged")),
            )
        finally:
            if self.ack_topic is not None:
                link._forget(self.ack_topic, key)


class MqttWitness:
    """Every message on a topic is an act the world reports; one is handed over per ask."""

    def __init__(self, link: MqttLink, id: str, topic: str) -> None:
        self._link, self.id, self.topic = link, id, topic

    async def overheard(self) -> Overheard | None:
        link = self._link
        await link._ensure()
        with link._lock:
            queue = link._queues[self.topic]
            if not queue:
                return None
            topic, body, received_at = queue.popleft()
            link._counts[self.topic] = number = link._counts.get(self.topic, 0) + 1
            dropped, link._dropped[self.topic] = link._dropped.get(self.topic, 0), 0
        if isinstance(body, dict):
            at, key = body.get("at"), body.get("key")
            return Overheard(
                foreign_id=str(body.get("id", f"{topic}#{number}")),
                what=body,
                at=at if isinstance(at, str) else received_at,
                exit=str(body.get("exit", "reported")),
                idempotency_key=key if isinstance(key, str) else None,
                dropped_before=dropped,
            )
        return Overheard(
            foreign_id=f"{topic}#{number}", what=body, at=received_at, dropped_before=dropped
        )


# ---------------------------------------------------------------------- the envelope, and topics


def _hang_up(client: mqtt.Client) -> None:
    """DISCONNECT, **delivered**, then the network thread joined. Stopping the thread first loses
    the packet still in paho's queue, and a broker then holds a session for a client that simply
    vanished — which is what made a local broker's shutdown hang."""
    gone = client.user_data_get()
    client.disconnect()
    if isinstance(gone, threading.Event):
        gone.wait(1.0)
    client.loop_stop()


def _decode(payload: bytes) -> Any:
    """A JSON object is the envelope; anything else is a reading of its text (D32)."""
    try:
        return json.loads(payload)
    except ValueError:
        return payload.decode("utf-8", "replace")


def _check_filter(topic: str) -> None:
    """What a broker would refuse at subscribe, refused at registration instead."""
    if not topic:
        raise ValueError("a topic filter cannot be empty")
    levels = topic.split("/")
    for index, level in enumerate(levels):
        if "#" in level and (level != "#" or index != len(levels) - 1):
            raise ValueError(f"{topic!r}: '#' may only be the last level, on its own")
        if "+" in level and level != "+":
            raise ValueError(f"{topic!r}: '+' may only be a whole level")


def _check_one_topic(topic: str, what: str) -> None:
    if not topic or "#" in topic or "+" in topic:
        raise ValueError(f"{topic!r}: {what} names one topic, with no wildcards")


__all__ = ["MqttActuator", "MqttLink", "MqttSensor", "MqttWitness"]
