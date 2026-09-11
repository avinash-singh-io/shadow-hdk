"""The projection reaches a host over the wire, already folded (D46).

A host in another language should not have to port the fold to render agent steps. So the runtime
side folds as it streams and sends each closed step as a `step` notification beside the `event`
ones — the same fold, the same events, one path. A host that wants both the record and the steps
gets both from one session.

Parity with in-process is held by construction rather than by two implementations: `Fold` is the
one used by `steps()` and `run_steps()`; the wire calls it.
"""

from __future__ import annotations

import anyio
from shadow_hdk.adapters.basic import AllowAll
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Event,
    Floor,
    Invoke,
    Lease,
    Observation,
)
from shadow_hdk.runtime import Ports, RunOptions, current_run
from shadow_hdk.runtime.steps import Step
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)
from shadow_hdk.wire.protocol import STEP
from shadow_hdk.wire.sides import HostSide, loopback
from tests.wire.test_loopback import LOOK, _look

THINKS = make_registration(
    "thinks", effects=EffectProfile(costs=True), description="Thinks, then answers."
)


async def _thinks(_inputs: JsonValue) -> Observation:
    """A component that puts a thought on the record before it answers — the same door the agent
    adapter uses, exercised without the agent because the agent cannot yet run over the wire
    (Phase 23: `visible()` does not cross)."""
    context = current_run()
    assert context is not None
    thought = _inputs.get("thought", "") if isinstance(_inputs, dict) else ""
    await context.reasoned(str(thought or ""))
    return Completed({"answer": 12})


async def over_a_loopback(reasoning: str = "") -> tuple[HostSide, list[Event]]:
    """Two steps — one that thinks, one that looks — driven over a loopback wire."""
    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(LOOK, _look), (THINKS, _thinks)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    plan = Composition(
        (
            Invoke("lead", THINKS.id, (Binding("thought", value=reasoning),)),
            Invoke("look", LOOK.id, ()),
        )
    )
    async with loopback(ports) as (host, _runtime):
        await host.initialize()
        with anyio.fail_after(60):
            await host.run(plan, RunOptions(lease=Lease(Ceiling(20, 600, 100), Floor(0))))
        return host, list(host.events)


async def test_steps_arrive_folded_beside_the_events() -> None:
    host, events = await over_a_loopback()

    assert host.steps, "no step notification crossed the wire"
    assert all(isinstance(s, Step) for s in host.steps)
    assert STEP == "step"


async def test_the_steps_that_crossed_are_the_steps_the_events_fold_to() -> None:
    """Parity, stated as a property: fold the events that crossed, get the steps that crossed."""
    from shadow_hdk.runtime.steps import steps

    host, events = await over_a_loopback()

    assert [s.step for s in host.steps] == [s.step for s in steps(events)]
    assert [s.outcome for s in host.steps] == [s.outcome for s in steps(events)]


async def test_a_thought_crosses_the_wire_inside_its_step() -> None:
    """The twelfth kind, end to end: `Reasoned` is in the union, so it crosses as an event — and
    the step it folds into carries it."""
    from shadow_hdk.kernel import Reasoned

    host, events = await over_a_loopback(reasoning="the handbook will know")

    assert any(isinstance(e, Reasoned) for e in events), "Reasoned did not cross as an event"
    assert any("handbook" in s.reasoning for s in host.steps), "the step lost its reasoning"
