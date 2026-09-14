"""The agent streams (Phase 30 group 1, D89).

Every runtime in the field streams the model's words as they are written; the kit's agent
called `complete` and a product streamed underneath it. Now the agent reads the model through
`ModelPort.stream`: each delta of text and of thinking is activity beside the record (D63) as
it arrives, the turn's response is assembled from the chunks — tool calls, usage, reasoning
included — and the record is the same as a completed turn's: the reasoning once, the answer
once. A model that does not stream (the port's default `stream` calls `complete`) still works,
in one piece.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from shadow_hdk.adapters.agent import AgentComponent, Pattern
from shadow_hdk.adapters.basic import AllowAll, CallableComponents
from shadow_hdk.kernel import (
    Activity,
    Binding,
    Ceiling,
    Completed,
    Composition,
    Event,
    Floor,
    Invoke,
    Lease,
    Observed,
    ScopeSet,
)
from shadow_hdk.kernel.activity import TEXT, THINKING
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import Reasoning, UsageReported
from shadow_hdk.kernel.ports import (
    ModelChunk,
    ModelRequest,
    ModelResponse,
    ObserverPort,
    ToolCall,
    Usage,
)
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListSink

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")


def look(topic: str) -> str:
    """Look a topic up."""
    return f"found {topic}"


class Watching(ObserverPort):
    def __init__(self) -> None:
        self.events: list[Event] = []
        self.activity: list[Activity] = []

    async def on(self, event: Event) -> None:
        self.events.append(event)

    async def on_activity(self, activity: Activity) -> None:
        self.activity.append(activity)


class Streams:
    """A model that answers in pieces: thinking first, then words, the tool call and the usage
    on the last chunk — the way every provider's stream arrives. `complete` is never called."""

    def __init__(self, turns: list[list[ModelChunk]]) -> None:
        self.turns = list(turns)
        self.completed = 0

    async def complete(self, _request: ModelRequest) -> ModelResponse:
        self.completed += 1
        raise AssertionError("the agent should stream, not complete")

    async def stream(self, _request: ModelRequest) -> AsyncIterator[ModelChunk]:
        for chunk in self.turns.pop(0):
            yield chunk


class Completes:
    """A model with no stream of its own: the port's default streams `complete` in one piece."""

    def __init__(self, responses: list[ModelResponse]) -> None:
        self.responses = list(responses)

    async def complete(self, _request: ModelRequest) -> ModelResponse:
        return self.responses.pop(0)


async def drive(model: Any, watching: Watching) -> list[Event]:
    tools = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    tools.add(look, effects=EffectProfile(reads=WORKSPACE))
    agent = AgentComponent(
        pattern=Pattern(name="p", system="work"),
        effects=EffectProfile(costs=True),
        at="2026-01-01T00:00:00+00:00",
    )
    ports = Ports(
        model=model,
        components=(tools, agent),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
        observer=watching,
    )
    return [
        event
        async for event in run(
            Composition(
                (Invoke("a1", agent.registration_id, (Binding(name="brief", value="go"),)),)
            ),
            ports,
            options=RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0))),
        )
    ]


def _answer(events: list[Event]) -> dict[str, Any]:
    observed = [e for e in events if isinstance(e, Observed) and e.step == "a1"]
    assert observed and isinstance(observed[-1].observation, Completed)
    output = observed[-1].observation.output
    assert isinstance(output, dict)
    return output


async def test_words_and_thinking_are_activity_as_they_arrive_and_the_record_is_whole() -> None:
    watching = Watching()
    model = Streams(
        [
            [
                ModelChunk(reasoning="I should "),
                ModelChunk(reasoning="look."),
                ModelChunk(text="Looking"),
                ModelChunk(
                    tool_calls=(ToolCall("t1", "look", {"topic": "x"}),),
                    usage=Usage(input_tokens=10, output_tokens=5, cost_cents=1),
                    done=True,
                ),
            ],
            [
                ModelChunk(text="Found "),
                ModelChunk(text="it."),
                ModelChunk(usage=Usage(input_tokens=20, output_tokens=3, cost_cents=1), done=True),
            ],
        ]
    )
    events = await drive(model, watching)
    assert model.completed == 0
    assert _answer(events)["text"] == "Found it."
    live = [(a.kind, a.text) for a in watching.activity if a.kind in (TEXT, THINKING)]
    assert live == [
        (THINKING, "I should "),
        (THINKING, "look."),
        (TEXT, "Looking"),
        (TEXT, "Found "),
        (TEXT, "it."),
    ]
    assert all(a.step == "a1" for a in watching.activity if a.kind in (TEXT, THINKING))
    thought = [e.text for e in events if isinstance(e, Reasoning)]
    assert thought == ["I should look."], "the reasoning once, whole, on the record"
    charged = [e for e in events if isinstance(e, UsageReported)]
    assert sum((e.usage.cost_cents or 0) for e in charged) == 2
    looked = [
        e for e in events if isinstance(e, Observed) and e.observation == Completed("found x")
    ]
    assert looked, "the tool call assembled from the stream was carried out"


async def test_a_model_that_only_completes_still_works_in_one_piece() -> None:
    watching = Watching()
    model = Completes([ModelResponse(text="all at once", reasoning="quick")])
    events = await drive(model, watching)
    assert _answer(events)["text"] == "all at once"
    live = [(a.kind, a.text) for a in watching.activity if a.kind in (TEXT, THINKING)]
    assert live == [(THINKING, "quick"), (TEXT, "all at once")]
    assert [e.text for e in events if isinstance(e, Reasoning)] == ["quick"]
