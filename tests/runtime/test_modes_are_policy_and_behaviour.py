"""A mode is a policy, a behaviour and a presentation, chosen live (D64).

The policy half — what runs, what asks, what is refused — is `ModeGovernance` over effects, and it
was always the harness's. What was missing: the behaviour half (who the model is), the presentation
(id, name, description a host shows), and switching mid-thread. A `ModeRegistry` holds `ModeSpec`s
as data (shipped, and a store later); `Thread.set_mode` changes which the run is judged by *and*
reopens the provider with the new behaviour; the change is on the record.

The three defaults — looking, confined, open — are shipped by the harness, derived from the
environment's mode, not written out in an example.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from shadow_hdk.adapters.modes import ModeRegistry, ModeSpec, governance_for, shipped_modes

from shadow_hdk.kernel import Behaviour, Ceiling, Floor, Lease, Turn
from shadow_hdk.kernel.events import ModeChanged
from shadow_hdk.kernel.ports import AgentSession
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)
from shadow_hdk.runtime.threads import InMemoryThreads, Thread

pytestmark = pytest.mark.anyio

WORK = make_registration("work")


class RecordingAgent:
    """Remembers the behaviour it was opened with, each time it is opened."""

    def __init__(self) -> None:
        self.behaviours: list[Behaviour | None] = []
        self.opened = 0
        self.session_id: str | None = None
        """What the provider's session says its id is, when it has one."""
        self.resumed: list[str] = []
        """The session ids each open was told to resume (D76)."""

    async def open(
        self,
        *,
        tools: Any = (),
        workspace: Any = None,
        behaviour: Behaviour | None = None,
        resume: str | None = None,
    ) -> AgentSession:
        self.opened += 1
        self.behaviours.append(behaviour)
        if resume:
            self.resumed.append(resume)
        return cast(AgentSession, _Session(self.session_id))


class _Session:
    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id

    async def turn(self, prompt: str) -> Turn:
        return Turn(text="ok")

    async def close(self) -> None:
        pass

    async def stream(self, prompt: str) -> Any:  # pragma: no cover
        raise NotImplementedError
        yield


def test_shipped_modes_are_the_four_defaults_with_a_presentation() -> None:
    registry = ModeRegistry(shipped_modes())
    by_id = {m.id: m for m in registry.listing()}
    assert set(by_id) == {"read-only", "ask", "workspace-write", "full"}
    assert by_id["read-only"].name and by_id["read-only"].description
    # the policy half is real: read-only refuses a write, full permits it (asking)
    assert by_id["read-only"].policy.ceiling.writes.names == frozenset({"provider-state"})
    assert by_id["full"].policy.ask_above is not None


async def test_the_ask_mode_asks_before_every_write_and_allows_a_read() -> None:
    """The mode every coding CLI opens in (Claude Code's *default*, Codex's *on-request*): the
    workspace is the ceiling, and anything that writes or runs inside it is asked about first —
    a person approves once, or keeps a rule (D65)."""
    from shadow_hdk.kernel import EffectProfile, ScopeSet
    from shadow_hdk.kernel.ports import Allow, Ask, Context, Refuse

    governance = governance_for(ModeRegistry(shipped_modes()), default="ask")
    context = Context(run_id="r", step="s", attributes={"mode": "ask"})
    read = EffectProfile(reads=ScopeSet(everything=True), contained=True)
    write = EffectProfile(
        reads=ScopeSet(everything=True), writes=ScopeSet.of("workspace"), contained=True
    )
    run = EffectProfile(
        reads=ScopeSet(everything=True),
        writes=ScopeSet.of("workspace"),
        reversible=False,
        contained=True,
    )
    outside = EffectProfile(reads=ScopeSet(everything=True), writes=ScopeSet(everything=True))
    assert isinstance(await governance.judge(read, context), Allow)
    assert isinstance(await governance.judge(write, context), Ask)
    assert isinstance(await governance.judge(run, context), Ask)
    assert isinstance(await governance.judge(outside, context), Refuse), "outside is the ceiling"


def test_a_registry_finds_a_mode_and_a_missing_one_is_none() -> None:
    registry = ModeRegistry(shipped_modes())
    assert registry.get("full") is not None
    assert registry.get("nope") is None


