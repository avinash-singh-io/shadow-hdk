"""One device contract, three roles (D31).

A `Sensor` reads the world; an `Actuator` writes it and cannot take it back; a `Witness` reads the
world's own log and reports what happened without us. Posture follows the role: a read we asked
for and a command we gave are `controlled`; what a witness reports is `observed` (D30). A protocol
adapter — MQTT, OPC-UA, ROS 2 — is written over these three and nothing else.

Lives in the runtime, beside `acting.py`, rather than in `adapters/devices`, because no adapter may
import another (`tests/invariants`) and every protocol adapter implements this: three protocols and
three dataclasses with no I/O, the vocabulary of the act's world-facing half. Not the kernel — the
kernel names ports, events, effects and observations, and a device is none of those; it is a
component, and how a component reaches the world is the runtime's business.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from pydantic import JsonValue


@dataclass(frozen=True)
class Reading:
    """What a sensor said, with the **device's own** stamp — the runtime adds the age."""

    value: JsonValue
    unit: str | None
    at: str


@dataclass(frozen=True)
class Ack:
    """How the device answered a command: what it called it, and how it ended in its own words."""

    foreign_id: str
    exit: str


@dataclass(frozen=True)
class Overheard:
    """An act the world reports: what the device called it, what happened, when, how it ended,
    and — if the device keys its own events — the key a retry would carry."""

    foreign_id: str
    what: JsonValue
    at: str
    exit: str = "done"
    idempotency_key: str | None = None


@runtime_checkable
class Sensor(Protocol):
    id: str

    async def read(self) -> Reading: ...


@runtime_checkable
class Actuator(Protocol):
    id: str

    async def command(self, argv: JsonValue, *, key: str) -> Ack:
        """Perform it. `key` is the run's idempotency key, handed to the device so the world can
        tell a retry from a second act. Raising is the honest answer when the ack never came."""
        ...


@runtime_checkable
class Witness(Protocol):
    id: str

    async def overheard(self) -> Overheard | None:
        """The next act overheard and not yet reported, or `None`."""
        ...


__all__ = ["Ack", "Actuator", "Overheard", "Reading", "Sensor", "Witness"]
