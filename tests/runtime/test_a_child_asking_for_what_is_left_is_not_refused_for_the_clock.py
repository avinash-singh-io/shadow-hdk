"""A child that asks for the parent's remaining wall-clock is not refused for it (BUG-022).

`remaining()` truncates wall seconds to an integer, and a caller that read it and then reserved a
moment later crossed a second boundary in between — the number it asked for was one more than the
number left, and the carve refused the child as exceeding its parent's ceiling. Measured in the
studio, on the first question a person answered there: the provider was told its call had
failed. Wall-clock is a clock, not a budget a child can overdraw by asking: a reservation clamps it
to what is left. Steps and money stay strict — asking for more of those than remain is an error.
"""

from __future__ import annotations

import pytest

from shadow_hdk.kernel import Ceiling, Floor, Lease
from shadow_hdk.runtime.session import LeaseMeter
from shadow_hdk.runtime.testing import FixedClock


def _meter(clock: FixedClock, wall: int = 10) -> LeaseMeter:
    return LeaseMeter(Lease(Ceiling(10, wall, 100), Floor(0)), clock)


def test_a_reservation_read_just_before_a_second_boundary_still_carves() -> None:
    clock = FixedClock()
    meter = _meter(clock)
    clock.advance(0.9)
    asked = meter.remaining().ceiling  # says 9 seconds left (10 - 0.9, truncated)
    clock.advance(0.2)  # a moment later: 8 left

    child = meter.carve(Ceiling(asked.max_steps, asked.max_wall_seconds, asked.max_cost_cents))

    assert child.ceiling.max_wall_seconds <= 8, "clamped to what is left, not refused"


def test_steps_and_money_are_still_strict() -> None:
    meter = _meter(FixedClock())
    with pytest.raises(ValueError):
        meter.carve(Ceiling(11, 1, 1))
    with pytest.raises(ValueError):
        meter.carve(Ceiling(1, 1, 101))
