"""An assistant message carries the calls it made (BUG-005).

`Message` had `role`, `content` and `tool_call_id` and nothing for an assistant's calls, so the
agent appended the text and dropped them. The second turn's request then held a tool *result* whose
`tool_call_id` referred to a call that appeared nowhere. OpenAI and Anthropic reject that outright;
a lenient provider accepts it and never shows the model which tool it called with what arguments.
Every agent test used `ScriptedModel`, which never looked — so the suite was green and a real
second turn was not.
"""

from __future__ import annotations

from shadow_hdk.adapters.agent import Pattern

from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import Message, ModelResponse, ToolCall
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

ROLE = "You are working on one task, using the tools you are given."


def look(topic: str) -> str:
    """Look a topic up."""
    return f"found {topic}"


async def _two_turns() -> ScriptedModel:
    from shadow_hdk.adapters.agent import AgentComponent
    from shadow_hdk.adapters.basic import AllowAll, CallableComponents

    from shadow_hdk.kernel import Binding, Ceiling, Composition, Floor, Invoke, Lease
    from shadow_hdk.runtime import RunOptions, run

    tools = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    tools.add(look, effects=EffectProfile(reads=EffectProfile().reads))
    agent = AgentComponent(
        pattern=Pattern(name="p", system=ROLE),
        effects=EffectProfile(costs=True),
        at="2026-01-01T00:00:00+00:00",
    )
    model = ScriptedModel(
        [
            ModelResponse("looking", (ToolCall("call-1", "look", {"topic": "lathes"}),)),
            ModelResponse("done", (ToolCall("d1", "done", {"summary": "looked"}),)),
        ]
    )
    ports = Ports(
        model=model,
        components=(tools, agent),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    composition = Composition(
        (Invoke("a1", agent.registration_id, (Binding(name="brief", value="look it up"),)),)
    )
    async for _ in run(
        composition, ports, options=RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0)))
    ):
        pass
    return model


async def test_every_tool_result_has_the_call_that_asked_for_it() -> None:
    """The pairing rule every provider enforces, checked over the whole transcript."""
    model = await _two_turns()
    second = model.requests[1].messages
    called = {call.id for m in second if m.role == "assistant" for call in m.tool_calls}
    answered = {m.tool_call_id for m in second if m.role == "tool"}
    assert answered, "the second turn carried no tool result at all"
    assert answered <= called, f"results {answered - called} answer calls that are in no message"


async def test_the_assistant_message_says_which_tool_and_with_what() -> None:
    model = await _two_turns()
    assistant = [m for m in model.requests[1].messages if m.role == "assistant"]
    assert len(assistant) == 1, assistant
    assert assistant[0].content == "looking"
    assert assistant[0].tool_calls == (ToolCall("call-1", "look", {"topic": "lathes"}),)


async def test_an_answer_with_no_calls_carries_none() -> None:
    """A plain answer is not a call the next turn has to account for."""
    assert Message("assistant", "just words").tool_calls == ()


def test_the_contract_round_trips_the_calls() -> None:
    from shadow_hdk.kernel.contracts import round_trip
    from shadow_hdk.kernel.ports import ModelRequest

    request = ModelRequest(
        (Message("assistant", "looking", tool_calls=(ToolCall("c1", "look", {"topic": "x"}),)),), ()
    )
    assert round_trip(request, ModelRequest) == request
