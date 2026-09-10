"""The graph's state, and reducers that do not care what order concurrent writes arrive in.

`FanOut` writes from several branches at once, which is why every field is a dict keyed by step id
rather than a list: merging is commutative, so the state does not depend on scheduling.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from pydantic import JsonValue

from shadow_hdk.kernel.composition import StepId


def merge_dicts[V](left: dict[StepId, V], right: dict[StepId, V]) -> dict[StepId, V]:
    return {**left, **right}


def merge_counts(left: dict[StepId, int], right: dict[StepId, int]) -> dict[StepId, int]:
    merged = dict(left)
    for key, value in right.items():
        merged[key] = merged.get(key, 0) + value
    return merged


class RunState(TypedDict):
    handles: Annotated[dict[StepId, JsonValue], merge_dicts]
    observations: Annotated[dict[StepId, JsonValue], merge_dicts]
    """**JSON, not our classes** (D19). A checkpoint is a wire: it crosses a process, a version, and
    into a store the host chose. The types stay ours; what crosses stays plain, and the runtime
    loads observations back at its own edge."""
    iterations: Annotated[dict[StepId, int], merge_counts]


def initial_state() -> RunState:
    return RunState(handles={}, observations={}, iterations={})
