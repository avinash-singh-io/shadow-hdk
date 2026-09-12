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
from shadow_hdk.adapters.modes import ModeRegistry, ModeSpec, shipped_modes

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

    async def open(
        self, *, tools: Any = (), workspace: Any = None, behaviour: Behaviour | None = None
    ) -> AgentSession:
        self.opened += 1
        self.behaviours.append(behaviour)
        return cast(AgentSession, _Session())


class _Session:
    async def turn(self, prompt: str) -> Turn:
        return Turn(text="ok")

    async def close(self) -> None:
        pass

    async def stream(self, prompt: str) -> Any:  # pragma: no cover
        raise NotImplementedError
        yield


def test_shipped_modes_are_the_three_defaults_with_a_presentation() -> None:
    registry = ModeRegistry(shipped_modes())
    by_id = {m.id: m for m in registry.listing()}
    assert set(by_id) == {"read-only", "workspace-write", "full"}
    assert by_id["read-only"].name and by_id["read-only"].description
    # the policy half is real: read-only refuses a write, full permits it (asking)
    assert by_id["read-only"].policy.ceiling.writes.names == frozenset({"provider-state"})
    assert by_id["full"].policy.ask_above is not None


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


async def test_set_mode_with_the_same_behaviour_does_not_reopen(tmp_path: Path) -> None:
    """Only a *behaviour* change reopens the provider; a policy-only change is a context flip."""
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
        assert agent.opened == 1, "same behaviour, same session"
        assert [e.kind for e in changed] == ["mode_changed"], "a policy change is still a change"
        again = await thread.set_mode("read-only")
        assert again == [], "setting the mode it already has changes nothing, so records nothing"
    finally:
        await thread.close()
    assert thread.record.mode == "read-only"
