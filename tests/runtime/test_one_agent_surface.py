"""D98: a model loop and a provider-owned loop live below the same durable Thread."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from shadow_hdk.kernel import (
    Activity,
    Allow,
    Ask,
    Ceiling,
    Completed,
    EffectProfile,
    Floor,
    Lease,
    ModelPort,
    ModelRequest,
    ModelResponse,
    ScopeSet,
    ToolCall,
    Usage,
)
from shadow_hdk.kernel.ports import Context, Judgement
from shadow_hdk.runtime import Approvals, Approve, Ports
from shadow_hdk.runtime.items import items
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    Judge,
    ListSink,
    ScriptedModel,
    make_registration,
)
from shadow_hdk.runtime.threads import InMemoryThreads, Thread
from shadow_hdk.testing import ScriptedAgent

pytestmark = pytest.mark.anyio

LOOK = make_registration("look", effects=EffectProfile(reads=ScopeSet.of("workspace")))
WRITE = make_registration("write", effects=EffectProfile(writes=ScopeSet.of("workspace")))
SPENT = Usage(input_tokens=7, output_tokens=3, cost_cents=2)


async def _look(inputs: Any) -> Completed:
    return Completed({"found": inputs})


async def _write(inputs: Any) -> Completed:
    return Completed({"wrote": inputs})


class AskWrites:
    async def judge(self, effects: EffectProfile, _context: Context) -> Judgement:
        return Ask("may this write?") if "workspace" in effects.writes.names else Allow()


class Seen:
    def __init__(self) -> None:
        self.events: list[Any] = []
        self.activities: list[Activity] = []

    async def on(self, event: Any) -> None:
        self.events.append(event)

    async def on_activity(self, activity: Activity) -> None:
        self.activities.append(activity)


class BlockingModel(ModelPort):
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.cancelled = asyncio.Event()

    async def complete(self, _request: ModelRequest) -> ModelResponse:
        self.started.set()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            self.cancelled.set()
            raise
        return ModelResponse()


def _ports(observer: Seen, *, asks: bool = False) -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(LOOK, _look), (WRITE, _write)]),),
        governance=AskWrites() if asks else Judge.allow_all(),
        sink=ListSink(),
        clock=FixedClock(),
        observer=observer,
    )


def _lease() -> Lease:
    return Lease(Ceiling(40, 600, 100), Floor(0))


def _provider(kind: str) -> tuple[Any, ScriptedModel | None]:
    if kind == "cli":
        return ScriptedAgent([([("look", {"query": "shadow"})], "found it")], usage=SPENT), None

    # Imported here so the CLI half of the evaluator remains green while the new adapter is red.
    from shadow_hdk.adapters.agent import ModelAgent, single

    model = ScriptedModel(
        [
            ModelResponse(
                text="I will look.",
                reasoning="Need current evidence.",
                tool_calls=(ToolCall("call-1", "look", {"query": "shadow"}),),
                usage=Usage(4, 1, 1),
            ),
            ModelResponse(text="found it", usage=Usage(3, 2, 1)),
        ]
    )
    return ModelAgent(model=model, pattern=single), model


@pytest.mark.parametrize("kind", ["cli", "model"])
async def test_both_provider_kinds_have_one_thread_turn_item_and_spend_surface(
    kind: str, tmp_path: Path
) -> None:
    observer = Seen()
    provider, model = _provider(kind)
    store = InMemoryThreads()
    thread = await Thread.open(
        agent=provider,
        ports=_ports(observer),
        store=store,
        root=tmp_path,
        lease=_lease(),
    )
    if isinstance(provider, ScriptedAgent):
        provider.reach = thread.registry.call
    try:
        events = [event async for event in thread.turn("find shadow")]
    finally:
        await thread.close()

    folded = items(events)
    assert [item.step for item in folded] == ["turn-1"]
    assert [child.component for child in folded[0].children] == ["look"]
    assert folded[0].children[0].inputs == {"query": "shadow"}
    assert thread.record.turns[-1].text == "found it"
    assert thread.record.spent.input_tokens == 7
    assert thread.record.spent.output_tokens == 3
    assert thread.record.spent.cents == 2
    if model is not None:
        assert [request.messages[-1].content for request in model.requests] == [
            "find shadow",
            '{"found": {"query": "shadow"}}',
        ]
        assert observer.activities[0].kind == "thinking"
        assert "".join(a.text for a in observer.activities if a.kind == "thinking") == (
            "Need current evidence."
        )
        assert "".join(a.text for a in observer.activities if a.kind == "text") == (
            "I will look.found it"
        )


async def test_a_model_unknown_tool_is_a_governed_refusal_not_an_out_of_band_call(
    tmp_path: Path,
) -> None:
    from shadow_hdk.adapters.agent import ModelAgent, single

    model = ScriptedModel(
        [
            ModelResponse(tool_calls=(ToolCall("call-1", "not_offered", {"secret": "no"}),)),
            ModelResponse(text="could not call it"),
        ]
    )
    thread = await Thread.open(
        agent=ModelAgent(model=model, pattern=single),
        ports=_ports(Seen()),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=_lease(),
    )
    try:
        events = [event async for event in thread.turn("try the unknown tool")]
    finally:
        await thread.close()

    assert not [
        event for event in events if event.kind == "invoked" and event.component == "not_offered"
    ]
    assert "no component" in model.requests[-1].messages[-1].content


async def test_a_model_session_is_held_across_turns_and_the_thread_record_resumes(
    tmp_path: Path,
) -> None:
    from shadow_hdk.adapters.agent import ModelAgent, single

    store = InMemoryThreads()
    first_model = ScriptedModel(
        [ModelResponse(text="first", usage=Usage(1, 1, 1)), ModelResponse(text="second")]
    )
    first_agent = ModelAgent(model=first_model, pattern=single)
    thread = await Thread.open(
        agent=first_agent,
        ports=_ports(Seen()),
        store=store,
        root=tmp_path,
        lease=_lease(),
    )
    [event async for event in thread.turn("one")]
    [event async for event in thread.turn("two")]
    thread_id = thread.id
    await thread.close()

    assert [request.messages[-1].content for request in first_model.requests] == ["one", "two"]
    assert thread.record.spent.unmetered, "omitted usage stays unknown, not zero"

    resumed_model = ScriptedModel([ModelResponse(text="third", usage=Usage(2, 1, 1))])
    resumed = await Thread.resume(
        thread_id,
        agent=ModelAgent(model=resumed_model, pattern=single),
        ports=_ports(Seen()),
        store=store,
        lease=_lease(),
    )
    try:
        [event async for event in resumed.turn("three")]
    finally:
        await resumed.close()

    assert [turn.id for turn in resumed.record.turns] == ["turn-1", "turn-2", "turn-3"]
    assert [turn.text for turn in resumed.record.turns] == ["first", "second", "third"]


async def test_a_model_tool_call_parks_through_the_same_thread_question_surface(
    tmp_path: Path,
) -> None:
    from shadow_hdk.adapters.agent import ModelAgent, single

    approvals = Approvals()
    model = ScriptedModel(
        [
            ModelResponse(tool_calls=(ToolCall("call-1", "write", {"value": 1}),)),
            ModelResponse(text="the approved write is recorded"),
        ]
    )
    thread = await Thread.open(
        agent=ModelAgent(model=model, pattern=single),
        ports=_ports(Seen(), asks=True),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=_lease(),
        approvals=approvals,
        checkpointer=InMemorySaver(),
    )
    try:
        events = [event async for event in thread.turn("write it", on_question="park")]
        assert thread.record.turns[-1].outcome == "parked"
        assert len(thread.record.pending) == 1
        assert thread.record.pending[0].component == "write"
        assert thread.record.pending[0].inputs == {"value": 1}
        assert [event.kind for event in events].count("approval_requested") >= 1

        settled = await thread.settle(thread.record.pending[0].handle, Approve())
        assert any(event.kind == "observed" for event in settled)
        assert not thread.record.pending

        [event async for event in thread.turn("continue")]
    finally:
        await thread.close()

    assert "approved" in model.requests[-1].messages[-1].content
    assert '"wrote": {"value": 1}' in model.requests[-1].messages[-1].content


async def test_interrupting_the_thread_cancels_a_blocked_model_call(tmp_path: Path) -> None:
    from shadow_hdk.adapters.agent import ModelAgent, single

    model = BlockingModel()
    thread = await Thread.open(
        agent=ModelAgent(model=model, pattern=single),
        ports=_ports(Seen()),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=_lease(),
    )
    turning = asyncio.create_task(_collect(thread.turn("wait")))
    try:
        await asyncio.wait_for(model.started.wait(), 1)
        await thread.interrupt()
        events = await asyncio.wait_for(turning, 1)
    finally:
        turning.cancel()
        await thread.close()

    assert model.cancelled.is_set()
    assert thread.record.turns[-1].outcome == "cancelled"
    assert any(event.kind == "ended" for event in events), "the runtime still closes its run"


async def test_the_python_composition_door_accepts_a_model_without_a_second_runner(
    tmp_path: Path,
) -> None:
    from shadow_hdk.serve import a_thread

    model = ScriptedModel([ModelResponse(text="through the same door")])
    async with a_thread(tmp_path, mode="full", model=model) as thread:
        [event async for event in thread.turn("hello")]

    assert thread.record.turns[-1].text == "through the same door"


async def _collect(events: Any) -> list[Any]:
    return [event async for event in events]
