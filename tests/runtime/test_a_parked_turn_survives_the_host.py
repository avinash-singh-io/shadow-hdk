"""A parked turn survives the host (Phase 29 group 1, D80).

A turn whose tool call the policy asked about is waiting on a person. The host goes away — the
laptop closed, the process restarted, the page that parked it long gone. What survives is on the
record: the question, what it is about, and the run that parked on it, which sleeps in the
checkpointer the store chose. A new host resumes the thread, finds the last turn `parked`, offers
the question again, and the answer settles it: the act runs (or is refused) from its checkpoint,
the record says so, and the agent is told at its next turn what became of the call it made —
its own transcript cannot be rewound, so it is told rather than pretended to.

The crash is simulated as a crash: the store's files are copied while the question is open, and
the second host opens the copy. Nothing the first host would write on its way out reaches it.
"""

from __future__ import annotations

import asyncio
import contextlib
import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import JsonValue

from shadow_hdk.adapters.basic import SqliteThreads
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
)
from shadow_hdk.kernel.ports import AgentSession, Allow, Ask, Context, Judgement, ToolSource
from shadow_hdk.runtime import Approvals, Approve, Deny, InMemoryEffectJournal, Ports
from shadow_hdk.runtime.testing import (
    AllowAuthorizer,
    FixedAuthority,
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)
from shadow_hdk.runtime.threads import Thread
from shadow_hdk.serve.stores import stores_for

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
WRITE = make_registration("write_file", effects=EffectProfile(writes=WORKSPACE, reversible=False))


class AsksAboutWrites:
    """The turn's own step is allowed; a write is put to the person — what the `ask` mode does,
    without the whole mode registry."""

    async def judge(self, _effects: EffectProfile, context: Context) -> Judgement:
        if context.attributes.get("component") == "write_file":
            return Ask("may it write?")
        return Allow()


class Writes:
    def __init__(self) -> None:
        self.wrote: list[JsonValue] = []

    async def __call__(self, inputs: JsonValue) -> Any:
        self.wrote.append(inputs)
        return Completed({"wrote": True})


class Agent:
    """A provider double whose turns call tools through the registry, then say a line; every
    prompt it was given is kept, because the note about a settled call arrives as one."""

    def __init__(self, turns: list[tuple[list[tuple[str, dict[str, Any]]], str]]) -> None:
        self.turns = list(turns)
        self.prompts: list[str] = []
        self.reach: Any = None

    async def open(self, *, tools: tuple[ToolSource, ...] = (), **_: Any) -> AgentSession:
        agent = self

        class _Session:
            async def turn(self, prompt: str) -> Turn:
                agent.prompts.append(prompt)
                calls, line = agent.turns.pop(0)
                for name, arguments in calls:
                    await agent.reach(name, arguments)
                return Turn(text=line)

            async def close(self) -> None:
                pass

            async def stream(self, prompt: str) -> AsyncIterator[Any]:  # pragma: no cover
                raise NotImplementedError
                yield

        return cast(AgentSession, _Session())


def _ports(writes: Writes) -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(WRITE, writes)]),),
        governance=AsksAboutWrites(),
        sink=ListSink(),
        clock=FixedClock(),
        authority=FixedAuthority(),
        authorizer=AllowAuthorizer(),
        effect_journal=InMemoryEffectJournal(),
    )


def _lease() -> Lease:
    return Lease(Ceiling(40, 600, None), Floor(0))


async def _park_a_turn_then_die(where: Path, image: Path) -> tuple[str, str]:
    """Host A: open a thread, start a turn that calls `write_file`, wait for the question, copy
    the store while it is open, and die. Returns the thread id and the question's handle."""
    stores = stores_for(f"sqlite:///{where}/live.sqlite")
    approvals = Approvals()
    agent = Agent([([("write_file", {"path": "a.txt", "content": "x"})], "wrote it")])
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(Writes()),
        store=stores.threads,
        root=where / "work",
        lease=_lease(),
        approvals=approvals,
        checkpointer=await stores.checkpointer(),
        mode="asking",
    )
    agent.reach = thread.registry.call

    async def turning() -> None:
        async for _event in thread.turn("write a.txt"):
            pass

    turn = asyncio.create_task(turning())
    try:
        asked = await asyncio.wait_for(approvals.next(), 30)
        assert asked.component == "write_file"
        assert asked.inputs == {"path": "a.txt", "content": "x"}
        # The record, as it is on disk while the person has not answered: what a crash leaves.
        await asyncio.sleep(0.05)  # the record's save after the question is a separate write
        shutil.copytree(where, image)
    finally:
        turn.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await turn
        await thread.close()
        await stores.aclose()
    return thread.id, asked.handle


