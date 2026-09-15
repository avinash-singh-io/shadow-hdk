"""Effect transaction facts are first-class public events, not private runtime telemetry."""

from __future__ import annotations

from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Composition,
    EffectProfile,
    EffectRecorded,
    Floor,
    Invoke,
    Lease,
    ScopeSet,
)
from shadow_hdk.kernel.contracts import round_trip
from shadow_hdk.runtime import RunOptions, run
from shadow_hdk.runtime.items import items
from shadow_hdk.runtime.testing import make_registration
from tests.runtime.conftest import ports_over

WRITE = make_registration(
    "publish", effects=EffectProfile(writes=ScopeSet.of("workspace"), reversible=False)
)


async def test_a_controlled_effect_records_its_full_public_lifecycle() -> None:
    ports, _ = ports_over([(WRITE, {"published": True})])
    events = [
        event
        async for event in run(
            Composition((Invoke("publish-1", "publish", (Binding("value", value=3),)),)),
            ports,
            options=RunOptions(lease=Lease(Ceiling(5, 60, 10), Floor(0)), run_id="run-1"),
        )
    ]

    records = [event for event in events if isinstance(event, EffectRecorded)]
    assert [event.status for event in records] == ["staged", "authorized", "executing", "receipt"]
    assert records[-1].detail == {"kind": "completed", "output": {"published": True}}
    assert all(round_trip(event, EffectRecorded) == event for event in records)

    (item,) = items(events)
    assert item.effect is not None
    assert item.effect.status == "receipt"
    assert item.effect.detail == records[-1].detail
