"""MQTT topics as sensors, actuators and witnesses (D32), through real runs against a local
broker the suite starts and stops."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from shadow_hdk.adapters.basic import AllowAll

from shadow_hdk.adapters.devices import DeviceComponents
from shadow_hdk.adapters.mqtt import MqttLink
from shadow_hdk.kernel import (
    Acted,
    Ceiling,
    Completed,
    Composition,
    Event,
    Failed,
    Floor,
    Invoke,
    Lease,
    Observed,
)
from shadow_hdk.kernel.ports import ComponentPort
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel
from tests.adapters.mqtt.conftest import DeviceSide, LocalBroker, until

NOON = "2026-01-01T12:00:00+00:00"
EARLIER = "2026-01-01T11:00:00+00:00"
LEASE = Lease(Ceiling(10, 600, 100), Floor(0))


async def _run(
    devices: ComponentPort, *steps: Invoke, clock: FixedClock | None = None, run_id: str = "r-1"
) -> list[Event]:
    ports = Ports(
        model=ScriptedModel(),
        components=(devices,),
        governance=AllowAll(),
        sink=ListSink(),
        clock=clock if clock is not None else FixedClock(NOON),
    )
    return [
        e
        async for e in run(
            Composition(steps), ports, options=RunOptions(lease=LEASE, run_id=run_id)
        )
    ]


def _observed(events: Sequence[Event], step: str) -> Observed:
    found = [e for e in events if isinstance(e, Observed) and e.step == step]
    assert len(found) == 1, found
    return found[0]


def _link(broker: LocalBroker, clock: FixedClock | None = None, **kw: Any) -> MqttLink:
    return MqttLink("127.0.0.1", broker.port, clock=clock or FixedClock(NOON), **kw)


# ---------------------------------------------------------------- the sensor


async def test_a_retained_reading_carries_the_devices_stamp_and_its_age(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    await device_side.publish(
        "plant/temp", {"value": 21.5, "unit": "C", "at": "2026-01-01T11:59:00+00:00"}, retain=True
    )
    async with _link(broker) as link:
        devices = DeviceComponents(sensors=[link.sensor("thermometer", "plant/temp")])
        await link.connect()
        events = await _run(devices, Invoke("s1", "thermometer"))
    reading = _observed(events, "s1").observation
    assert reading == Completed(
        {
            "value": 21.5,
            "unit": "C",
            "at": "2026-01-01T11:59:00+00:00",
            "stamped_by": "device",
            "age_seconds": 60.0,
        }
    )


async def test_a_reading_with_no_stamp_is_stamped_by_the_receiver(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    clock = FixedClock(NOON)
    async with _link(broker, clock) as link:
        sensor = link.sensor("thermometer", "plant/temp")
        await link.connect()
        assert await link.subscribed("plant/temp"), "the broker never acknowledged the subscription"
        await device_side.publish("plant/temp", {"value": 3})
        assert await until(lambda: link.seen("plant/temp"))
        events = await _run(
            DeviceComponents(sensors=[sensor]), Invoke("s1", "thermometer"), clock=clock
        )
    reading = _observed(events, "s1").observation
    assert reading == Completed(
        {"value": 3, "unit": None, "at": NOON, "stamped_by": "receiver", "age_seconds": 0.0}
    )


async def test_nothing_published_yet_is_failed_naming_the_topic(broker: LocalBroker) -> None:
    async with _link(broker, grace=0.1) as link:
        devices = DeviceComponents(sensors=[link.sensor("thermometer", "plant/temp")])
        events = await _run(devices, Invoke("s1", "thermometer"))
    failed = _observed(events, "s1").observation
    assert isinstance(failed, Failed) and "plant/temp" in failed.error


async def test_a_payload_that_is_not_json_is_a_reading_of_its_text(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    await device_side.publish("plant/label", "lathe 4", retain=True)
    async with _link(broker) as link:
        devices = DeviceComponents(sensors=[link.sensor("label", "plant/label")])
        events = await _run(devices, Invoke("s1", "label"))
    reading = _observed(events, "s1").observation
    assert isinstance(reading, Completed) and isinstance(reading.output, dict)
    assert reading.output["value"] == "lathe 4" and reading.output["unit"] is None


# ---------------------------------------------------------------- the actuator


async def test_a_command_without_an_ack_topic_is_published_and_says_so(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    await device_side.listen("plant/valve/set")
    async with _link(broker) as link:
        devices = DeviceComponents(actuators=[link.actuator("valve", "plant/valve/set")])
        events = await _run(devices, Invoke("s1", "valve", ()), run_id="r-7")
    receipt = _observed(events, "s1").observation
    assert isinstance(receipt, Acted)
    assert receipt.idempotency_key == "r-7/s1" and receipt.exit == "published"
    assert receipt.foreign_id.startswith("plant/valve/set#")
    assert await until(lambda: bool(device_side.received.get("plant/valve/set")))
    assert device_side.received["plant/valve/set"] == [{"key": "r-7/s1", "argv": {}}]
    assert device_side.qos_seen["plant/valve/set"] == [1], (
        "a command is QoS 1: the PUBACK is the word"
    )


async def test_a_command_with_an_ack_topic_carries_the_devices_own_answer(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    await device_side.answers(
        "plant/valve/set",
        "plant/valve/ack",
        lambda command: {"key": command["key"], "id": "cmd-9", "exit": "opened"},
    )
    async with _link(broker) as link:
        valve = link.actuator("valve", "plant/valve/set", ack_topic="plant/valve/ack")
        events = await _run(DeviceComponents(actuators=[valve]), Invoke("s1", "valve"))
    receipt = _observed(events, "s1").observation
    assert isinstance(receipt, Acted)
    assert receipt.foreign_id == "cmd-9" and receipt.exit == "opened"


async def test_an_ack_for_another_key_is_not_ours(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    await device_side.answers(
        "plant/valve/set", "plant/valve/ack", lambda c: {"key": "someone-else", "exit": "opened"}
    )
    async with _link(broker, timeout=0.5) as link:
        valve = link.actuator("valve", "plant/valve/set", ack_topic="plant/valve/ack")
        events = await _run(DeviceComponents(actuators=[valve]), Invoke("s1", "valve"))
    failed = _observed(events, "s1").observation
    assert isinstance(failed, Failed) and "TimeoutError" in failed.error


async def test_no_ack_within_the_timeout_is_failed_and_no_receipt(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    """The command went out — the device side has it — and the ack never came: no receipt."""
    await device_side.listen("plant/valve/set")
    async with _link(broker, timeout=0.5) as link:
        valve = link.actuator("valve", "plant/valve/set", ack_topic="plant/valve/ack")
        events = await _run(DeviceComponents(actuators=[valve]), Invoke("s1", "valve"))
    failed = _observed(events, "s1").observation
    assert isinstance(failed, Failed) and "plant/valve/ack" in failed.error
    assert not [e for e in events if isinstance(e, Observed) and isinstance(e.observation, Acted)]
    assert await until(lambda: bool(device_side.received.get("plant/valve/set")))


# ---------------------------------------------------------------- the witness


async def test_events_are_overheard_one_per_invoke_as_observed_receipts(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    async with _link(broker) as link:
        panel = link.witness("panel", "plant/events/#")
        await link.connect()
        assert await link.subscribed("plant/events/#"), (
            "the broker never acknowledged the subscription"
        )
        await device_side.publish(
            "plant/events/valve", {"id": "evt-1", "what": "opened", "at": EARLIER, "exit": "opened"}
        )
        await device_side.publish(
            "plant/events/door", {"id": "evt-2", "what": "closed", "key": "op:4"}
        )
        assert await until(lambda: link.pending("plant/events/#") == 2)
        events = await _run(
            DeviceComponents(witnesses=[panel]),
            Invoke("s1", "panel"),
            Invoke("s2", "panel"),
            Invoke("s3", "panel"),
        )
    first = _observed(events, "s1")
    assert first.posture == "observed"
    assert isinstance(first.observation, Acted)
    assert first.observation.foreign_id == "evt-1" and first.observation.exit == "opened"
    assert first.observation.idempotency_key == "panel/evt-1"
    assert first.observation.grounds == {
        "reported_by": "panel",
        "at": EARLIER,
        "what": {"id": "evt-1", "what": "opened", "at": EARLIER, "exit": "opened"},
        "posture": "observed",
    }
    second = _observed(events, "s2").observation
    assert isinstance(second, Acted)
    assert second.foreign_id == "evt-2" and second.idempotency_key == "op:4"
    assert second.exit == "reported"
    assert isinstance(second.grounds, dict) and second.grounds["at"] == NOON
    assert _observed(events, "s3").observation == Completed({"overheard": 0})


async def test_an_event_that_is_not_json_is_overheard_as_text(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    async with _link(broker) as link:
        panel = link.witness("panel", "plant/events")
        await link.connect()
        assert await link.subscribed("plant/events"), (
            "the broker never acknowledged the subscription"
        )
        await device_side.publish("plant/events", "door slammed")
        assert await until(lambda: link.pending("plant/events") == 1)
        events = await _run(DeviceComponents(witnesses=[panel]), Invoke("s1", "panel"))
    act = _observed(events, "s1").observation
    assert isinstance(act, Acted)
    assert act.foreign_id == "plant/events#1" and act.grounds == {
        "reported_by": "panel",
        "at": NOON,
        "what": "door slammed",
        "posture": "observed",
    }


async def test_a_sensor_registered_after_connect_is_subscribed(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    async with _link(broker) as link:
        await link.connect()
        sensor = link.sensor("thermometer", "plant/temp")
        assert await link.subscribed("plant/temp"), "the broker never acknowledged the subscription"
        await device_side.publish("plant/temp", {"value": 7})
        assert await until(lambda: link.seen("plant/temp"))
        events = await _run(DeviceComponents(sensors=[sensor]), Invoke("s1", "thermometer"))
    reading = _observed(events, "s1").observation
    assert isinstance(reading, Completed) and isinstance(reading.output, dict)
    assert reading.output["value"] == 7


# ---------------------------------------------------------------- the link


async def test_a_closed_link_is_not_reopened_behind_the_callers_back(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    await device_side.publish("plant/temp", {"value": 1}, retain=True)
    link = _link(broker)
    devices = DeviceComponents(sensors=[link.sensor("thermometer", "plant/temp")])
    await link.connect()
    assert await until(lambda: link.seen("plant/temp")), "the retained message never arrived"
    await link.close()
    events = await _run(devices, Invoke("s1", "thermometer"))
    failed = _observed(events, "s1").observation
    assert isinstance(failed, Failed) and "closed" in failed.error


@pytest.mark.parametrize("bad", ["plant/#/x", "plant/a+b", ""])
def test_a_topic_the_broker_would_refuse_is_refused_at_registration(bad: str) -> None:
    """No broker needed: refused before anything connects."""
    link = MqttLink("127.0.0.1", 1, clock=FixedClock(NOON))
    with pytest.raises(ValueError):
        link.sensor("thermometer", bad)
    with pytest.raises(ValueError):
        link.witness("panel", bad)


@pytest.mark.parametrize("bad", ["plant/#", "plant/+/set", ""])
def test_a_command_topic_names_one_topic(bad: str) -> None:
    link = MqttLink("127.0.0.1", 1, clock=FixedClock(NOON))
    with pytest.raises(ValueError):
        link.actuator("valve", bad)