@contextlib.asynccontextmanager
async def _resumed_on(
    image: Path, thread_id: str, agent: Agent, writes: Writes
) -> AsyncIterator[Thread]:
    """Host B: the thread picked up from the crash image, closed with its stores after."""
    stores = stores_for(f"sqlite:///{image}/live.sqlite")
    thread = await Thread.resume(
        thread_id,
        agent=cast(Any, agent),
        ports=_ports(writes),
        store=stores.threads,
        lease=_lease(),
        approvals=Approvals(),
        checkpointer=await stores.checkpointer(),
    )
    agent.reach = thread.registry.call
    try:
        yield thread
    finally:
        await thread.close()
        await stores.aclose()


async def test_the_question_is_on_the_record_while_it_is_open(tmp_path: Path) -> None:
    thread_id, handle = await _park_a_turn_then_die(tmp_path / "a", tmp_path / "image")
    record = await SqliteThreads(tmp_path / "image" / "live.threads.sqlite").get(thread_id)
    assert record is not None
    assert record.turns[-1].outcome == "running", "the host died before the turn settled"
    (question,) = record.pending
    assert question.handle == handle
    assert question.turn == "turn-1" and question.kind == "approval"
    assert question.component == "write_file"
    assert question.inputs == {"path": "a.txt", "content": "x"}
    assert question.run_id and question.run_id != record.turns[-1].run_id, "the run that parked"


async def test_a_new_host_finds_the_turn_parked_and_the_question_pending(tmp_path: Path) -> None:
    thread_id, handle = await _park_a_turn_then_die(tmp_path / "a", tmp_path / "image")
    async with _resumed_on(tmp_path / "image", thread_id, Agent([]), Writes()) as resumed:
        assert resumed.record.turns[-1].outcome == "parked"
        assert [q.handle for q in resumed.pending] == [handle]


async def test_approved_the_act_runs_from_its_checkpoint_and_the_agent_is_told(
    tmp_path: Path,
) -> None:
    thread_id, handle = await _park_a_turn_then_die(tmp_path / "a", tmp_path / "image")
    writes = Writes()
    agent = Agent([([], "carrying on")])
    async with _resumed_on(tmp_path / "image", thread_id, agent, writes) as resumed:
        events = await resumed.settle(handle, Approve())
        observed = [e for e in events if isinstance(e, Observed)]
        assert observed and observed[-1].observation == Completed({"wrote": True}), events
        assert writes.wrote == [{"path": "a.txt", "content": "x"}], "the act ran, once"
        assert resumed.pending == ()
        assert resumed.record.turns[-1].outcome == "parked"
        assert "write_file" in resumed.record.turns[-1].text
        assert "approved" in resumed.record.turns[-1].text

        [e async for e in resumed.turn("next")]
        (prompt,) = agent.prompts
        assert "write_file" in prompt and "approved" in prompt and '"wrote": true' in prompt
        assert prompt.endswith("next")


async def test_denied_nothing_runs_and_the_agent_is_told_why(tmp_path: Path) -> None:
    thread_id, handle = await _park_a_turn_then_die(tmp_path / "a", tmp_path / "image")
    writes = Writes()
    agent = Agent([([], "fine")])
    async with _resumed_on(tmp_path / "image", thread_id, agent, writes) as resumed:
        events = await resumed.settle(handle, Deny("not that file"))
        observed = [e for e in events if isinstance(e, Observed)]
        assert observed and isinstance(observed[-1].observation, Refused), events
        assert observed[-1].observation.reason == "not that file"
        assert writes.wrote == []
        assert resumed.pending == ()
        [e async for e in resumed.turn("next")]
        (prompt,) = agent.prompts
        assert "write_file" in prompt and "denied" in prompt and "not that file" in prompt


async def test_an_unknown_handle_is_refused_by_name(tmp_path: Path) -> None:
    thread_id, _handle = await _park_a_turn_then_die(tmp_path / "a", tmp_path / "image")
    async with _resumed_on(tmp_path / "image", thread_id, Agent([]), Writes()) as resumed:
        with pytest.raises(KeyError, match="nobody"):
            await resumed.settle("nobody", Approve())


