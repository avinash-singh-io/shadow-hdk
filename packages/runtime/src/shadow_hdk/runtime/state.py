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


SUMS = ("steps", "cost_cents", "unpriced")
"""Counters: what every step adds to."""

MARKS = ("elapsed_seconds", "seq")
"""High-water marks: what the furthest-along branch reached."""


def merge_spent(left: dict[str, float], right: dict[str, float]) -> dict[str, float]:
    """Add the counters, take the highest mark. Commutative and associative, because a `FanOut`
    writes from several branches at once and the total must not depend on which arrived first."""
    merged: dict[str, float] = {name: left.get(name, 0) + right.get(name, 0) for name in SUMS}
    for name in MARKS:
        merged[name] = max(left.get(name, 0), right.get(name, 0))
    return merged


class RunState(TypedDict):
    handles: Annotated[dict[StepId, JsonValue], merge_dicts]
    observations: Annotated[dict[StepId, JsonValue], merge_dicts]
    """**JSON, not our classes** (D19). A checkpoint is a wire: it crosses a process, a version, and
    into a store the host chose. The types stay ours; what crosses stays plain, and the runtime
    loads observations back at its own edge."""
    iterations: Annotated[dict[StepId, int], merge_counts]
    children: Annotated[dict[StepId, JsonValue], merge_dicts]
    """What this run is holding, so a parent that parks comes back holding it still (D37).
    A handle mapped to `None` is one that was released — kept as a headstone so the record merges
    the same in any order, which is what a `FanOut` requires."""
    spent: Annotated[dict[str, float], merge_spent]
    """What the run has spent, in the only durable place the runtime has (D33). `run` and `resume`
    each build a fresh meter and emitter, so without this a lease of three steps admitted five
    across an Ask — the ordinary way a governed run pauses. JSON, like everything that crosses a
    checkpoint (D19)."""


def no_spend() -> dict[str, float]:
    return {"steps": 0, "cost_cents": 0, "unpriced": 0, "elapsed_seconds": 0.0, "seq": 0}


def initial_state() -> RunState:
    return RunState(handles={}, observations={}, iterations={}, children={}, spent=no_spend())
