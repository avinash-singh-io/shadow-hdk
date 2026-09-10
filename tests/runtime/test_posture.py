"""Every observation carries the posture of the component that produced it (D30).

Stamped by the runtime from the registration — never by the component, whose own opinion of its
posture is exactly what the record must not depend on. `controlled` is *we gated it*; `observed` is
*evidence recorded after something else acted* (`08` §4).
"""

from __future__ import annotations

import dataclasses

from pydantic import JsonValue

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    Event,
    Failed,
    Floor,
    Invoke,
    Lease,
    Observation,
    Observed,
    Registration,
)
from shadow_hdk.kernel.contracts import round_trip
from shadow_hdk.runtime import RunOptions, run
from shadow_hdk.runtime.testing import make_registration
from tests.runtime.conftest import ports_over

LOOK = make_registration("look")


def observed(registration: Registration) -> Registration:
    return dataclasses.replace(
        registration,
        component=dataclasses.replace(
            registration.component,
            provenance=dataclasses.replace(registration.component.provenance, posture="observed"),
        ),
    )


OVERHEARD = observed(make_registration("overheard"))


async def _answers(_inputs: JsonValue) -> Observation:
    return Completed("seen")


async def _events(*steps: Invoke) -> list[Event]:
    ports, _ = ports_over([(LOOK, _answers), (OVERHEARD, _answers)])
    return [
        e
        async for e in run(
            Composition(steps),
            ports,
            options=RunOptions(lease=Lease(Ceiling(5, 600, 10), Floor(0))),
        )
    ]


def _observed(events: list[Event], step: str) -> Observed:
    found = [e for e in events if isinstance(e, Observed) and e.step == step]
    assert len(found) == 1, found
    return found[0]


async def test_an_observed_component_is_observed_on_the_record() -> None:
    events = await _events(Invoke("s1", LOOK.id), Invoke("s2", OVERHEARD.id))
    assert _observed(events, "s1").posture == "controlled"
    assert _observed(events, "s2").posture == "observed"


async def test_a_step_that_failed_before_any_component_ran_is_controlled() -> None:
    """Nothing was invoked; the runtime refused it, and refusing is control."""
    events = await _events(Invoke("s1", "no-such-component"))
    missing = _observed(events, "s1")
    assert isinstance(missing.observation, Failed)
    assert missing.posture == "controlled"


def test_the_posture_round_trips_and_defaults_to_controlled() -> None:
    event = Observed(
        run_id="r", seq=1, at="", step="s", observation=Completed(1), posture="observed"
    )
    assert round_trip(event, Event) == event
    assert (
        Observed(run_id="r", seq=1, at="", step="s", observation=Completed(1)).posture
        == "controlled"
    )
