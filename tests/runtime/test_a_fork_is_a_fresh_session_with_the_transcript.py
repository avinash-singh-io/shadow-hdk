"""A fork is a fresh provider session with the transcript (BUG-062; D139's "next move").

D139 says the move after `session_gone` is `fork` — "a fresh provider session with the
transcript". Until 0.34.1 `Thread.fork` copied the record whole, `session_id` included, so a
resume of the fork opened the provider on the very session it no longer had and `SessionGone`
was raised again; and nothing seeded the transcript — `seeded_turns` stayed 0 on a fork and, on
a rollback, said N while nobody seeded anything. Measured by the product on 0.34.0.

Now `fork` and `rollback` both leave `session_id` empty and say `seeded_turns`; the first turn
on such a record — a fresh provider session, no turn taken since — is told the kept turns
ahead of its prompt, once, by the kit. The record says what happened rather than pretending.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.kernel import Ceiling, Floor, Lease, Turn
from shadow_hdk.kernel.ports import AgentSession
from shadow_hdk.runtime import Approvals, Ports
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink
from shadow_hdk.runtime.threads import InMemoryThreads, SessionGone, Thread
from tests.wire.test_a_thread_crosses_the_wire import AllowAll

pytestmark = pytest.mark.anyio


class Recording:
    """An agent that remembers what it was opened with and what each session was told — and
    whose session `s-1`, once lost, says so."""

    def __init__(self) -> None:
        self.opened_with: list[str | None] = []
        self.prompts: list[str] = []
        self.lost: set[str] = set()
        self.next_id = 0

    async def open(self, *, resume: str | None = None, **_: Any) -> AgentSession:
        self.opened_with.append(resume)
        agent = self
        if resume is None:
            agent.next_id += 1
        session_id = resume or f"s-{agent.next_id}"

        class _Session:
            def __init__(self) -> None:
                self.session_id = session_id

            async def turn(self, prompt: str) -> Turn:
                agent.prompts.append(prompt)
                if session_id in agent.lost:
                    return Turn(
                        text=f"no rollout found for thread id {session_id}",
                        failed=True,
                        session_gone=True,
                    )
                return Turn(text=f"answer {len(agent.prompts)}")

            async def close(self) -> None:
                pass

            async def steer(self, text: str) -> bool:
                return False

            async def interrupt(self) -> bool:
                return False

        return cast(AgentSession, _Session())


def _ports() -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


def _lease() -> Lease:
    return Lease(Ceiling(20, 600, None), Floor(0))


async def _open(tmp_path: Path, agent: Recording, store: InMemoryThreads) -> Thread:
    return await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(),
        store=store,
        root=tmp_path / "work",
        lease=_lease(),
        approvals=Approvals(),
        mode="full",
        provider="double",
    )


async def _resume(thread_id: str, agent: Recording, store: InMemoryThreads) -> Thread:
    return await Thread.resume(
        thread_id, agent=cast(Any, agent), ports=_ports(), store=store, lease=_lease()
    )


async def test_after_session_gone_a_fork_opens_a_fresh_session_seeded_with_the_transcript(
    tmp_path: Path,
) -> None:
    agent, store = Recording(), InMemoryThreads()
    thread = await _open(tmp_path, agent, store)
    [e async for e in thread.turn("what is the lathe's weight?")]
    [e async for e in thread.turn("and its height?")]
    assert thread.record.session_id == "s-1"
    await thread.close()

    agent.lost.add("s-1")
    resumed = await _resume(thread.id, agent, store)
    with pytest.raises(SessionGone):
        async for _ in resumed.turn("and its width?"):
            pass
    forked = await resumed.fork()
    await resumed.close()

    assert forked.forked_from == thread.id
    assert forked.session_id == "", "a fork is a fresh provider session"
    assert forked.seeded_turns == len(forked.turns) == 3, (
        "the record says what seeds the first turn"
    )

    fresh = await _resume(forked.id, agent, store)
    try:
        assert agent.opened_with[-1] is None, "opened fresh, not on the lost session"
        [e async for e in fresh.turn("so, the width?")]
        told = agent.prompts[-1]
        assert "what is the lathe's weight?" in told and "answer 1" in told, told
        assert "and its height?" in told and "answer 2" in told, told
        assert told.rstrip().endswith("so, the width?"), "the transcript ahead of the prompt"
        assert fresh.record.turns[-1].outcome == "completed"
        assert fresh.record.session_id == "s-2", (
            "the fresh session's own id, kept for the next resume"
        )

        [e async for e in fresh.turn("thanks")]
        assert "what is the lathe's weight?" not in agent.prompts[-1], "seeded once, not every turn"
    finally:
        await fresh.close()


async def test_a_rollback_is_a_fresh_session_seeded_with_the_kept_turns(tmp_path: Path) -> None:
    """A rollback said `seeded_turns=N` since Phase 25 and nobody seeded; the provider was even
    resumed on its old session, which still remembered the rolled-back turns."""
    agent, store = Recording(), InMemoryThreads()
    thread = await _open(tmp_path, agent, store)
    for prompt in ("one", "two", "three"):
        [e async for e in thread.turn(prompt)]
    rolled = await thread.rollback(to_turn=1)
    await thread.close()

    assert rolled.session_id == "" and rolled.seeded_turns == 1

    fresh = await _resume(rolled.id, agent, store)
    try:
        [e async for e in fresh.turn("four")]
        told = agent.prompts[-1]
        assert "one" in told and "answer 1" in told
        assert "two" not in told and "three" not in told, "the rolled-back turns are gone"
        assert agent.opened_with[-1] is None
    finally:
        await fresh.close()


async def test_a_thread_with_no_turns_forks_without_a_seed(tmp_path: Path) -> None:
    agent, store = Recording(), InMemoryThreads()
    thread = await _open(tmp_path, agent, store)
    forked = await thread.fork()
    await thread.close()
    assert forked.seeded_turns == 0 and forked.session_id == ""

    fresh = await _resume(forked.id, agent, store)
    try:
        [e async for e in fresh.turn("first")]
        assert agent.prompts[-1] == "first"
    finally:
        await fresh.close()
