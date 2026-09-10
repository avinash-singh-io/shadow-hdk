"""Devices as components: D29's effects, the role's posture, Phase 13's act.

`DeviceComponents` is a component port over a set of devices. It registers each with the effects
its role declares — a sensor `reads: {world}`, an actuator `writes: {world}` irreversibly, a
witness `reads: {world}` with posture `observed` — and performs the act the way Phase 13 says a
world-effect is performed: the lease read at the moment of the act, the run's idempotency key
handed to the device, the receipt carrying its grounds. One id cannot be two roles: its effects
would be the union, and no rule could permit reading it without permitting commanding it.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from pydantic import JsonValue

from shadow_hdk.kernel.components import (
    Component,
    Interface,
    Posture,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.effects import EffectProfile, ScopeSet
from shadow_hdk.kernel.observations import Acted, Completed, Failed, Observation, Refused
from shadow_hdk.kernel.ports import ComponentPort
from shadow_hdk.runtime import current_run
from shadow_hdk.runtime.acting import exhausted, grounds
from shadow_hdk.runtime.devices import Actuator, Sensor, Witness

WORLD = ScopeSet.of("world")
SENSES = EffectProfile(reads=WORLD)
WRITES = EffectProfile(writes=WORLD, reversible=False)


class DeviceComponents(ComponentPort):
    def __init__(
        self,
        *,
        sensors: Sequence[Sensor] = (),
        actuators: Sequence[Actuator] = (),
        witnesses: Sequence[Witness] = (),
        registered_by: str = "devices",
        at: str = "",
    ) -> None:
        self._sensors = {s.id: s for s in sensors}
        self._actuators = {a.id: a for a in actuators}
        self._witnesses = {w.id: w for w in witnesses}
        roles = [*self._sensors, *self._actuators, *self._witnesses]
        for name in sorted({n for n in roles if roles.count(n) > 1}):
            raise ValueError(f"{name!r} is registered as more than one role; one id, one role")
        self._registered_by, self._at = registered_by, at

    async def registrations(self) -> Sequence[Registration]:
        return [
            *(self._register(s.id, "sensor", SENSES, "controlled") for s in self._sensors.values()),
            *(
                self._register(a.id, "actuator", WRITES, "controlled")
                for a in self._actuators.values()
            ),
            *(
                self._register(w.id, "witness", SENSES, "observed")
                for w in self._witnesses.values()
            ),
        ]

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        if (sensor := self._sensors.get(registration)) is not None:
            return await _read(sensor)
        if (actuator := self._actuators.get(registration)) is not None:
            return await _command(actuator, inputs)
        if (witness := self._witnesses.get(registration)) is not None:
            return await _report(witness)
        return Failed(f"no device registered as {registration!r}")

    def _register(
        self, name: str, role: str, effects: EffectProfile, posture: Posture
    ) -> Registration:
        return Registration(
            id=name,
            component=Component(
                interface=Interface(
                    name=name,
                    description=f"{name}, a {role}",
                    input_schema={"type": "object"},
                    output_schema={"type": "object"},
                ),
                effects=effects,
                provenance=Provenance(
                    registered_by=self._registered_by,
                    adapter="devices",
                    at=self._at,
                    posture=posture,
                ),
                labels=frozenset({"device", role}),
            ),
        )


async def _read(sensor: Sensor) -> Observation:
    reading = await sensor.read()
    context = current_run()
    return Completed(
        {
            "value": reading.value,
            "unit": reading.unit,
            "at": reading.at,
            "age_seconds": _age(reading.at, context.now()) if context is not None else None,
        }
    )


async def _command(actuator: Actuator, argv: JsonValue) -> Observation:
    context = current_run()
    if context is None:
        return Failed("an actuator acts only inside a run: there is no lease and no key")
    if why := exhausted(context.remaining()):
        return Refused(why)
    key = context.idempotency_key()
    ack = await actuator.command(argv, key=key)
    return Acted(
        foreign_id=ack.foreign_id,
        idempotency_key=key,
        exit=ack.exit,
        grounds=grounds(context, argv=argv),
    )


async def _report(witness: Witness) -> Observation:
    overheard = await witness.overheard()
    if overheard is None:
        return Completed({"overheard": 0})
    return Acted(
        foreign_id=overheard.foreign_id,
        idempotency_key=overheard.idempotency_key or f"{witness.id}/{overheard.foreign_id}",
        exit=overheard.exit,
        grounds={
            "reported_by": witness.id,
            "at": overheard.at,
            "what": overheard.what,
            "posture": "observed",
        },
    )


def _age(stamped: str, now: str) -> float | None:
    """How old a reading is by the runtime's clock, or `None` when the device's stamp cannot be
    read — a late reading is the ordinary failure of a sensor, and the agent should see it as
    data rather than have it hidden."""
    try:
        return (datetime.fromisoformat(now) - datetime.fromisoformat(stamped)).total_seconds()
    except ValueError:
        return None


__all__ = ["SENSES", "WORLD", "WRITES", "DeviceComponents"]
