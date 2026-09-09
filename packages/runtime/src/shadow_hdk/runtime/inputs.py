"""Bindings become JSON: a literal passes through, a reference reads an earlier step's output.

A reference to a step that produced nothing is the agent's mistake, not a crash — the caller turns
`DanglingRef` into a `Failed` observation the agent can see and route around (D7).
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import JsonValue

from shadow_hdk.kernel.composition import Binding, StepId
from shadow_hdk.runtime.errors import DanglingRef


def resolve_inputs(bindings: tuple[Binding, ...], handles: Mapping[StepId, JsonValue]) -> JsonValue:
    resolved: dict[str, JsonValue] = {}
    for binding in bindings:
        if binding.ref is None:
            resolved[binding.name] = binding.value
            continue
        if binding.ref not in handles:
            raise DanglingRef(
                f"{binding.name!r} refers to {binding.ref!r}, which has produced nothing"
            )
        resolved[binding.name] = handles[binding.ref]
    return resolved
