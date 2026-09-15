"""The kernel's contracts are published as JSON Schema from day one (09 §3b).

A TypeScript host reads the same schemas this code is generated from. ``round_trip`` is the CI
proof that nothing a port carries can be a callable, a live object, or anything else that cannot
cross a wire.
"""

from __future__ import annotations

from typing import Any, overload

from pydantic import JsonValue, TypeAdapter

from shadow_hdk.kernel.authority import (
    AuthoritySnapshot,
    EffectAuthorization,
    EffectEntry,
    StagedEffect,
)
from shadow_hdk.kernel.capabilities import (
    Compatibility,
    EnvironmentCapabilities,
    ExecutionRequirements,
    ExecutionSelection,
    ProviderCapabilities,
)
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
from shadow_hdk.kernel.providers import Provider

CONTRACTS: dict[str, Any] = {
    "AuthoritySnapshot": AuthoritySnapshot,
    "StagedEffect": StagedEffect,
    "EffectAuthorization": EffectAuthorization,
    "EffectEntry": EffectEntry,
    "ProviderCapabilities": ProviderCapabilities,
    "EnvironmentCapabilities": EnvironmentCapabilities,
    "ExecutionRequirements": ExecutionRequirements,
    "ExecutionSelection": ExecutionSelection,
    "Compatibility": Compatibility,
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
    "Provider": Provider,
}
"""Every published type, by the name a host will look it up under."""


_ADAPTERS: dict[Any, TypeAdapter[Any]] = {}
"""One adapter per type, for the life of the process."""


def adapter_for(as_type: Any) -> TypeAdapter[Any]:
    """The `TypeAdapter` for a type, built once (BUG-016).

    Constructing one walks the whole annotation and builds a core schema — for `Observation`, a
    six-arm discriminated union, thousands of nodes. It is a **pure function of the type**: nothing
    about it varies per call. Building it per call cost **0.743 ms**, and D19 means every step of
    every run dumps its observation through here, so a hundred-step run built 101 adapters and
    spent 57% of the runtime's entire per-step overhead rebuilding the same schema.

    **Unbounded on purpose, and it is not TD-005's kind of growth.** The key is a *type*, and a
    program holds finitely many of those — they are created by module import, not by traffic. An
    eviction policy here would throw away exactly the object that is expensive to rebuild, on a set
    that cannot grow with load.

    An unhashable annotation cannot be a key, and is built fresh rather than refused. A shape like
    `list[dict[str, int]]` is an ordinary thing to ask of a kernel whose job is crossing wires, and
    a cache that turned a working call into a `TypeError` would be worse than the bug it fixes.
    """
    try:
        cached = _ADAPTERS.get(as_type)
    except TypeError:
        return TypeAdapter(as_type)
    if cached is None:
        cached = _ADAPTERS[as_type] = TypeAdapter(as_type)
    return cached


def json_schema(name: str) -> dict[str, JsonValue]:
    schema: dict[str, JsonValue] = adapter_for(CONTRACTS[name]).json_schema()
    return schema


def all_schemas() -> dict[str, dict[str, JsonValue]]:
    return {name: json_schema(name) for name in CONTRACTS}


def dump(value: object, as_type: Any) -> str:
    return adapter_for(as_type).dump_json(value).decode()


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
    return adapter_for(as_type).validate_json(text)


def round_trip[T](value: T, as_type: Any) -> T:
    """``load(dump(value))`` — equal to ``value`` for every contract, or the build fails."""
    adapter = adapter_for(as_type)
    result: T = adapter.validate_json(adapter.dump_json(value))
    return result