async def test_a_turn_the_host_died_in_with_nothing_pending_is_cancelled_and_says_so(
    tmp_path: Path,
) -> None:
    """No question was open: the host simply died mid-turn. The turn cannot be `running` in a
    process that is not running it; it is `cancelled`, and the text says by what."""
    from dataclasses import replace

    from shadow_hdk.kernel import ThreadRecord, TurnRecord

    store = SqliteThreads(tmp_path / "live.threads.sqlite")
    await store.create(
        ThreadRecord(
            id="t1",
            root=str(tmp_path / "work"),
            created_at="2026-09-14T00:00:00+00:00",
            mode="asking",
            turns=(TurnRecord(id="turn-1", run_id="r1", prompt="go", at="2026-09-14T00:00:01"),),
        )
    )
    agent = Agent([])
    resumed = await Thread.resume(
        "t1", agent=cast(Any, agent), ports=_ports(Writes()), store=store, lease=_lease()
    )
    try:
        last = resumed.record.turns[-1]
        assert last.outcome == "cancelled" and "host" in last.text
        kept = await store.get("t1")
        assert kept is not None and kept.turns[-1] == last, "and the store says the same"
        assert replace(last, outcome="running") != last
    finally:
        await resumed.close()


async def test_a_question_answered_live_is_on_the_record_only_while_it_is_open(
    tmp_path: Path,
) -> None:
    """The same record, no crash: the question is `pending` while the person thinks, and off the
    record once the step it was about is observed — so a host that dies after the answer does not
    offer a settled question again."""
    stores = stores_for(f"sqlite:///{tmp_path}/live.sqlite")
    approvals = Approvals()
    writes = Writes()
    agent = Agent([([("write_file", {"path": "a.txt", "content": "x"})], "wrote it")])
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(writes),
        store=stores.threads,
        root=tmp_path / "work",
        lease=_lease(),
        approvals=approvals,
        checkpointer=await stores.checkpointer(),
        mode="asking",
    )
    agent.reach = thread.registry.call
    try:

        async def turning() -> None:
            async for _event in thread.turn("write a.txt"):
                pass

        turn = asyncio.create_task(turning())
        asked = await asyncio.wait_for(approvals.next(), 30)
        await asyncio.sleep(0.05)
        assert [q.handle for q in thread.pending] == [asked.handle], "open: on the record"
        kept = await stores.threads.get(thread.id)
        assert kept is not None and [q.handle for q in kept.pending] == [asked.handle]
        approvals.answer(asked.handle, Approve())
        await asyncio.wait_for(turn, 30)
        assert writes.wrote == [{"path": "a.txt", "content": "x"}]
        assert thread.pending == (), "answered: off the record"
        kept = await stores.threads.get(thread.id)
        assert kept is not None and kept.pending == () and kept.turns[-1].outcome == "completed"
    finally:
        await thread.close()
        await stores.aclose()


async def test_a_question_answered_mid_turn_is_off_the_record_before_the_next_opens(
    tmp_path: Path,
) -> None:
    """Two calls in one turn, the first answered while the turn still runs: what a crash between
    them would find is the second question alone. A settled question offered again after a
    restart would run the act twice."""
    stores = stores_for(f"sqlite:///{tmp_path}/live.sqlite")
    approvals = Approvals()
    writes = Writes()
    agent = Agent(
        [
            (
                [
                    ("write_file", {"path": "a.txt", "content": "x"}),
                    ("write_file", {"path": "b.txt", "content": "y"}),
                ],
                "wrote both",
            )
        ]
    )
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(writes),
        store=stores.threads,
        root=tmp_path / "work",
        lease=_lease(),
        approvals=approvals,
        checkpointer=await stores.checkpointer(),
        mode="asking",
    )
    agent.reach = thread.registry.call
    turn = asyncio.create_task(_drain(thread.turn("write two files")))
    try:
        first = await asyncio.wait_for(approvals.next(), 30)
        approvals.answer(first.handle, Approve())
        second = await asyncio.wait_for(approvals.next(), 30)
        await asyncio.sleep(0.05)
        kept = await stores.threads.get(thread.id)
        assert kept is not None
        assert [q.handle for q in kept.pending] == [second.handle], "the first is settled"
        assert kept.turns[-1].outcome == "running"
        approvals.answer(second.handle, Approve())
        await asyncio.wait_for(turn, 30)
        assert len(writes.wrote) == 2
    finally:
        turn.cancel()
        with contextlib.suppress(BaseException):
            await turn
        await thread.close()
        await stores.aclose()


async def _drain(events: AsyncIterator[Any]) -> None:
    async for _event in events:
        pass
