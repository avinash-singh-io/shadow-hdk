"""One device contract, three roles, the fake first (D29, D30, D31).

Every test drives a real run through `DeviceComponents`. The environment is varied where the claim
is about the environment: a reading that is late by the runtime's clock, a catalogue that takes so
long the lease is spent by the time the actuator is reached, a device that disconnects mid-act.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from pydantic import JsonValue

from shadow_hdk.adapters.basic import AllowAll, Controlled
from shadow_hdk.adapters.devices import DeviceComponents, Overheard
from shadow_hdk.adapters.devices.testing import FakeActuator, FakeSensor, FakeWitness
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
    Refused,
    Registration,
    ScopeSet,
)
from shadow_hdk.kernel.components import RegistrationId
from shadow_hdk.kernel.ports import ComponentPort, GovernancePort
from shadow_hdk.runtime import InMemoryEffectJournal, Ports, RunOptions, run
from shadow_hdk.runtime.testing import (
    AllowAuthorizer,
    FixedAuthority,
    FixedClock,
    ListSink,
    ScriptedModel,
)

WORLD = ScopeSet.of("world")
NOON = "2026-01-01T12:00:00+00:00"
LEASE = Lease(Ceiling(10, 600, 100), Floor(0))


class SlowCatalogue(ComponentPort):
    """A port whose catalogue takes a while to answer — a server that is not quite there."""

    def __init__(self, clock: FixedClock, seconds: float) -> None:
        self._clock, self._seconds = clock, seconds

    async def registrations(self) -> Sequence[Registration]:
        self._clock.advance(self._seconds)
        return []

    async def invoke(self, _r: RegistrationId, _i: JsonValue) -> Completed:
        return Completed(None)


async def _run(
    devices: DeviceComponents,
    *steps: Invoke,
    clock: FixedClock | None = None,
    governance: GovernancePort | None = None,
    also: tuple[ComponentPort, ...] = (),
    run_id: str = "r-1",
) -> list[Event]:
    chosen_clock = clock if clock is not None else FixedClock(NOON)
    ports = Ports(
        model=ScriptedModel(),
        components=(devices, *also),
        governance=governance if governance is not None else AllowAll(),
        sink=ListSink(),
        clock=chosen_clock,
        authority=FixedAuthority(),
        authorizer=AllowAuthorizer(),
        effect_journal=InMemoryEffectJournal(),
    )
    return [
        e
        async for e in run(
            Composition(steps), ports, options=RunOptions(lease=LEASE, run_id=run_id)
        )
    ]


def _observed(events: list[Event], step: str) -> Observed:
    found = [e for e in events if isinstance(e, Observed) and e.step == step]
    assert len(found) == 1, found
    return found[0]


# ---------------------------------------------------------------- roles and effects


async def test_each_role_declares_its_effects_and_posture() -> None:
    devices = DeviceComponents(
        sensors=[FakeSensor("thermometer", value=21.5, unit="C", at=NOON)],
        actuators=[FakeActuator("valve")],
        witnesses=[FakeWitness("operator_panel", [])],
    )
    by_id = {r.id: r.component for r in await devices.registrations()}
    assert by_id["thermometer"].effects.reads == WORLD
    assert not by_id["thermometer"].effects.writes.names
    assert by_id["thermometer"].provenance.posture == "controlled"
    assert by_id["valve"].effects.writes == WORLD
    assert by_id["valve"].effects.reversible is False
    assert by_id["valve"].provenance.posture == "controlled"
    assert by_id["operator_panel"].effects.reads == WORLD
    assert not by_id["operator_panel"].effects.writes.names
    assert by_id["operator_panel"].provenance.posture == "observed"
    assert {"device", "sensor"} <= by_id["thermometer"].labels
    assert {"device", "actuator"} <= by_id["valve"].labels
    assert {"device", "witness"} <= by_id["operator_panel"].labels


def test_one_id_cannot_be_two_roles() -> None:
    """Its effects would be the union, and no rule could permit reading without commanding."""
    with pytest.raises(ValueError, match="valve"):
        DeviceComponents(
            sensors=[FakeSensor("valve", value=1, unit=None, at=NOON)],
            actuators=[FakeActuator("valve")],
        )


# ---------------------------------------------------------------- the sensor


async def test_a_reading_carries_the_devices_stamp_and_its_age_by_the_runtimes_clock() -> None:
    clock = FixedClock(NOON)
    sensor = FakeSensor("thermometer", value=21.5, unit="C", at="2026-01-01T11:59:00+00:00")
    devices = DeviceComponents(sensors=[sensor])
    events = await _run(devices, Invoke("s1", "thermometer"), clock=clock)
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
    clock.advance(30)
    events = await _run(devices, Invoke("s1", "thermometer"), clock=clock)
    later = _observed(events, "s1").observation
    assert isinstance(later, Completed) and isinstance(later.output, dict)
    assert later.output["age_seconds"] == 90.0


async def test_a_stamp_the_runtime_cannot_read_has_no_age() -> None:
    devices = DeviceComponents(sensors=[FakeSensor("thermometer", value=1, unit=None, at="soon")])
    events = await _run(devices, Invoke("s1", "thermometer"))
    reading = _observed(events, "s1").observation
    assert isinstance(reading, Completed) and isinstance(reading.output, dict)
    assert reading.output["age_seconds"] is None and reading.output["at"] == "soon"


# ---------------------------------------------------------------- the actuator


async def test_a_command_leaves_a_receipt_with_the_lease_read_at_the_act() -> None:
    valve = FakeActuator("valve")
    devices = DeviceComponents(actuators=[valve])
    events = await _run(devices, Invoke("s1", "valve", ()), run_id="r-7")
    receipt = _observed(events, "s1")
    assert receipt.posture == "controlled"
    assert isinstance(receipt.observation, Acted)
    assert receipt.observation.foreign_id == "valve#1"
    assert receipt.observation.idempotency_key == "r-7/s1"
    assert receipt.observation.exit == "acknowledged", "the exit is the device's own word"
    grounds = receipt.observation.grounds
    assert isinstance(grounds, dict) and isinstance(grounds["lease"], dict)
    assert grounds["lease"]["max_steps"] == 9 and grounds["lease"]["max_wall_seconds"] == 600
    assert grounds["argv"] == {} and grounds["step"] == "s1" and grounds["run"] == "r-7"
    assert valve.commands == [("r-7/s1", {})]


async def test_a_command_on_a_spent_lease_is_refused_and_the_world_is_untouched() -> None:
    """The step was admitted with 600 s left; a catalogue that takes 601 s to answer sits between
    admission and the act, and the lease is read at the act."""
    clock = FixedClock(NOON)
    valve = FakeActuator("valve")
    devices = DeviceComponents(actuators=[valve])
    events = await _run(
        devices, Invoke("s1", "valve"), clock=clock, also=(SlowCatalogue(clock, 601),)
    )
    refused = _observed(events, "s1").observation
    assert isinstance(refused, Refused) and "time" in refused.reason
    assert valve.commands == []


async def test_a_device_that_disconnects_mid_act_is_failed_and_leaves_no_receipt() -> None:
    """The command went out; the ack never came back. That is `Failed`, not a receipt — and the
    world may have moved, which is what the idempotency key is for on the retry."""
    valve = FakeActuator("valve").disconnect_after(0)
    devices = DeviceComponents(actuators=[valve])
    events = await _run(devices, Invoke("s1", "valve"))
    failed = _observed(events, "s1").observation
    assert isinstance(failed, Failed) and "ConnectionError" in failed.error
    assert not [e for e in events if isinstance(e, Observed) and isinstance(e.observation, Acted)]
    assert len(valve.commands) == 1, "the command had been sent when the link dropped"


# ---------------------------------------------------------------- the witness


async def test_a_witnessed_act_is_an_observed_receipt_naming_the_device() -> None:
    panel = FakeWitness(
        "operator_panel",
        [
            Overheard(foreign_id="evt-41", what={"valve": "opened"}, at=NOON, exit="opened"),
            Overheard(foreign_id="evt-42", what={"valve": "closed"}, at=NOON, exit="closed"),
        ],
    )
    devices = DeviceComponents(witnesses=[panel])
    events = await _run(
        devices,
        Invoke("s1", "operator_panel"),
        Invoke("s2", "operator_panel"),
        Invoke("s3", "operator_panel"),
        governance=Controlled(AllowAll()),
    )
    first = _observed(events, "s1")
    assert first.posture == "observed", "the runtime stamps the posture, not the device"
    assert isinstance(first.observation, Acted)
    assert first.observation.foreign_id == "evt-41"
    assert first.observation.idempotency_key == "operator_panel/evt-41"
    assert first.observation.exit == "opened"
    assert first.observation.grounds == {
        "reported_by": "operator_panel",
        "at": NOON,
        "what": {"valve": "opened"},
        "posture": "observed",
    }
    second = _observed(events, "s2").observation
    assert isinstance(second, Acted) and second.foreign_id == "evt-42"
    assert _observed(events, "s3").observation == Completed({"overheard": 0})


async def test_an_overheard_act_keeps_the_key_the_device_gave_it() -> None:
    panel = FakeWitness(
        "panel", [Overheard(foreign_id="evt-1", what=None, at=NOON, idempotency_key="op:9")]
    )
    events = await _run(DeviceComponents(witnesses=[panel]), Invoke("s1", "panel"))
    act = _observed(events, "s1").observation
    assert isinstance(act, Acted) and act.idempotency_key == "op:9"


async def test_controlled_admits_the_witness_and_the_actuator_alike() -> None:
    """A witness reads; an actuator we command is controlled. Neither is what `Controlled`
    refuses — an observed *effect* — and the record still says which was which."""
    devices = DeviceComponents(
        actuators=[FakeActuator("valve")], witnesses=[FakeWitness("panel", [])]
    )
    events = await _run(
        devices, Invoke("s1", "valve"), Invoke("s2", "panel"), governance=Controlled(AllowAll())
    )
    assert isinstance(_observed(events, "s1").observation, Acted)
    assert _observed(events, "s1").posture == "controlled"
    assert _observed(events, "s2").observation == Completed({"overheard": 0})
    assert _observed(events, "s2").posture == "observed"


async def test_an_actuator_outside_a_run_is_failed_and_nothing_is_performed() -> None:
    """No run means no lease to read and no key to hand over; refused before the device."""
    valve = FakeActuator("valve")
    devices = DeviceComponents(actuators=[valve])
    outcome = await devices.invoke("valve", {})
    assert isinstance(outcome, Failed) and "inside a run" in outcome.error
    assert valve.commands == []
