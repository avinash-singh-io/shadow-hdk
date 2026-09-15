"""Transaction facts and folded transaction state cross the public wire unchanged."""

from __future__ import annotations

from shadow_hdk.kernel import (
    EffectRecorded,
)
from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.kernel.events import Event
from shadow_hdk.wire.schemas import published


def test_effect_transaction_facts_cross_the_wire_and_publish_unknown() -> None:
    event = EffectRecorded(
        run_id="run-1",
        seq=3,
        at="2026-09-15T12:00:00+00:00",
        step="publish-1",
        attempt_id="run-1/publish-1",
        status="unknown",
        stage_digest="a" * 64,
        detail={"reason": "outcome_unknown_after_execution_started"},
        recorded_at="2026-09-15T12:00:00+00:00",
    )
    crossed = load(dump(event, Event), Event)
    assert crossed == event
    assert "effect_recorded" in str(published()["Event"])
