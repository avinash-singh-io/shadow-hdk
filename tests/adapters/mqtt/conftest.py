"""A broker on localhost the suite starts and stops, and a *device side* to talk to it.

The broker is `amqtt`, asyncio, on the test's own loop — so nothing here may block that loop; every
wait is `await`ed. The device side is a second paho client on its own thread: it publishes
readings and events and answers commands, the way a device on the other side of the broker would.
"""

from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
import warnings
from collections.abc import AsyncIterator, Callable
from typing import Any

import paho.mqtt.client as mqtt
import pytest
from amqtt.broker import Broker
from paho.mqtt.enums import CallbackAPIVersion


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
    return port


class LocalBroker:
    """The broker, with `stop()` and `start()` so a test can take it away and bring it back."""

    def __init__(self, port: int, *, anonymous: bool = True) -> None:
        self.port = port
        self.anonymous = anonymous
        self._broker: Broker | None = None

    async def start(self) -> None:
        self._broker = Broker(
            {
                "listeners": {"default": {"type": "tcp", "bind": f"127.0.0.1:{self.port}"}},
                "sys_interval": 0,
                "auth": {"allow-anonymous": self.anonymous},
                "topic-check": {"enabled": False},
            }
        )
        await asyncio.wait_for(self._broker.start(), 10)

    async def stop(self) -> None:
        """Capped, with the reason: `amqtt` 0.12's shutdown stalls when a client sends a clean
        DISCONNECT while a QoS 1 delivery to it — a retained message, typically — is still in
        flight; its broadcast loop waits on a PUBACK that will never come. A client that simply
        vanishes is handled fine. That is the dev broker's quirk, not the adapter's, so a stalled
        shutdown is cut short here rather than failing a test that already passed."""
        if self._broker is not None:
            try:
                await asyncio.wait_for(self._broker.shutdown(), 3)
            except TimeoutError:
                warnings.warn(
                    "amqtt shutdown stalled on an in-flight QoS 1 delivery; cut short", stacklevel=2
                )
            self._broker = None


@pytest.fixture
async def broker() -> AsyncIterator[LocalBroker]:
    local = LocalBroker(free_port())
    await local.start()
    try:
        yield local
    finally:
        await local.stop()


class DeviceSide:
    """What is on the other side of the broker: publishes, listens, answers.

    Every wait is awaited and every blocking paho call goes to a worker thread, because the broker
    runs on this very loop — a `time.sleep` here would stop the broker from answering.
    """

    def __init__(self, port: int) -> None:
        self._port = port
        self._client = mqtt.Client(CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311)
        self._lock = threading.Lock()
        self.received: dict[str, list[Any]] = {}
        self.qos_seen: dict[str, list[int]] = {}
        self._answers: dict[str, tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]] = {}
        self._client.on_message = self._on_message
        self._gone = threading.Event()
        self._client.on_disconnect = lambda *_: self._gone.set()

    async def connect(self) -> None:
        await asyncio.to_thread(self._client.connect, "127.0.0.1", self._port)
        self._client.loop_start()
        assert await until(self._client.is_connected), "the device side never reached the broker"

    def _on_message(self, _c: mqtt.Client, _u: Any, message: mqtt.MQTTMessage) -> None:
        try:
            body: Any = json.loads(message.payload)
        except ValueError:
            body = message.payload.decode("utf-8", "replace")
        with self._lock:
            self.received.setdefault(message.topic, []).append(body)
            self.qos_seen.setdefault(message.topic, []).append(message.qos)
            answer = self._answers.get(message.topic)
        if answer is not None and isinstance(body, dict):
            ack_topic, reply = answer
            self._client.publish(ack_topic, json.dumps(reply(body)), qos=1)

    async def publish(self, topic: str, body: Any, *, retain: bool = False) -> None:
        payload = body if isinstance(body, str) else json.dumps(body)
        info = self._client.publish(topic, payload, qos=1, retain=retain)
        await asyncio.to_thread(info.wait_for_publish, 5)
        assert info.is_published(), f"the device side could not publish on {topic}"

    async def listen(self, topic: str) -> None:
        self._client.subscribe(topic, qos=1)
        await asyncio.sleep(0.05)

    async def answers(
        self, command_topic: str, ack_topic: str, reply: Callable[[dict[str, Any]], dict[str, Any]]
    ) -> None:
        with self._lock:
            self._answers[command_topic] = (ack_topic, reply)
        await self.listen(command_topic)

    async def close(self) -> None:
        self._client.disconnect()
        await asyncio.to_thread(self._gone.wait, 1.0)  # the DISCONNECT delivered, not just queued
        await asyncio.to_thread(self._client.loop_stop)


@pytest.fixture
async def device_side(broker: LocalBroker) -> AsyncIterator[DeviceSide]:
    side = DeviceSide(broker.port)
    await side.connect()
    try:
        yield side
    finally:
        await side.close()


async def until(condition: Callable[[], bool], *, timeout: float = 3.0) -> bool:
    """Wait for `condition` without blocking the loop the broker lives on."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition():
            return True
        await asyncio.sleep(0.01)
    return condition()
