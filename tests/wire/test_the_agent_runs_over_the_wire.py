"""The agent adapter runs with the host on the other side of a socket (D51).

Phase 21 found it could not: four things it needs from its context did not cross — `visible()`,
`floor_met()`, `spawn_options()` and `children`. They cross now, the way `propose` and `reasoned`
already did, for the same reason: there is one registry, one meter and one record, and they are on
the runtime's side.

The claim is parity: a `single` pattern driven over the loopback wire produces the events it
produces in-process — `Reasoning` and `Invoked` and `Observed` in the same order, the tool called
once, the answer the same — and an orchestrator that spawns a helper gets the helper's events back
with the parent's record intact.
"""

from __future__ import annotations

import anyio
from pydantic import JsonValue

from shadow_hdk.adapters.agent import AgentComponent, Pattern
from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Event,
    Floor,
    Invoke,
    Invoked,
    Lease,
    Observation,
    Reasoning,
)
from shadow_hdk.kernel.ports import ModelResponse, ToolCall, Usage
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)
from shadow_hdk.wire.sides import loopback

LOOK = make_registration("look", effects=EffectProfile(), description="Look something up.")
SINGLE = Pattern("single", "Answer.", tool_names=frozenset({"look"}), max_turns=4)


async def _look(_inputs: JsonValue) -> Observation:
    return Completed({"found": 12})


def a_script() -> list[ModelResponse]:
    return [
        ModelResponse(
            tool_calls=(ToolCall("c1", "look", {}),),
            usage=Usage(10, 5, 1),
            reasoning="the handbook will know",
        ),
        ModelResponse(text="12kg", usage=Usage(10, 5, 1)),
    ]


def ports_for(script: list[ModelResponse], pattern: Pattern = SINGLE) -> Ports:
    agent = AgentComponent(pattern=pattern, effects=EffectProfile(costs=True), name="agent", at="t")
    return Ports(
        model=ScriptedModel(script),
        components=(InMemoryComponents([(LOOK, _look)]), agent),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


PLAN = Composition((Invoke("lead", "agent", (Binding("brief", value="go"),)),))
OPTIONS = RunOptions(lease=Lease(Ceiling(20, 600, 100), Floor(0)), run_id="r")


def shape(events: list[Event]) -> list[tuple[str, str]]:
    return [(e.kind, getattr(e, "step", "")) for e in events]


async def test_a_single_agent_runs_over_the_wire_and_produces_the_same_events() -> None:
    """The bug this closes: `visible()` did not cross, so the agent's first move — building its
    catalogue — failed the step before any model was asked."""
    here = [e async for e in run(PLAN, ports_for(a_script()), options=OPTIONS)]
    async with loopback(ports_for(a_script())) as (host, _runtime):
        await host.initialize()
        with anyio.fail_after(60):
            await host.run(PLAN, OPTIONS)
        there = list(host.events)

    assert shape(there) == shape(here), (shape(here), shape(there))
    assert [e.text for e in there if isinstance(e, Reasoning)] == ["the handbook will know"]
    assert [e.component for e in there if isinstance(e, Invoked)] == ["agent", "look"]


async def test_the_tool_the_agent_reached_for_ran_once_on_the_host() -> None:
    """The component crosses to the host like any other; what must not happen is a second, local
    call on the runtime side or none at all."""
    calls: list[JsonValue] = []

    async def counting(inputs: JsonValue) -> Observation:
        calls.append(inputs)
        return Completed({"found": 12})

    agent = AgentComponent(pattern=SINGLE, effects=EffectProfile(costs=True), name="agent", at="t")
    ports = Ports(
        model=ScriptedModel(a_script()),
        components=(InMemoryComponents([(LOOK, counting)]), agent),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    async with loopback(ports) as (host, _runtime):
        await host.initialize()
        with anyio.fail_after(60):
            await host.run(PLAN, OPTIONS)

    assert len(calls) == 1


async def test_the_floor_and_the_spawn_options_are_the_runtimes_answers() -> None:
    """`done` before the floor is met gets one nudge — a judgement the meter makes, and the meter
    is on the runtime's side. Over the wire the agent asks and is told."""
    nudging = Pattern("single", "Answer.", tool_names=frozenset({"look"}), max_turns=4)
    script = [
        ModelResponse(tool_calls=(ToolCall("c1", "done", {"summary": "nothing"}),)),
        ModelResponse(tool_calls=(ToolCall("c2", "done", {"summary": "still nothing"}),)),
    ]
    floor_of_one = RunOptions(lease=Lease(Ceiling(20, 600, 100), Floor(1)), run_id="r")

    here = [e async for e in run(PLAN, ports_for(script, nudging), options=floor_of_one)]
    async with loopback(ports_for(script, nudging)) as (host, _runtime):
        await host.initialize()
        with anyio.fail_after(60):
            await host.run(PLAN, floor_of_one)
        there = list(host.events)

    assert shape(there) == shape(here)
