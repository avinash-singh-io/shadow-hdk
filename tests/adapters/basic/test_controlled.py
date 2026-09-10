"""Only `controlled` satisfies consent-before-effect (D30).

`Controlled(inner)` refuses an observed component for any effect that writes or reaches — a thing
we did not gate cannot be consented to before it happens — and admits an observed read, because a
reading is evidence, not an effect. Everything else is the inner policy's. The catalogue judgement
sees posture too, so an observed actuator is *absent* from what the model is offered rather than
shown and then refused.
"""

from __future__ import annotations

import dataclasses

from shadow_hdk.adapters.basic import AllowAll, Controlled
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Event,
    Floor,
    Invoke,
    Lease,
    Observation,
    Observed,
    Refused,
    Registration,
    ScopeSet,
)
from shadow_hdk.kernel.events import Refused as RefusedEvent
from shadow_hdk.kernel.ports import Allow, Context, GovernancePort, Judgement, Refuse
from shadow_hdk.runtime import Ports, RunOptions, current_run, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)
from tests.adapters.contract import GovernancePortContract

WORLD = ScopeSet.of("world")


def observed(registration: Registration) -> Registration:
    return dataclasses.replace(
        registration,
        component=dataclasses.replace(
            registration.component,
            provenance=dataclasses.replace(registration.component.provenance, posture="observed"),
        ),
    )


THERMOMETER = observed(make_registration("thermometer", effects=EffectProfile(reads=WORLD)))
WITNESSED_VALVE = observed(
    make_registration("valve_seen", effects=EffectProfile(writes=WORLD, reversible=False))
)
VALVE = make_registration("valve", effects=EffectProfile(writes=WORLD, reversible=False))
PHONE = observed(make_registration("phone_seen", effects=EffectProfile(reaches=True)))
CATALOGUE = make_registration("catalogue")


async def _ok(_inputs: JsonValue) -> Observation:
    return Completed("done")


class Recording(GovernancePort):
    """Says yes and remembers what it was told."""

    def __init__(self) -> None:
        self.seen: list[Context] = []

    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        self.seen.append(context)
        return Allow()


class NoWrites(GovernancePort):
    async def judge(self, effects: EffectProfile, _context: Context) -> Judgement:
        if effects.writes.names or effects.writes.everything:
            return Refuse("writing is not permitted here")
        return Allow()


async def _run(governance: GovernancePort, *steps: Invoke) -> list[Event]:
    ports = Ports(
        model=ScriptedModel(),
        components=(
            InMemoryComponents(
                [(THERMOMETER, _ok), (WITNESSED_VALVE, _ok), (VALVE, _ok), (PHONE, _ok)]
            ),
        ),
        governance=governance,
        sink=ListSink(),
        clock=FixedClock(),
    )
    return [
        e
        async for e in run(
            Composition(steps),
            ports,
            options=RunOptions(lease=Lease(Ceiling(10, 600, 10), Floor(0))),
        )
    ]


def _outcome(events: list[Event], step: str) -> Observation | str:
    for e in events:
        if isinstance(e, RefusedEvent) and e.step == step:
            return e.reason
        if isinstance(e, Observed) and e.step == step:
            return e.observation
    raise AssertionError(f"{step} was neither refused nor observed")


async def test_an_observed_write_is_refused_naming_the_posture() -> None:
    events = await _run(Controlled(AllowAll()), Invoke("s1", WITNESSED_VALVE.id))
    reason = _outcome(events, "s1")
    assert isinstance(reason, str), reason
    assert "observed" in reason and "valve_seen" in reason, reason


async def test_an_observed_reach_is_refused_too() -> None:
    events = await _run(Controlled(AllowAll()), Invoke("s1", PHONE.id))
    assert isinstance(_outcome(events, "s1"), str)


async def test_an_observed_read_is_admitted() -> None:
    """A reading is evidence, not an effect."""
    events = await _run(Controlled(AllowAll()), Invoke("s1", THERMOMETER.id))
    assert _outcome(events, "s1") == Completed("done")


async def test_a_controlled_write_is_the_inner_policys_to_judge() -> None:
    admitted = await _run(Controlled(AllowAll()), Invoke("s1", VALVE.id))
    assert _outcome(admitted, "s1") == Completed("done")
    refused = await _run(Controlled(NoWrites()), Invoke("s1", VALVE.id))
    assert _outcome(refused, "s1") == "writing is not permitted here"


async def test_governance_is_told_the_posture_and_the_component() -> None:
    recording = Recording()
    await _run(recording, Invoke("s1", THERMOMETER.id), Invoke("s2", VALVE.id))
    by_step = {c.step: c.attributes for c in recording.seen if c.step in {"s1", "s2"}}
    assert by_step["s1"] == {"posture": "observed", "component": "thermometer"}
    assert by_step["s2"] == {"posture": "controlled", "component": "valve"}


async def test_the_catalogue_omits_what_controlled_would_always_refuse() -> None:
    """Absent, not greyed out (Phase 3's rule), so the model is never offered it."""
    shown: list[set[str]] = []

    async def looks(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        shown.append({r.id for r in await context.visible()})
        return Completed(None)

    ports = Ports(
        model=ScriptedModel(),
        components=(
            InMemoryComponents([(THERMOMETER, _ok), (WITNESSED_VALVE, _ok), (VALVE, _ok)]),
            InMemoryComponents([(CATALOGUE, looks)]),
        ),
        governance=Controlled(AllowAll()),
        sink=ListSink(),
        clock=FixedClock(),
    )
    async for _ in run(
        Composition((Invoke("s1", CATALOGUE.id),)),
        ports,
        options=RunOptions(lease=Lease(Ceiling(10, 600, 10), Floor(0))),
    ):
        pass
    assert shown == [{"thermometer", "valve", "catalogue"}], shown


async def test_a_refusal_is_on_the_record_as_a_refusal() -> None:
    """Not a `Failed`: *you may not* and *it broke* invite different next moves."""
    events = await _run(Controlled(AllowAll()), Invoke("s1", WITNESSED_VALVE.id))
    assert not [e for e in events if isinstance(e, Observed) and isinstance(e.observation, Refused)]
    assert [e for e in events if isinstance(e, RefusedEvent)]


class TestControlledIsAGovernancePort(GovernancePortContract):
    """Held to the shared shape as well as its own behaviour (TD-004).

    `Controlled` wraps another governance, so the contract asks the question that matters for a
    wrapper: does it still answer *every* profile shape with a judgement, including the ones its own
    tests never send it?
    """

    def port(self) -> GovernancePort:
        return Controlled(AllowAll())
