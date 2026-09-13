"""Bindings become the JSON a component is invoked with.

A binding is either a literal or a reference to what an earlier step produced. A reference to a step
that produced nothing is the agent's mistake, not a crash: `DanglingRef` becomes a `Failed`
observation the agent can see and route around (D7).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pydantic import JsonValue

from shadow_hdk.kernel.composition import Binding, StepId
from shadow_hdk.runtime.errors import DanglingRef


def resolve_inputs(
    bindings: Sequence[Binding], handles: Mapping[StepId, JsonValue]
) -> dict[str, JsonValue]:
    inputs: dict[str, JsonValue] = {}
    for binding in bindings:
        if binding.ref is None:
            inputs[binding.name] = binding.value
            continue
        if binding.ref not in handles:
            raise DanglingRef(
                f"{binding.name!r} binds to step {binding.ref!r}, which has produced nothing"
            )
        inputs[binding.name] = handles[binding.ref]
    return inputs
