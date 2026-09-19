"""A turn's failure is typed on the record and raised typed (ENH-024, D139).

A thread resumed on a session id its CLI no longer has used to end as an anonymous failed turn;
a product could not tell "the resume broke" from "the turn broke", and had to guess whether to
`fork`. Now the turn record says `failure = "session_gone"`, and `Thread.turn` raises
`SessionGone(thread_id, session_id, provider)` once the stream has ended — after the record was
written, so the trail is true whether or not anyone catches it. A turn that failed for another
reason has an empty `failure` and raises nothing, as before.
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


class GoneProvider:
    """An agent whose session, once resumed, says the session is gone — or merely fails."""

    def __init__(self, *, gone: bool, session_id: str = "s-1") -> None:
        self.gone = gone
        self.session_id = session_id
        self.opened_with: list[str | None] = []

    class _Session:
        def __init__(self, agent: GoneProvider) -> None:
            self.agent = agent
            self.session_id = agent.session_id

        async def turn(self, prompt: str) -> Turn:
            if self.agent.gone:
                return Turn(
                    text="No conversation found with session ID: s-1",
                    failed=True,
                    session_gone=True,
                )
            return Turn(text="You've hit your usage limit.", failed=True)

        async def close(self) -> None:
            pass

        async def steer(self, text: str) -> bool:
            return False

        async def interrupt(self) -> bool:
            return False

    async def open(self, *, resume: str | None = None, **_kw: Any) -> AgentSession:
        self.opened_with.append(resume)
        return cast(AgentSession, GoneProvider._Session(self))


def _ports() -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


async def _open(tmp_path: Path, agent: GoneProvider, store: InMemoryThreads) -> Thread:
    return await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(),
        store=store,
        root=tmp_path / "work",
        lease=Lease(Ceiling(20, 600, None), Floor(0)),
        approvals=Approvals(),
        mode="full",
        provider="double",
    )


async def test_a_gone_session_is_typed_on_the_record_and_raised(tmp_path: Path) -> None:
    agent = GoneProvider(gone=True)
    store = InMemoryThreads()
    thread = await _open(tmp_path, agent, store)
    try:
        with pytest.raises(SessionGone) as gone:
            async for _ in thread.turn("hello again"):
                pass
        assert gone.value.thread_id == thread.id
        assert gone.value.session_id == "s-1"
        assert gone.value.provider == "double"

        last = thread.record.turns[-1]
        assert last.outcome == "failed"
        assert last.failure == "session_gone"
        assert "No conversation found" in last.text
        saved = await store.get(thread.id)
        assert saved is not None and saved.turns[-1].failure == "session_gone", "durable"
    finally:
        await thread.close()


async def test_any_other_failure_stays_an_untyped_failed_turn(tmp_path: Path) -> None:
    agent = GoneProvider(gone=False)
    thread = await _open(tmp_path, agent, InMemoryThreads())
    try:
        events = [e async for e in thread.turn("hello")]
        assert events, "the turn ran"
        last = thread.record.turns[-1]
        assert last.outcome == "failed"
        assert last.failure == ""
    finally:
        await thread.close()


def test_the_refusal_says_all_three_names() -> None:
    said = str(SessionGone("t-1", "s-1", "codex"))
    assert "t-1" in said and "s-1" in said and "codex" in said