def _ports(governance: Any) -> Ports:
    async def work(_inputs: Any) -> Any:
        from shadow_hdk.kernel import Completed

        return Completed({})

    return Ports(
        model=None,
        components=(InMemoryComponents([(WORK, work)]),),
        governance=governance,
        sink=ListSink(),
        clock=FixedClock(),
    )


async def _thread(agent: RecordingAgent, tmp_path: Path, registry: ModeRegistry) -> Thread:
    from shadow_hdk.adapters.modes import governance_for

    return await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(governance_for(registry, default="workspace-write")),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
        modes=registry,
        mode="workspace-write",
    )


async def test_set_mode_reopens_the_provider_with_the_new_behaviour(tmp_path: Path) -> None:
    registry = ModeRegistry(
        (
            ModeSpec.of("workspace-write", behaviour=Behaviour(model="sonnet")),
            ModeSpec.of(
                "full",
                name="Full",
                description="the machine",
                behaviour=Behaviour(model="opus", effort="high"),
            ),
        )
    )
    agent = RecordingAgent()
    thread = await _thread(agent, tmp_path, registry)
    try:
        assert agent.behaviours[-1] == Behaviour(model="sonnet")
        events = await thread.set_mode("full")
        assert agent.opened == 2, "changing the behaviour reopens the provider session"
        assert agent.behaviours[-1] == Behaviour(model="opus", effort="high")
    finally:
        await thread.close()
    assert [e.mode for e in events if isinstance(e, ModeChanged)] == ["full"]
    assert thread.record.mode == "full"


async def test_set_mode_changes_which_policy_judges_the_next_turn(tmp_path: Path) -> None:
    registry = ModeRegistry(shipped_modes())
    agent = RecordingAgent()
    thread = await _thread(agent, tmp_path, registry)
    try:
        await thread.set_mode("read-only")
        # the run is now judged read-only; a turn that only talks still runs (its writes are
        # the provider's own state), and the mode on the record is read-only.
        [e async for e in thread.turn("hello")]
    finally:
        await thread.close()
    assert thread.record.mode == "read-only"
    assert thread.record.turns[-1].outcome == "completed"


async def test_set_mode_to_an_unknown_mode_is_refused_and_changes_nothing(tmp_path: Path) -> None:
    registry = ModeRegistry(shipped_modes())
    agent = RecordingAgent()
    thread = await _thread(agent, tmp_path, registry)
    try:
        with pytest.raises(KeyError):
            await thread.set_mode("banana")
        assert thread.record.mode == "workspace-write", "a bad set_mode leaves the mode alone"
        assert agent.opened == 1, "and does not reopen the provider"
    finally:
        await thread.close()


async def test_set_mode_reopens_the_provider_on_its_own_session(tmp_path: Path) -> None:
    """A mode change reopens the provider (D76): the catalogue a resident CLI holds is the old
    mode's, and it was measured to keep it after `list_changed` (BUG-032); a fresh process lists
    again, and is resumed on the provider's own session id so it keeps its memory. Setting the
    mode it already has changes nothing and reopens nothing."""
    registry = ModeRegistry(
        (
            ModeSpec.of("workspace-write", behaviour=Behaviour(model="sonnet")),
            ModeSpec.of("read-only", behaviour=Behaviour(model="sonnet")),
        )
    )
    agent = RecordingAgent()
    thread = await _thread(agent, tmp_path, registry)
    try:
        changed = await thread.set_mode("read-only")
        assert agent.opened == 2, "reopened, so the provider lists the new mode's tools"
        assert [e.kind for e in changed] == ["mode_changed"], "a policy change is still a change"
        again = await thread.set_mode("read-only")
        assert again == [] and agent.opened == 2, "the mode it already has: nothing, no reopen"
    finally:
        await thread.close()
    assert thread.record.mode == "read-only"


async def test_a_reopen_hands_the_providers_session_id_back(tmp_path: Path) -> None:
    """The session says its id; the record keeps it; the next open is told to resume it."""
    registry = ModeRegistry((ModeSpec.of("workspace-write"), ModeSpec.of("read-only")))
    agent = RecordingAgent()
    agent.session_id = "claude-abc"
    thread = await _thread(agent, tmp_path, registry)
    try:
        [_ async for _ in thread.turn("hello")]
        assert thread.record.session_id == "claude-abc", "remembered after the turn"
        await thread.set_mode("read-only")
        assert agent.resumed == ["claude-abc"], "the reopen was told which session to resume"
    finally:
        await thread.close()
