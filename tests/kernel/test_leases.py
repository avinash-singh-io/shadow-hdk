from __future__ import annotations

import pytest

from shadow_hdk.kernel.leases import Ceiling, Floor, Lease


def test_the_ceiling_always_beats_the_floor() -> None:
    with pytest.raises(ValueError, match="ceiling always beats the floor"):
        Lease(Ceiling(max_steps=3, max_wall_seconds=60), Floor(min_steps=4))


def test_a_child_is_carved_from_the_parent_never_added_to_it() -> None:
    parent = Lease(Ceiling(max_steps=10, max_wall_seconds=600, max_cost_cents=100), Floor(2))
    child, remaining = parent.carve(Ceiling(max_steps=4, max_wall_seconds=600, max_cost_cents=30))
    assert child.ceiling.max_steps == 4 and child.floor.min_steps == 2
    assert remaining.ceiling.max_steps == 6 and remaining.ceiling.max_cost_cents == 70
    with pytest.raises(ValueError, match="cannot exceed"):
        remaining.carve(Ceiling(max_steps=7, max_wall_seconds=600, max_cost_cents=10))


def test_an_unmetered_parent_cannot_hand_out_a_metered_ceiling_it_does_not_have() -> None:
    parent = Lease(Ceiling(max_steps=10, max_wall_seconds=600))
    child, _ = parent.carve(Ceiling(max_steps=1, max_wall_seconds=60))
    assert child.ceiling.max_cost_cents is None
    with pytest.raises(ValueError):
        Lease(Ceiling(max_steps=10, max_wall_seconds=600, max_cost_cents=5)).carve(
            Ceiling(max_steps=1, max_wall_seconds=60)
        )
