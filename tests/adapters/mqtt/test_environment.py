"""The broker that is not there, the one that refuses us, and the one that leaves and comes back.

A claim of independence from the environment is only tested by varying the environment. Every
outcome is read through a real run: what the step observed, and what the device on the other side
of the broker did or did not receive.
"""

from __future__ import annotations

import pytest

from shadow_hdk.adapters.devices import DeviceComponents
from shadow_hdk.adapters.mqtt import MqttLink
from shadow_hdk.kernel import Acted, Failed, Invoke
from shadow_hdk.runtime.testing import FixedClock
from tests.adapters.mqtt.conftest import DeviceSide, LocalBroker, free_port, until
from tests.adapters.mqtt.test_mqtt import NOON, _observed, _run


async def test_a_broker_that_is_not_there_fails_the_act_and_connect_says_so() -> None:
    link = MqttLink("127.0.0.1", free_port(), clock=FixedClock(NOON), timeout=1)
    valve = link.actuator("valve", "plant/valve/set")
    events = await _run(DeviceComponents(actuators=[valve]), Invoke("s1", "valve"))
    failed = _observed(events, "s1").observation
    assert isinstance(failed, Failed) and "refused" in failed.error.lower(), failed
    assert not [e for e in events if isinstance(getattr(e, "observation", None), Acted)]
    with pytest.raises(ConnectionError):
        await link.connect()
    assert not link.connected


async def test_a_broker_that_refuses_us_is_a_connection_error_naming_the_refusal() -> None:
    strict = LocalBroker(free_port(), anonymous=False)
    await strict.start()
    try:
        link = MqttLink("127.0.0.1", strict.port, clock=FixedClock(NOON), timeout=2)
        with pytest.raises(ConnectionError, match="refused the connection"):
            await link.connect()
        devices = DeviceComponents(sensors=[link.sensor("thermometer", "plant/temp")])
        events = await _run(devices, Invoke("s1", "thermometer"))
        failed = _observed(events, "s1").observation
        assert isinstance(failed, Failed) and "refused the connection" in failed.error
    finally:
        await strict.stop()


async def test_a_broker_that_leaves_fails_the_act_and_nothing_is_sent_when_it_is_back(
    broker: LocalBroker, device_side: DeviceSide
) -> None:
    """A step that failed must not change the world later. The failed command is never handed to
    the client, and once the broker is back the only command the device sees is the new act's."""
    await device_side.listen("plant/valve/set")
    link = MqttLink("127.0.0.1", broker.port, clock=FixedClock(NOON), timeout=1)
    devices = DeviceComponents(actuators=[link.actuator("valve", "plant/valve/set")])
    first = await _run(devices, Invoke("s1", "valve"), run_id="before")
    assert isinstance(_observed(first, "s1").observation, Acted)
    assert await until(lambda: len(device_side.received.get("plant/valve/set", [])) == 1)

    await broker.stop()
    assert await until(lambda: not link.connected), "the link never noticed the broker leave"
    second = await _run(devices, Invoke("s1", "valve"), run_id="while-gone")
    failed = _observed(second, "s1").observation
    assert isinstance(failed, Failed) and "refused" in failed.error.lower(), failed

    await broker.start()
    back = DeviceSide(broker.port)
    await back.connect()
    try:
        await back.listen("plant/valve/set")
        await until(lambda: bool(back.received.get("plant/valve/set")), timeout=1.0)
        assert back.received.get("plant/valve/set", []) == [], "a failed act reached the world late"
        third = await _run(devices, Invoke("s1", "valve"), run_id="after")
        assert isinstance(_observed(third, "s1").observation, Acted)
        assert await until(lambda: bool(back.received.get("plant/valve/set")))
        assert [c["key"] for c in back.received["plant/valve/set"]] == ["after/s1"]
    finally:
        await back.close()
    await link.close()
