"""The governed turn as a primitive (Phase 30 group 1, D87).

A product that owns its conversation — its own messages, its own tables — takes the kit's turn
without the kit's container: `Conversation` is one provider session opened on the served
registry, whose turns are runs judged by the ports it was given, streamed as events; what it
remembers is the last turn, for the product to fold into its own model. No `ThreadStore`, no
record, no hold. `Thread` is a `Conversation` plus a record, a store and a hold.

Before this a product had to open a `Thread` per turn over an in-memory store with a one-entry
fake mode registry to get a governed CLI turn (Intent Studio, `engine.py::_subscription_turn`).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    EffectProfile,
    Floor,
    Lease,
    Observed,
    Refused,
    ScopeSet,
    Turn,
    TurnRecord,
)
from shadow_hdk.kernel.ports import AgentSession, Allow, Ask, Context, Judgement, ToolSource
from shadow_hdk.runtime import Approvals, Approve, Ports
from shadow_hdk.runtime.conversation import Conversation, Turned
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink, make_registration
from shadow_hdk.runtime.threads import Thread

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
LOOK = make_registration("look", effects=EffectProfile(reads=WORKSPACE))
WRITE = make_registration("write_file", effects=EffectProfile(writes=WORKSPACE, reversible=False))


class Seen:
    def __init__(self) -> None:
        self.contexts: list[Context] = []

    async def judge(self, _effects: EffectProfile, context: Context) -> Judgement:
        self.contexts.append(context)
        if context.attributes.get("component") == "write_file":
            return Ask("may it write?")
        return Allow()


class Agent:
    """A provider double: each turn calls what it was scripted to, through the registry the
    conversation served it, then says its line; every answer a tool gave it is kept."""

    def __init__(self, turns: list[tuple[list[tuple[str, dict[str, Any]]], str]]) -> None:
        self.turns = list(turns)
        self.reach: Any = None
        self.prompts: list[str] = []
        self.answers: list[Any] = []
        self.opened = 0
        self.behaviours: list[Any] = []

    async def open(
        self, *, tools: tuple[ToolSource, ...] = (), behaviour: Any = None, **_: Any
    ) -> AgentSession:
        agent = self
        self.opened += 1
        self.behaviours.append(behaviour)

        class _Session:
            async def turn(self, prompt: str) -> Turn:
                agent.prompts.append(prompt)
                calls, line = agent.turns.pop(0)
                for name, arguments in calls:
                    agent.answers.append(await agent.reach(name, arguments))
                return Turn(text=line)

            async def close(self) -> None:
                pass

            async def stream(self, prompt: str) -> AsyncIterator[Any]:  # pragma: no cover
                raise NotImplementedError
                yield

        return cast(AgentSession, _Session())


class Writes:
    def __init__(self) -> None:
        self.wrote: list[JsonValue] = []

    async def __call__(self, inputs: JsonValue) -> Any:
        self.wrote.append(inputs)
        return Completed({"wrote": True})


async def look(_inputs: Any) -> Any:
    return Completed({"found": 1})


def _ports(governance: Any, writes: Writes | None = None) -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(LOOK, look), (WRITE, writes or Writes())]),),
        governance=governance,
        sink=ListSink(),
        clock=FixedClock(),
    )


def _lease() -> Lease:
    return Lease(Ceiling(40, 600, None), Floor(0))


async def _open(agent: Agent, ports: Ports, tmp_path: Path, **kw: Any) -> Conversation:
    conversation = await Conversation.open(
        agent=cast(Any, agent), ports=ports, root=tmp_path, lease=_lease(), **kw
    )
    agent.reach = conversation.registry.call
    return conversation


async def test_a_conversation_turns_without_a_store_and_remembers_only_the_last_turn(
    tmp_path: Path,
) -> None:
    seen = Seen()
    agent = Agent([([("look", {})], "one"), ([], "two")])
    conversation = await _open(agent, _ports(seen), tmp_path, principal="alice")
    try:
        assert conversation.id and conversation.turns_taken == 0
        events = [e async for e in conversation.turn("first")]
        assert [e.kind for e in events][0] == "started"
        assert any(isinstance(e, Observed) and e.step == "turn-1" for e in events)
        last = conversation.last
        assert isinstance(last, Turned) and isinstance(last.as_record(), TurnRecord)
        assert last.id == "turn-1" and last.prompt == "first" and last.outcome == "completed"
        assert last.text == "one" and last.run_id
        assert conversation.turns_taken == 1
        # Every judgement carried the identity, the tool call's included (D82).
        assert seen.contexts and all(c.principal == "alice" for c in seen.contexts)
        assert {c.attributes.get("thread") for c in seen.contexts} == {conversation.id}

        [e async for e in conversation.turn("second")]
        assert conversation.last is not None and conversation.last.id == "turn-2"
        assert conversation.last.text == "two"
        assert conversation.remaining().ceiling.max_steps < 40
    finally:
        await conversation.close()
    assert not hasattr(conversation, "record"), "nothing of a record: the product keeps its own"


async def test_a_question_is_answered_live_through_the_handle(tmp_path: Path) -> None:
    approvals = Approvals()
    writes = Writes()
    agent = Agent([([("write_file", {"path": "a.txt"})], "wrote")])
    conversation = await _open(agent, _ports(Seen(), writes), tmp_path, approvals=approvals)

    async def answering() -> None:
        asked = await approvals.next()
        approvals.answer(asked.handle, Approve())

    task = asyncio.create_task(answering())
    try:
        [e async for e in conversation.turn("write")]
        await asyncio.wait_for(task, 5)
        assert writes.wrote == [{"path": "a.txt"}]
        assert conversation.last is not None and conversation.last.outcome == "completed"
        assert conversation.last.pending == (), "answered: nothing left open"
    finally:
        await conversation.close()


async def test_a_turn_parks_on_purpose_and_the_question_is_the_last_turns(
    tmp_path: Path,
) -> None:
    """`on_question="park"` (D88): the question is not put to anybody now — the provider is
    told the call is kept and will run once approved, the turn ends `parked`, and the question
    with the run that sleeps on it is on `last` for whoever keeps the record."""
    approvals = Approvals()
    writes = Writes()
    agent = Agent([([("write_file", {"path": "a.txt"})], "asked to write; stopping")])
    conversation = await _open(agent, _ports(Seen(), writes), tmp_path, approvals=approvals)
    try:
        [e async for e in conversation.turn("write", on_question="park")]
        assert writes.wrote == [], "nothing ran"
        (answer,) = agent.answers
        assert isinstance(answer, Refused) and "kept" in answer.reason
        last = conversation.last
        assert last is not None and last.outcome == "parked", last
        (question,) = last.pending
        assert question.component == "write_file" and question.inputs == {"path": "a.txt"}
        assert question.turn == "turn-1" and question.run_id, "the run that sleeps on it"
        assert approvals.pending() == (), "not waiting on anyone"
    finally:
        await conversation.close()


async def test_set_mode_changes_the_behaviour_and_reopens_the_provider(tmp_path: Path) -> None:
    class _Spec:
        def __init__(self, behaviour: str) -> None:
            self.behaviour = behaviour
            self.environment = ""

    class _Modes:
        def get(self, mode_id: str) -> Any:
            return _Spec(f"be {mode_id}")

    agent = Agent([([], "ok")])
    conversation = await _open(agent, _ports(Seen()), tmp_path, modes=_Modes(), mode="calm")
    try:
        assert agent.behaviours == ["be calm"] and conversation.mode == "calm"
        changed = await conversation.set_mode("bold")
        assert changed and changed.mode == "bold" and conversation.mode == "bold"
        assert agent.opened == 2 and agent.behaviours[-1] == "be bold"
        assert await conversation.set_mode("bold") is None, "nothing to change"
    finally:
        await conversation.close()


async def test_a_thread_is_a_conversation_with_a_record(tmp_path: Path) -> None:
    from shadow_hdk.runtime.threads import InMemoryThreads

    agent = Agent([([("look", {})], "one")])
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(Seen()),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=_lease(),
    )
    agent.reach = thread.registry.call
    try:
        assert isinstance(thread.conversation, Conversation)
        assert thread.conversation.id == thread.id
        [e async for e in thread.turn("go")]
        assert thread.conversation.last is not None
        assert thread.record.turns[-1] == thread.conversation.last.as_record()
    finally:
        await thread.close()
