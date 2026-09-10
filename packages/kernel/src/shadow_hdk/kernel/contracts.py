"""The kernel's contracts are published as JSON Schema from day one (09 §3b).

A TypeScript host reads the same schemas this code is generated from. ``round_trip`` is the CI
proof that nothing a port carries can be a callable, a live object, or anything else that cannot
cross a wire.
"""

from __future__ import annotations

from typing import Any, overload

from pydantic import JsonValue, TypeAdapter

from shadow_hdk.kernel.components import Component, Registration
from shadow_hdk.kernel.composition import Composition
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import Event
from shadow_hdk.kernel.leases import Lease
from shadow_hdk.kernel.observations import Observation, Proposal
from shadow_hdk.kernel.ports import (
    Context,
    Judgement,
    ModelRequest,
    ModelResponse,
)

CONTRACTS: dict[str, Any] = {
    "EffectProfile": EffectProfile,
    "Component": Component,
    "Registration": Registration,
    "Composition": Composition,
    "Observation": Observation,
    "Proposal": Proposal,
    "Lease": Lease,
    "Event": Event,
    "ModelRequest": ModelRequest,
    "ModelResponse": ModelResponse,
    "Context": Context,
    "Judgement": Judgement,
}
"""Every published type, by the name a host will look it up under."""


def json_schema(name: str) -> dict[str, JsonValue]:
    schema: dict[str, JsonValue] = TypeAdapter(CONTRACTS[name]).json_schema()
    return schema


def all_schemas() -> dict[str, dict[str, JsonValue]]:
    return {name: json_schema(name) for name in CONTRACTS}


def dump(value: object, as_type: Any) -> str:
    return TypeAdapter(as_type).dump_json(value).decode()


@overload
def load[T](text: str, as_type: type[T]) -> T: ...


@overload
def load(text: str, as_type: Any) -> Any: ...


def load(text: str, as_type: Any) -> Any:
    """Two shapes, because our contracts are of two shapes. A concrete type gives back that type.
    A **union** — `Event`, `Observation`, `Judgement` — satisfies no `type[T]`, and the old
    signature made every `load(text, Event)` in the wire an `arg-type` error that nobody saw,
    because those packages were outside the gate (BUG-007). A union caller annotates what it
    expects, and `TypeAdapter` is what makes the annotation true rather than a hope.
    """
    return TypeAdapter(as_type).validate_json(text)


def round_trip[T](value: T, as_type: Any) -> T:
    """``load(dump(value))`` — equal to ``value`` for every contract, or the build fails."""
    result: T = TypeAdapter(as_type).validate_json(TypeAdapter(as_type).dump_json(value))
    return result
