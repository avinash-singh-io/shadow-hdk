"""The meter — a ceiling that always beats the floor, and a child carved rather than added.

Unit tests on `LeaseMeter` itself. The same rules are asserted end to end over a real run in
`test_spawn.py` (Group 3); here they are asserted where they are implemented, so a failure names
the arithmetic rather than the graph.
"""

from __future__ import annotations

import pytest

from shadow_hdk.kernel import Ceiling, Floor, Lease, Usage
from shadow_hdk.runtime.session import LeaseMeter
from shadow_hdk.runtime.testing import FixedClock


def meter(
    *, steps: int = 10, wall: int = 600, cost: int | None = 100, floor: int = 0
) -> tuple[LeaseMeter, FixedClock]:
    clock = FixedClock()
    return LeaseMeter(Lease(Ceiling(steps, wall, cost), Floor(floor)), clock), clock


def test_the_step_ceiling_ends_the_run() -> None:
    m, _ = meter(steps=3)
    for _ in range(3):
        assert m.check() is None
        m.charge(Usage(1, 1, 1))
    assert m.check() == "lease_exhausted"
    assert m.steps == 3


def test_the_wall_ceiling_ends_the_run() -> None:
    m, clock = meter(wall=60)
    clock.advance(59)
    assert m.check() is None
    clock.advance(2)
    assert m.check() == "lease_exhausted"


def test_the_cost_ceiling_ends_the_run() -> None:
    m, _ = meter(cost=10)
    m.charge(Usage(100, 100, 6))
    assert m.check() is None
    m.charge(Usage(100, 100, 6))
    assert m.check() == "lease_exhausted"
    assert m.cost_cents == 12


def test_unknown_usage_does_not_charge_zero() -> None:
    """A provider that cannot price a call reports unknown, and the meter says unknown."""
    m, _ = meter(cost=10)
    assert m.cost_is_known
    m.charge(Usage(10, 10, None))
    assert m.steps == 1
    assert not m.cost_is_known
    assert m.cost_cents == 0  # nothing is invented…
    assert m.remaining().ceiling.max_cost_cents is None  # …and nothing is promised


def test_a_child_is_carved_and_the_parent_is_debited() -> None:
    m, _ = meter(steps=10, cost=100)
    m.charge(Usage(1, 1, 20))
    child = m.carve(Ceiling(max_steps=4, max_wall_seconds=600, max_cost_cents=30))
    assert child.ceiling.max_steps == 4
    assert child.ceiling.max_cost_cents == 30
    remaining = m.remaining().ceiling
    assert remaining.max_steps == 10 - 1 - 4
    assert remaining.max_cost_cents == 100 - 20 - 30


def test_a_child_asking_more_than_remains_is_refused() -> None:
    m, _ = meter(steps=5, cost=50)
    m.carve(Ceiling(max_steps=4, max_wall_seconds=600, max_cost_cents=40))
    with pytest.raises(ValueError, match="cannot exceed"):
        m.carve(Ceiling(max_steps=4, max_wall_seconds=600, max_cost_cents=5))


def test_the_ceiling_beats_the_floor_when_they_disagree() -> None:
    m, _ = meter(steps=2, floor=2)
    assert not m.floor_met()
    m.charge(Usage(1, 1, 1))
    assert not m.floor_met()
    m.charge(Usage(1, 1, 1))
    assert m.floor_met()
    assert m.check() == "lease_exhausted"


def test_a_floor_above_its_ceiling_is_refused_at_construction() -> None:
    with pytest.raises(ValueError, match="ceiling always beats the floor"):
        Lease(Ceiling(2, 60), Floor(3))
