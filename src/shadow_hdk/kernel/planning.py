"""Whole-plan admission — the judgement no step can make (D107–D109, D111).

A plan is a `Composition` (D107); nothing here adds to the grammar. What this module adds is the
one thing per-step judgement is blind to: the properties of the *whole* — how deep it nests, how
wide it fans out, how many steps it will take, and whether every component it names exists.
`admit` measures a composition against `PlanLimits` and answers with `Admitted` or `PlanRefused`,
and the refusal is data — every mismatch, in a stable order — the way a capability mismatch is
(Phase 31). It is pure and total: the same inputs give the same answer, and a malformed plan is a
refusal, never an exception.

**Limits are what a composition can be measured for.** Depth, fan-out and steps are properties of
the plan's shape; seconds and cents are not — no static reading bounds them — and the lease
already governs both at run time. `PlanLimits` composes by `meet`, the same order effect profiles
have, so a team's mode can only narrow a host's and a child receives the meet of its parent's and
its own (D109). Admission is **not** authorization: an admitted plan's irreversible acts still
obtain their grant at the act (Phase 33, D108).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Literal

from shadow_hdk.kernel.components import Registration
from shadow_hdk.kernel.composition import Await, Composition, FanOut, Invoke, Sequence, Step, Until

PlanAxis = Literal["depth", "fan_out", "steps", "component"]
"""What a mismatch is about — the judgements no step can make. A step's own effects are its own
to be judged at its invocation; admission names them (`PlanAdmitted.asks`, `.refusals`), it does
not pre-empt them."""


@dataclass(frozen=True)
class PlanLimits:
    """How much plan a host, a mode or a parent admits. `None` is unbounded.

    Order-bearing, like an effect profile: `meet` takes the narrower of each field, so limits
    compose without a review and the narrowing proof covers them.
    """

    depth: int | None = None
    fan_out: int | None = None
    steps: int | None = None

    def meet(self, other: PlanLimits) -> PlanLimits:
        return PlanLimits(
            depth=_narrower(self.depth, other.depth),
            fan_out=_narrower(self.fan_out, other.fan_out),
            steps=_narrower(self.steps, other.steps),
        )

    def narrower_than(self, other: PlanLimits) -> bool:
        """Every field of this at most the other's, `None` being no bound at all."""
        return (
            _at_most(self.depth, other.depth)
            and _at_most(self.fan_out, other.fan_out)
            and _at_most(self.steps, other.steps)
        )


UNBOUNDED = PlanLimits()


def _narrower(a: int | None, b: int | None) -> int | None:
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


def _at_most(a: int | None, b: int | None) -> bool:
    if b is None:
        return True
    if a is None:
        return False
    return a <= b


@dataclass(frozen=True)
class PlanMeasure:
    """What a composition is, read off its shape: depth (a top-level leaf is 1), fan_out (the
    widest `FanOut`), steps (leaf steps, an `Until` body counted `max_iterations` times)."""

    depth: int
    fan_out: int
    steps: int
    deepest: str = ""
    """The first leaf, in composition order, at the greatest depth — what a depth mismatch names."""
    widest: str = ""
    """The first `FanOut`, in composition order, at the greatest width."""


@dataclass(frozen=True)
class PlanMismatch:
    """One way a plan does not fit, as data a host or a planner can act on."""

    axis: PlanAxis
    step: str
    required: str
    found: str


@dataclass(frozen=True)
class Admitted:
    plan_digest: str
    authority_digest: str = ""
    limits: PlanLimits = UNBOUNDED


@dataclass(frozen=True)
class PlanRefused:
    mismatches: tuple[PlanMismatch, ...] = ()


def measure(composition: Composition) -> PlanMeasure:
    leaves: list[tuple[str, int, int]] = []  # (id, depth, weight)
    fans: list[tuple[str, int]] = []

    def walk(step: Step, depth: int, weight: int) -> None:
        if isinstance(step, Invoke | Await):
            leaves.append((step.id, depth, weight))
        elif isinstance(step, Sequence):
            for inner in step.steps:
                walk(inner, depth + 1, weight)
        elif isinstance(step, FanOut):
            fans.append((step.id, len(step.steps)))
            for inner in step.steps:
                walk(inner, depth + 1, weight)
        elif isinstance(step, Until):
            walk(step.step, depth + 1, weight * max(step.max_iterations, 1))

    for top in composition.steps:
        walk(top, 1, 1)
    if not leaves:
        return PlanMeasure(depth=0, fan_out=0, steps=0)
    deepest = max(leaves, key=lambda leaf: leaf[1])  # the first at the max: max keeps the first
    widest = max(fans, key=lambda fan: fan[1]) if fans else ("", 1)
    return PlanMeasure(
        depth=deepest[1],
        fan_out=max(widest[1], 1),
        steps=sum(weight for _, _, weight in leaves),
        deepest=deepest[0],
        widest=widest[0],
    )


def leaves_of(composition: Composition) -> tuple[Invoke | Await, ...]:
    """Every leaf step in composition order — what existence and effects are checked over."""
    found: list[Invoke | Await] = []

    def walk(step: Step) -> None:
        if isinstance(step, Invoke | Await):
            found.append(step)
        elif isinstance(step, Sequence | FanOut):
            for inner in step.steps:
                walk(inner)
        elif isinstance(step, Until):
            walk(step.step)

    for top in composition.steps:
        walk(top)
    return tuple(found)


def composition_digest(composition: Composition) -> str:
    """Canonical JSON, sha-256 — the same rule as a staged effect's digest, so a plan admitted here
    is the exact plan that runs."""
    encoded = json.dumps(
        asdict(composition), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def admit(
    composition: Composition,
    registrations: Iterable[Registration | str],
    limits: PlanLimits,
    *,
    authority_digest: str = "",
) -> Admitted | PlanRefused:
    """Measure the whole plan against the limits and the registry — before anything compiles.

    The mismatch list is complete, in the stable order depth, fan_out, steps, then component per
    leaf in composition order. The runtime adds `effect` rows of its own; the kernel cannot judge.
    """
    known = {r.id if isinstance(r, Registration) else str(r) for r in registrations}
    found = measure(composition)
    mismatches: list[PlanMismatch] = []
    if found.steps == 0:
        return PlanRefused((PlanMismatch("steps", "", "at least 1", "0"),))
    if limits.depth is not None and found.depth > limits.depth:
        mismatches.append(PlanMismatch("depth", found.deepest, str(limits.depth), str(found.depth)))
    if limits.fan_out is not None and found.fan_out > limits.fan_out:
        mismatches.append(
            PlanMismatch("fan_out", found.widest, str(limits.fan_out), str(found.fan_out))
        )
    if limits.steps is not None and found.steps > limits.steps:
        mismatches.append(PlanMismatch("steps", "", str(limits.steps), str(found.steps)))
    for leaf in leaves_of(composition):
        if leaf.component not in known:
            mismatches.append(PlanMismatch("component", leaf.id, "registered", leaf.component))
    if mismatches:
        return PlanRefused(tuple(mismatches))
    return Admitted(
        plan_digest=composition_digest(composition),
        authority_digest=authority_digest,
        limits=limits,
    )


__all__ = [
    "UNBOUNDED",
    "Admitted",
    "PlanAxis",
    "PlanLimits",
    "PlanMeasure",
    "PlanMismatch",
    "PlanRefused",
    "admit",
    "composition_digest",
    "leaves_of",
    "measure",
]
