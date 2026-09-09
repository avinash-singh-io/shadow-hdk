"""Leases carry a ceiling and a floor (09 §7).

Maxima on money, steps and wall time, and a minimum effort before the agent may declare something
unfinishable — a model trained to be agreeable gives up early, and a floor is the honest counter.
The ceiling always beats the floor; the ceiling is someone's money.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Ceiling:
    max_steps: int
    max_wall_seconds: int
    max_cost_cents: int | None = None
    """``None`` is *unmetered*, never *free*: a host that cannot price a step must say so."""

    def within(self, other: Ceiling) -> bool:
        cost_ok = other.max_cost_cents is None or (
            self.max_cost_cents is not None and self.max_cost_cents <= other.max_cost_cents
        )
        return (
            self.max_steps <= other.max_steps
            and self.max_wall_seconds <= other.max_wall_seconds
            and cost_ok
        )


@dataclass(frozen=True)
class Floor:
    min_steps: int = 0


@dataclass(frozen=True)
class Lease:
    ceiling: Ceiling
    floor: Floor = Floor()

    def __post_init__(self) -> None:
        if self.floor.min_steps > self.ceiling.max_steps:
            raise ValueError(
                f"floor {self.floor.min_steps} exceeds ceiling {self.ceiling.max_steps}: "
                "the ceiling always beats the floor"
            )

    def carve(self, child: Ceiling) -> tuple[Lease, Lease]:
        """A child's lease is carved from the parent's, so fan-out changes shape, never ceiling.

        Returns ``(child_lease, remaining_parent_lease)``. Refuses a child that would exceed
        what the parent has left. The child inherits the floor, clamped to its own ceiling.
        """
        if not child.within(self.ceiling):
            raise ValueError("a child lease cannot exceed its parent's ceiling")
        remaining_cost = (
            None
            if self.ceiling.max_cost_cents is None
            else self.ceiling.max_cost_cents - (child.max_cost_cents or 0)
        )
        remaining = Ceiling(
            max_steps=self.ceiling.max_steps - child.max_steps,
            max_wall_seconds=self.ceiling.max_wall_seconds,
            max_cost_cents=remaining_cost,
        )
        child_floor = Floor(min(self.floor.min_steps, child.max_steps))
        parent_floor = Floor(min(self.floor.min_steps, remaining.max_steps))
        return Lease(child, child_floor), Lease(remaining, parent_floor)
