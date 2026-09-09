"""The same inputs twice produce the same stream, byte for byte.

This is what makes a replay differ cost $0 (10 §5 R3) and what makes a regression in the loop
distinguishable from a change in a model's mood.
"""

from __future__ import annotations

from shadow_hdk.kernel import (
    Ceiling,
    Composition,
    Event,
    FanOut,
    Floor,
    Invoke,
    Lease,
    Sequence,
)
from shadow_hdk.kernel.contracts import dump
from shadow_hdk.runtime import RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, make_registration
from tests.runtime.conftest import ports_over

REG = make_registration("step")


async def _stream(composition: Composition) -> list[str]:
    ports, _ = ports_over([(REG, "ok")], clock=FixedClock())
    return [
        dump(event, Event)
        async for event in run(
            composition, ports, options=RunOptions(lease=Lease(Ceiling(50, 3600, 100), Floor(0)))
        )
    ]


async def test_a_sequence_replays_identically() -> None:
    shape = Composition((Sequence("seq", tuple(Invoke(f"s{i}", REG.id) for i in range(3))),))
    assert await _stream(shape) == await _stream(shape)


async def test_a_fan_out_replays_identically_by_step_id() -> None:
    shape = Composition((FanOut("fan", tuple(Invoke(f"c{i}", REG.id) for i in range(3))),))
    first, second = await _stream(shape), await _stream(shape)
    assert sorted(first) == sorted(second)
    assert first[0] == second[0] and first[-1] == second[-1]
