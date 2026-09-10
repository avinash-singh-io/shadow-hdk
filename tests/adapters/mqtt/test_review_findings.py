"""The review's findings, reproduced first (design.md §6): BUG-002, BUG-003, TD-002, ENH-001.

`FanOut` runs branches concurrently, so two first uses of one link at once is the ordinary case, not
a corner; and the network thread is a second actor that registration must not race.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

import pytest

from shadow_hdk.adapters.devices import DeviceComponents
from shadow_hdk.adapters.mqtt import MqttLink
from shadow_hdk.kernel import Acted, Completed, Invoke
from shadow_hdk.runtime.devices import Overheard
from shadow_hdk.runtime.testing import FixedClock
from tests.adapters.mqtt.conftest import DeviceSide, LocalBroker, until
from tests.adapters.mqtt.test_mqtt import NOON, _observed, _run

# ---------------------------------------------------------------- BUG-002: one session per link


def _paho_threads() -> int:
    return sum(1 for t in threading.enumerate() if t.name.startswith("paho-mqtt-client"))


async def test_two_concurrent_first_uses_open_one_session(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    """Measured by the review: two clients, a publish queued twice, one client leaked past close."""
    link = MqttLink("127.0.0.1", broker.port, clock=FixedClock(NOON))
    link.witness("panel", "plant/events")
    before = _paho_threads()
    await asyncio.gather(link.connect(), link.connect(), link.connect())
    assert link.opened == 1, "each concurrent first use opened its own session"
    assert _paho_threads() == before + 1, "more network threads than sessions"
    assert await link.subscribed("plant/events")
    await device_side.publish("plant/events", {"id": "evt-1"})
    assert await until(lambda: link.pending("plant/events") >= 1)
    await asyncio.sleep(0.2)
    assert link.pending("plant/events") == 1, "one publish was routed once per session"
    await link.close()
    assert not link.connected
    assert await until(lambda: _paho_threads() == before), "a session outlived close()"


async def test_concurrent_acts_on_one_link_share_its_session(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    """Through real runs racing on one link — the `FanOut` case — every act is received once."""
    await device_side.listen("plant/valve/set")
    link = MqttLink("127.0.0.1", broker.port, clock=FixedClock(NOON))
    devices = DeviceComponents(actuators=[link.actuator("valve", "plant/valve/set")])
    runs = await asyncio.gather(
        *(_run(devices, Invoke("s1", "valve"), run_id=f"r-{i}") for i in range(4))
    )
    for events in runs:
        assert isinstance(_observed(events, "s1").observation, Acted)
    assert link.opened == 1
    assert await until(lambda: len(device_side.received.get("plant/valve/set", [])) == 4)
    await asyncio.sleep(0.2)
    keys = sorted(c["key"] for c in device_side.received["plant/valve/set"])
    assert keys == ["r-0/s1", "r-1/s1", "r-2/s1", "r-3/s1"]
    await link.close()


# ---------------------------------------------------------------- BUG-003: the network thread


async def test_a_fault_in_routing_does_not_kill_the_network_thread(
    broker: LocalBroker, device_side: DeviceSide, monkeypatch: pytest.MonkeyPatch
) -> None:
    """paho re-raises callback exceptions and ends its thread, leaving a link that says it is
    connected and hears nothing. A fault is counted and the thread lives."""
    link = MqttLink("127.0.0.1", broker.port, clock=FixedClock(NOON))
    sensor = link.sensor("thermometer", "plant/temp")
    await link.connect()
    assert await link.subscribed("plant/temp")
    real_route = link._route
    calls = {"n": 0}

    def flaky(message: Any) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("a routing fault")
        real_route(message)

    monkeypatch.setattr(link, "_route", flaky)
    await device_side.publish("plant/temp", {"value": 1})
    assert await until(lambda: link.faults == 1)
    await device_side.publish("plant/temp", {"value": 2})
    assert await until(lambda: link.seen("plant/temp")), "the thread died with the first fault"
    assert link.connected
    events = await _run(DeviceComponents(sensors=[sensor]), Invoke("s1", "thermometer"))
    reading = _observed(events, "s1").observation
    assert isinstance(reading, Completed) and isinstance(reading.output, dict)
    assert reading.output["value"] == 2
    await link.close()


class RecordingLock:
    """A lock that remembers who held it, so *under the lock* is a fact and not a hope. A stress
    test racing two threads passed with and without the lock — under the GIL the window is too
    small to hit on purpose — so the claim is asserted directly."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.held_during: list[str] = []
        self._during: str | None = None

    def during(self, what: str) -> None:
        self._during = what

    def __enter__(self) -> RecordingLock:
        self._lock.acquire()
        if self._during is not None:
            self.held_during.append(self._during)
        return self

    def __exit__(self, *_: object) -> None:
        self._lock.release()


def test_registration_happens_under_the_lock_the_network_thread_uses() -> None:
    link = MqttLink("127.0.0.1", 1, clock=FixedClock(NOON))
    lock = RecordingLock()
    link._lock = lock  # type: ignore[assignment]
    lock.during("sensor")
    link.sensor("thermometer", "plant/temp")
    lock.during("witness")
    link.witness("panel", "plant/events/#")
    lock.during("actuator")
    link.actuator("valve", "plant/valve/set", ack_topic="plant/valve/ack")
    assert {"sensor", "witness", "actuator"} <= set(lock.held_during), lock.held_during


