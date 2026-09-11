"""A component puts thinking on the record the way it puts a proposal there (D45).

`RunContext.reasoned(text)` is the door — beside `propose` and `spawn` — and the agent adapter is
its first caller: after every model turn that carried reasoning, before the tool calls that
reasoning led to, so a reader sees *why* before *what*.

Empty text emits nothing. The rule is `Spent`'s: a kind that appears when there is nothing to say
is a kind readers learn to skip.
"""

from __future__ import annotations

from shadow_hdk.adapters.agent import AgentComponent, Pattern
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
    Invoked,
    Lease,
    Observation,
    Reasoned,
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

LOOK = make_registration("look", effects=EffectProfile(), description="Look something up.")
ROLE = Pattern("single", "Answer.", tool_names=frozenset({"look"}), max_turns=4)


async def _look(_inputs: JsonValue) -> Observation:
    return Completed({"found": 1})


async def a_run(*script: ModelResponse) -> list[Event]:
    agent = AgentComponent(pattern=ROLE, effects=EffectProfile(costs=True), name="agent", at="t")
    ports = Ports(
        model=ScriptedModel(list(script)),
        components=(InMemoryComponents([(LOOK, _look)]), agent),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    plan = Composition((Invoke("agent", "agent", (Binding("brief", value="go"),)),))
    return [
        e
        async for e in run(
            plan, ports, options=RunOptions(lease=Lease(Ceiling(20, 600, 100), Floor(0)))
        )
    ]


def says(text: str = "", *, reasoning: str = "", calls: tuple[ToolCall, ...] = ()) -> ModelResponse:
    return ModelResponse(text=text, tool_calls=calls, usage=Usage(10, 5, 1), reasoning=reasoning)


async def test_a_models_reasoning_lands_on_the_stream() -> None:
    events = await a_run(
        says(reasoning="the handbook will know", calls=(ToolCall("c1", "look", {}),)),
        says("12kg", reasoning="that settles it"),
    )
    thoughts = [e for e in events if isinstance(e, Reasoned)]

    assert [t.text for t in thoughts] == ["the handbook will know", "that settles it"]


async def test_thinking_comes_before_the_call_it_led_to() -> None:
    """A reader sees why before what: the `Reasoned` precedes the `Invoked` for the tool the
    reasoning reached for."""
    events = await a_run(
        says(reasoning="check the handbook", calls=(ToolCall("c1", "look", {}),)),
        says("done"),
    )
    kinds = [e.kind for e in events]
    thought = kinds.index("reasoned")
    looked = next(
        i for i, e in enumerate(events) if isinstance(e, Invoked) and e.component == "look"
    )

    assert thought < looked, kinds


async def test_a_model_that_did_not_reason_emits_nothing() -> None:
    """`Spent`'s rule: nothing to say, no event."""
    events = await a_run(says("12kg"))

    assert not [e for e in events if isinstance(e, Reasoned)]


async def test_the_thought_is_stamped_with_the_agents_step() -> None:
    """So a projection can fold it under the step that was thinking, not the one that ran the
    tool it led to."""
    events = await a_run(says("x", reasoning="hm"))
    thought = next(e for e in events if isinstance(e, Reasoned))

    assert thought.step == "agent"
    assert thought.run_id == events[0].run_id
