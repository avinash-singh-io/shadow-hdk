"""The devices adapter, held to the component contract (TD-004).

A device is a component and not a port (D29), so it answers exactly the questions any component
does. The fakes are the first devices (D31) and are what makes this runnable with no broker, no
server and no hardware.
"""

from __future__ import annotations

from pydantic import JsonValue

from shadow_hdk.adapters.devices import DeviceComponents
from shadow_hdk.adapters.devices.testing import FakeActuator, FakeSensor, FakeWitness
from shadow_hdk.kernel.components import RegistrationId
from shadow_hdk.kernel.ports import ComponentPort
from shadow_hdk.testing.contracts import ComponentPortContract


class TestDeviceComponentsIsAComponentPort(ComponentPortContract):
    def port(self) -> ComponentPort:
        return DeviceComponents(
            sensors=[
                FakeSensor("thermometer", value="21.5", unit="C", at="2026-01-01T00:00:00+00:00")
            ],
            actuators=[FakeActuator("valve")],
            witnesses=[FakeWitness("bus", [])],
            at="2026-01-01T00:00:00+00:00",
        )

    def valid_call(self) -> tuple[RegistrationId, JsonValue]:
        return "thermometer", {}