def test_the_tables_exist_before_the_filter_is_visible() -> None:
    """A message routed between the filter appearing and its table appearing was a `KeyError` on
    the network thread. The filter set refuses an add whose table is not there yet."""
    link = MqttLink("127.0.0.1", 1, clock=FixedClock(NOON))

    class Checking(set[str]):
        def __init__(self, table: dict[str, Any]) -> None:
            super().__init__()
            self._table = table

        def add(self, topic: str) -> None:
            assert topic in self._table, f"{topic} became visible before its table existed"
            super().add(topic)

    link._sensor_filters = Checking(link._first)
    link._witness_filters = Checking(link._queues)
    link.sensor("thermometer", "plant/temp")
    link.witness("panel", "plant/events/#")
    assert "plant/temp" in link._sensor_filters and "plant/events/#" in link._witness_filters


async def test_a_fault_in_another_callback_does_not_kill_the_thread_either(
    broker: LocalBroker, device_side: DeviceSide, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`_on_message` is wrapped; `on_subscribe` is not. paho would end its thread on the raise;
    `suppress_exceptions` is what keeps it alive, and this test is what makes it not dead code."""
    link = MqttLink("127.0.0.1", broker.port, clock=FixedClock(NOON))
    sensor = link.sensor("thermometer", "plant/temp")

    def broken(*_: Any) -> None:
        raise RuntimeError("a fault in on_subscribe")

    monkeypatch.setattr(link, "_on_subscribe", broken)
    await link.connect()
    await asyncio.sleep(0.2)
    assert link.connected
    await device_side.publish("plant/temp", {"value": 5}, retain=True)
    assert await until(lambda: link.seen("plant/temp")), "the thread died in on_subscribe"
    events = await _run(DeviceComponents(sensors=[sensor]), Invoke("s1", "thermometer"))
    reading = _observed(events, "s1").observation
    assert isinstance(reading, Completed) and isinstance(reading.output, dict)
    assert reading.output["value"] == 5
    await link.close()


async def test_a_device_registered_while_the_link_opens_is_subscribed(
    broker: LocalBroker, device_side: DeviceSide, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The window between `_open`'s snapshot of the filters and `self._client = client`: a device
    registered there sees no live client and leaves its subscription to nobody. The registration
    is injected exactly there, on the opening thread, so the window is hit every time."""
    link = MqttLink("127.0.0.1", broker.port, clock=FixedClock(NOON))
    real_filters = link._filters
    calls = {"n": 0}

    def filters_then_a_late_registration() -> set[str]:
        snapshot = real_filters()
        calls["n"] += 1
        if calls["n"] == 1:
            link.sensor("thermometer", "plant/temp")  # after the snapshot, before assignment
        return snapshot

    monkeypatch.setattr(link, "_filters", filters_then_a_late_registration)
    await link.connect()
    assert await link.subscribed("plant/temp"), "registered while opening, never subscribed"
    await device_side.publish("plant/temp", {"value": 9})
    assert await until(lambda: link.seen("plant/temp"))
    await link.close()


# ---------------------------------------------------------------- TD-002: a bounded witness queue


async def test_a_witness_queue_is_bounded_and_says_what_it_dropped(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    """A late reading is data; so is a lost event."""
    link = MqttLink("127.0.0.1", broker.port, clock=FixedClock(NOON))
    panel = link.witness("panel", "plant/events", keep=2)
    await link.connect()
    assert await link.subscribed("plant/events")
    for n in (1, 2, 3, 4):
        await device_side.publish("plant/events", {"id": f"evt-{n}"})
    assert await until(lambda: link.dropped("plant/events") == 2)
    assert link.pending("plant/events") == 2
    events = await _run(
        DeviceComponents(witnesses=[panel]), Invoke("s1", "panel"), Invoke("s2", "panel")
    )
    first = _observed(events, "s1").observation
    assert isinstance(first, Acted) and first.foreign_id == "evt-3"
    assert isinstance(first.grounds, dict) and first.grounds["dropped_before"] == 2
    second = _observed(events, "s2").observation
    assert isinstance(second, Acted) and second.foreign_id == "evt-4"
    assert isinstance(second.grounds, dict) and "dropped_before" not in second.grounds
    await link.close()


def test_overheard_carries_what_was_dropped_before_it() -> None:
    assert Overheard(foreign_id="e", what=None, at=NOON).dropped_before == 0


# ---------------------------------------------------------------- ENH-001: a sensor names one topic


@pytest.mark.parametrize("wild", ["plant/+/temp", "plant/#"])
def test_a_sensor_names_one_topic(wild: str) -> None:
    """`_latest` is keyed by the filter, so a wildcard sensor could not say which device it read."""
    link = MqttLink("127.0.0.1", 1, clock=FixedClock(NOON))
    with pytest.raises(ValueError, match="one topic"):
        link.sensor("thermometer", wild)
    link.witness("panel", wild)  # a witness may still overhear a whole subtree
