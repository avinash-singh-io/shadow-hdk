"""The meter — a ceiling that always beats the floor, and a child carved rather than added.

Unit tests on `LeaseMeter` itself. The same rules are asserted end to end over a real run in
`test_spawn.py` (Group 3); here they are asserted where they are implemented, so a failure names
the arithmetic rather than the graph.
"""

from __future__ import annotations

import pytest
from pydantic import JsonValue

from shadow_hdk.kernel import Ceiling, Completed, Floor, Invoke, Lease, Usage
from shadow_hdk.runtime.session import LeaseMeter
from shadow_hdk.runtime.state import initial_state
from shadow_hdk.runtime.testing import FixedClock, make_registration
from tests.runtime.conftest import executor_over


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


def test_a_child_s_reservation_is_released_when_it_ends() -> None:
    """A carve is a *reservation*, not a spend. An agent that runs twelve turns, each a child that
    asks for five steps and uses one, must not have drained sixty steps from its parent."""
    m, _ = meter(steps=20, cost=200)
    reserved = Ceiling(max_steps=5, max_wall_seconds=600, max_cost_cents=50)
    for _ in range(3):
        m.carve(reserved)
        m.settle(reserved, steps=1, cost_cents=10, cost_known=True)
    assert m.steps == 3
    assert m.cost_cents == 30
    assert m.remaining().ceiling.max_steps == 17
    assert m.remaining().ceiling.max_cost_cents == 170


def test_settling_an_unpriced_child_makes_the_parent_admit_it_cannot_total() -> None:
    m, _ = meter(steps=20, cost=200)
    reserved = Ceiling(max_steps=5, max_wall_seconds=600, max_cost_cents=50)
    m.carve(reserved)
    m.settle(reserved, steps=2, cost_cents=0, cost_known=False)
    assert not m.cost_is_known
    assert m.remaining().ceiling.max_cost_cents is None


def test_a_reservation_still_bites_while_the_child_is_running() -> None:
    m, _ = meter(steps=6)
    m.carve(Ceiling(max_steps=5, max_wall_seconds=600, max_cost_cents=10))
    assert m.remaining().ceiling.max_steps == 1


async def test_what_a_step_cost_reaches_the_meter_from_the_observation() -> None:
    """A step is counted when it *begins* — so a step in flight counts against the ceiling and
    concurrent children cannot collectively overrun it. Its **cost** can only be known when it
    ends, so the two are charged separately, and this asserts the second one arrives at all.
    """
    reg = make_registration("thinks")

    async def priced(_inputs: JsonValue) -> Completed:
        return Completed({"usage": {"input_tokens": 10, "output_tokens": 5, "cost_cents": 7}})

    ex, _, _ = executor_over([(reg, priced)], lease=Lease(Ceiling(10, 600, 100), Floor(0)))
    await ex.invoke(Invoke("s1", reg.id), initial_state())
    assert ex.session.meter.steps == 1
    assert ex.session.meter.cost_cents == 7, "the model's price never reached the meter"


async def test_a_step_whose_price_is_unknown_is_not_charged_as_free() -> None:
    reg = make_registration("thinks")

    async def unpriced(_inputs: JsonValue) -> Completed:
        return Completed({"usage": {"input_tokens": 10, "output_tokens": 5, "cost_cents": None}})

    ex, _, _ = executor_over([(reg, unpriced)], lease=Lease(Ceiling(10, 600, 100), Floor(0)))
    await ex.invoke(Invoke("s1", reg.id), initial_state())
    assert not ex.session.meter.cost_is_known
