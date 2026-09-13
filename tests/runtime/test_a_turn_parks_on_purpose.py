"""A park on purpose (Phase 30 group 1, D88).

A request/response product cannot hold a turn open while a person thinks: the request must
return. `turn(on_question="park")` ends the turn `parked` at its questions — each kept on the
record with the run that sleeps on it — and a later request settles it; a host that is there
can answer any one question `Parked` itself. D80 covered the host that died; this is the host
that chose to.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.kernel import Completed, Observed
from shadow_hdk.runtime import Approvals, Approve, Parked
from shadow_hdk.runtime.threads import InMemoryThreads, Thread
from shadow_hdk.serve.stores import stores_for
from tests.runtime.test_a_conversation_without_a_record import Agent, Seen, Writes, _lease, _ports

pytestmark = pytest.mark.anyio


async def test_a_turn_parked_on_purpose_is_settled_on_a_later_request(tmp_path: Path) -> None:
    stores = stores_for(f"sqlite:///{tmp_path}/live.sqlite")
    approvals = Approvals()
    writes = Writes()
    agent = Agent([([("write_file", {"path": "a.txt"})], "asked; stopping"), ([], "carried on")])
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(Seen(), writes),
        store=stores.threads,
        root=tmp_path / "work",
        lease=_lease(),
        approvals=approvals,
        checkpointer=await stores.checkpointer(),
    )
    agent.reach = thread.registry.call
    try:
        [e async for e in thread.turn("write a.txt", on_question="park")]
        assert thread.record.turns[-1].outcome == "parked"
        (question,) = thread.pending
        assert question.component == "write_file" and question.run_id
        kept = await stores.threads.get(thread.id)
        assert kept is not None and kept.pending == thread.pending, "on the store"
        assert writes.wrote == []

        # The later request: the person said yes.
        events = await thread.settle(question.handle, Approve())
        observed = [e for e in events if isinstance(e, Observed)]
        assert observed and observed[-1].observation == Completed({"wrote": True})
        assert writes.wrote == [{"path": "a.txt"}]
        assert thread.pending == ()

        [e async for e in thread.turn("next")]
        assert "approved" in agent.prompts[-1] and '"wrote": true' in agent.prompts[-1]
        after = thread.record.turns[-1]
        assert after.id == "turn-2" and after.outcome == "completed"
    finally:
        await thread.close()
        await stores.aclose()


async def test_a_host_may_park_one_question_itself_and_wait_on_another(tmp_path: Path) -> None:
    """`on_question="wait"` with a host that answers `Parked` for the call it cannot decide now
    and `Approve` for the one it can."""
    approvals = Approvals()
    writes = Writes()
    agent = Agent(
        [([("write_file", {"path": "a.txt"}), ("write_file", {"path": "b.txt"})], "done")]
    )
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(Seen(), writes),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=_lease(),
        approvals=approvals,
    )
    agent.reach = thread.registry.call

    async def answering() -> None:
        first = await approvals.next()
        approvals.answer(first.handle, Parked())
        second = await approvals.next()
        approvals.answer(second.handle, Approve())

    task = asyncio.create_task(answering())
    try:
        [e async for e in thread.turn("write both")]
        await asyncio.wait_for(task, 10)
        assert writes.wrote == [{"path": "b.txt"}], "the second ran; the first is kept"
        assert thread.record.turns[-1].outcome == "parked"
        (question,) = thread.pending
        assert question.inputs == {"path": "a.txt"}
    finally:
        await thread.close()


async def test_without_a_handle_a_park_is_the_refusal_it_always_was(tmp_path: Path) -> None:
    """Nobody to keep the question for: the call is refused as before, nothing is pending."""
    writes = Writes()
    agent = Agent([([("write_file", {"path": "a.txt"})], "refused")])
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(Seen(), writes),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=_lease(),
    )
    agent.reach = thread.registry.call
    try:
        [e async for e in thread.turn("write", on_question="park")]
        assert thread.record.turns[-1].outcome == "completed"
        assert thread.pending == () and writes.wrote == []
    finally:
        await thread.close()
