"""BUG-056: a change that reopens the provider or the environment happens **between turns, or
not at all**. During a running turn, `set_mode` and `add_root` refuse with the typed `TurnRunning`
— the same refusal `turn(when="reject")` gives (D81), which the wire already names `turn_running`
— and the turn runs on untouched. Before this, `set_mode` closed the provider's session under the
turn (a truncated or failed turn, nothing on the record saying why) and `add_root` refused with an
untyped error a page could not switch on.

The lock that makes a turn exclusive is also held across the change itself, so a turn that
arrives while a mode change is reopening the provider *waits* and runs on the new mode, rather
than racing the reopen.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import anyio
import pytest

from shadow_hdk.kernel import Ceiling, Floor, Lease, Turn
from shadow_hdk.kernel.ports import AgentSession
from shadow_hdk.runtime import Approvals, Ports
from shadow_hdk.runtime.conversation import TurnRunning
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink
from shadow_hdk.runtime.threads import InMemoryThreads, Thread
from shadow_hdk.wire.sides import loopback
from tests.wire.test_a_thread_crosses_the_wire import AllowAll, ScriptedThreads, _OwnIds

pytestmark = pytest.mark.anyio


class SlowProvider:
    """An agent double whose turn and whose open each wait to be let go — so a test can hold a
    turn *running* or a reopen *in progress* and act in the meantime."""

    def __init__(self) -> None:
        self.let_turn_finish = asyncio.Event()
        self.let_open_finish = asyncio.Event()
        self.let_open_finish.set()
        self.turn_started = asyncio.Event()
        self.opened = 0
        self.sessions: list[SlowProvider._Session] = []
        self.session_id = "slow"

    class _Session:
        def __init__(self, agent: SlowProvider, number: int) -> None:
            self.agent = agent
            self.number = number
            self.prompts: list[str] = []
            self.session_id = "slow"

        async def turn(self, prompt: str) -> Turn:
            self.prompts.append(prompt)
            self.agent.turn_started.set()
            await self.agent.let_turn_finish.wait()
            return Turn(text=f"answered on session {self.number}")

        async def close(self) -> None:
            pass

        async def steer(self, text: str) -> bool:
            return False

        async def interrupt(self) -> bool:
            return False

    async def open(self, **_kw: Any) -> AgentSession:
        await self.let_open_finish.wait()
        self.opened += 1
        session = SlowProvider._Session(self, self.opened)
        self.sessions.append(session)
        return cast(AgentSession, session)


def _ports() -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


async def _thread(tmp_path: Path, agent: SlowProvider) -> Thread:
    return await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(),
        store=InMemoryThreads(),
        root=tmp_path / "work",
        lease=Lease(Ceiling(20, 600, None), Floor(0)),
        approvals=Approvals(),
        mode="workspace-write",
    )


async def _drain(thread: Thread, text: str) -> list[Any]:
    return [e async for e in thread.turn(text)]


async def test_set_mode_during_a_running_turn_is_refused_typed_and_the_turn_is_untouched(
    tmp_path: Path,
) -> None:
    agent = SlowProvider()
    thread = await _thread(tmp_path, agent)
    try:
        running = asyncio.create_task(_drain(thread, "take your time"))
        with anyio.fail_after(10):
            await agent.turn_started.wait()
        assert thread.turning
        # Bounded: a `set_mode` that *waited* for the turn instead of refusing would hang here.
        with anyio.fail_after(5), pytest.raises(TurnRunning) as refused:
            await thread.set_mode("read-only")
        assert refused.value.thread_id == thread.id
        assert refused.value.turn_id == thread.record.turns[-1].id
        assert thread.record.mode == "workspace-write", "nothing changed"
        assert agent.opened == 1, "the provider was not reopened under the turn"
        agent.let_turn_finish.set()
        with anyio.fail_after(10):
            await running
        assert thread.record.turns[-1].outcome == "completed"
        assert thread.record.turns[-1].text == "answered on session 1"
    finally:
        await thread.close()


async def test_add_root_during_a_running_turn_is_refused_typed(tmp_path: Path) -> None:
    agent = SlowProvider()
    (tmp_path / "other").mkdir()
    thread = await _thread(tmp_path, agent)
    try:
        running = asyncio.create_task(_drain(thread, "take your time"))
        with anyio.fail_after(10):
            await agent.turn_started.wait()
        with anyio.fail_after(5), pytest.raises(TurnRunning) as refused:
            await thread.add_root("other", tmp_path / "other")
        assert refused.value.turn_id == thread.record.turns[-1].id
        assert [r.name for r in thread.workspace.roots] == [thread.workspace.roots[0].name]
        agent.let_turn_finish.set()
        with anyio.fail_after(10):
            await running
        assert thread.record.turns[-1].outcome == "completed"
    finally:
        await thread.close()


async def test_a_turn_arriving_during_a_mode_change_waits_and_runs_on_the_new_session(
    tmp_path: Path,
) -> None:
    """The change holds the turn lock: a turn asked for while the provider is being reopened
    neither races the reopen nor is refused — it waits, then runs on the reopened session."""
    agent = SlowProvider()
    agent.let_turn_finish.set()
    thread = await _thread(tmp_path, agent)
    try:
        agent.let_open_finish.clear()  # the reopen inside set_mode will hang until released
        changing = asyncio.create_task(thread.set_mode("read-only"))
        await asyncio.sleep(0.05)  # set_mode is now waiting inside the provider's open()
        assert not changing.done()
        turning = asyncio.create_task(_drain(thread, "while changing"))
        await asyncio.sleep(0.05)
        assert not turning.done(), "the turn waits for the change to finish"
        assert agent.sessions[-1].prompts == [], "nothing ran on the old session"
        agent.let_open_finish.set()
        with anyio.fail_after(10):
            await changing
            await turning
        assert agent.opened == 2
        assert agent.sessions[1].prompts == ["while changing"], "the turn ran on the new session"
        assert thread.record.mode == "read-only"
    finally:
        await thread.close()


class SlowThreads(ScriptedThreads):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(tmp_path)
        self.agent: Any = SlowProvider()

    async def open(
        self, *, root: str, mode: str, want: str | None, name: str, observer: Any, roots: Any = None
    ) -> Thread:
        return await Thread.open(
            agent=cast(Any, self.agent),
            ports=Ports(
                model=None,
                components=(InMemoryComponents([]),),
                governance=AllowAll(),
                sink=ListSink(),
                clock=_OwnIds(),
                observer=observer,
            ),
            store=self.threads,
            root=root or str(self._tmp),
            lease=Lease(Ceiling(20, 600, None), Floor(0)),
            name=name,
            approvals=self.approvals,
            mode=mode,
            provider="scripted",
        )


async def test_over_the_wire_the_refusal_is_the_typed_turn_running(tmp_path: Path) -> None:
    from shadow_hdk.wire.peer import RemoteError

    threads = SlowThreads(tmp_path)
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        started = await host.peer.call(
            "thread/start", {"root": str(tmp_path), "mode": "workspace-write"}
        )
        turning = asyncio.create_task(
            host.peer.call("turn/start", {"thread_id": started["thread_id"], "text": "slow"})
        )
        with anyio.fail_after(10):
            await threads.agent.turn_started.wait()
        with anyio.fail_after(5), pytest.raises(RemoteError) as refused:
            await host.peer.call(
                "thread/set_mode", {"thread_id": started["thread_id"], "mode": "read-only"}
            )
        assert refused.value.data["kind"] == "turn_running"
        assert refused.value.data["turn_id"]
        threads.agent.let_turn_finish.set()
        with anyio.fail_after(10):
            done = await turning
        assert done["turn"]["outcome"] == "completed"
        await host.peer.call("thread/close", {"thread_id": started["thread_id"]})
