"""Identity on the thread (Phase 29 group 3, D82).

`Thread.open(principal=, attributes=)` puts who the thread is for, and the product's words about
it (a tenant, a workspace id), on the record — and on every judgement's context, so a governance
port sees them at the turn's own step, at every tool call the agent makes, and when the catalogue
is judged for `tools()`. A rule the person makes at a card is theirs: scoped to the principal who
answered. A mode out of the thread's scope cannot be set.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.adapters.modes import ActRules, Mode, ModeGovernance, ModeRegistry, ModeSpec
from shadow_hdk.kernel import Ceiling, Completed, EffectProfile, Floor, Lease, ScopeSet, Turn
from shadow_hdk.kernel.ports import AgentSession, Allow, Ask, Context, Judgement, ToolSource
from shadow_hdk.runtime import Approvals, ApproveAndAddRule, Ports
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink, make_registration
from shadow_hdk.runtime.threads import InMemoryThreads, Thread

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
WRITE = make_registration("write_file", effects=EffectProfile(writes=WORKSPACE, reversible=False))


class Seen:
    """A governance port that keeps every context it judged."""

    def __init__(self) -> None:
        self.contexts: list[Context] = []

    async def judge(self, _effects: EffectProfile, context: Context) -> Judgement:
        self.contexts.append(context)
        return Allow()


class Agent:
    def __init__(self, calls: list[tuple[str, dict[str, Any]]]) -> None:
        self.calls = calls
        self.reach: Any = None

    async def open(self, *, tools: tuple[ToolSource, ...] = (), **_: Any) -> AgentSession:
        agent = self

        class _Session:
            async def turn(self, prompt: str) -> Turn:
                for name, arguments in agent.calls:
                    await agent.reach(name, arguments)
                return Turn(text="done")

            async def close(self) -> None:
                pass

            async def stream(self, prompt: str) -> AsyncIterator[Any]:  # pragma: no cover
                raise NotImplementedError
                yield

        return cast(AgentSession, _Session())


async def write(_inputs: Any) -> Any:
    return Completed({"wrote": True})


def _ports(governance: Any) -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(WRITE, write)]),),
        governance=governance,
        sink=ListSink(),
        clock=FixedClock(),
    )


def _lease() -> Lease:
    return Lease(Ceiling(40, 600, None), Floor(0))


async def test_the_principal_and_attributes_are_on_the_record_and_every_judgement(
    tmp_path: Path,
) -> None:
    seen = Seen()
    agent = Agent([("write_file", {"path": "a.txt"})])
    store = InMemoryThreads()
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(seen),
        store=store,
        root=tmp_path,
        lease=_lease(),
        principal="alice",
        attributes={"tenant": "acme", "workspace": "w-1"},
    )
    agent.reach = thread.registry.call
    try:
        assert thread.record.principal == "alice"
        assert thread.record.attributes == {"tenant": "acme", "workspace": "w-1"}
        kept = await store.get(thread.id)
        assert kept is not None and kept.principal == "alice"

        [e async for e in thread.turn("go")]
        steps = {c.step for c in seen.contexts}
        assert "turn-1" in steps and any(s.startswith("tools__write_file") for s in steps)
        for context in seen.contexts:
            assert context.principal == "alice", context
            assert context.attributes["tenant"] == "acme", context
            assert context.attributes["workspace"] == "w-1", context

        seen.contexts.clear()
        await thread.tools()
        assert seen.contexts and all(c.principal == "alice" for c in seen.contexts)
        assert all(c.attributes.get("tenant") == "acme" for c in seen.contexts)
    finally:
        await thread.close()


async def test_a_resumed_thread_keeps_its_identity(tmp_path: Path) -> None:
    seen = Seen()
    store = InMemoryThreads()
    thread = await Thread.open(
        agent=cast(Any, Agent([])),
        ports=_ports(seen),
        store=store,
        root=tmp_path,
        lease=_lease(),
        principal="alice",
        attributes={"tenant": "acme"},
    )
    await thread.close()
    again = Seen()
    resumed = await Thread.resume(
        thread.id, agent=cast(Any, Agent([])), ports=_ports(again), store=store, lease=_lease()
    )
    try:
        [e async for e in resumed.turn("again")]
        assert again.contexts and all(c.principal == "alice" for c in again.contexts)
        assert all(c.attributes.get("tenant") == "acme" for c in again.contexts)
    finally:
        await resumed.close()


async def test_a_reserved_attribute_is_refused_at_open(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="component"):
        await Thread.open(
            agent=cast(Any, Agent([])),
            ports=_ports(Seen()),
            store=InMemoryThreads(),
            root=tmp_path,
            lease=_lease(),
            attributes={"component": "x"},
        )


async def test_a_rule_made_at_a_card_is_the_answerers(tmp_path: Path) -> None:
    """Approve-and-add-rule from alice's card writes a rule scoped to alice: bob's thread is
    still asked."""
    everything = ScopeSet(everything=True)
    asking = Mode(
        "asking",
        ceiling=EffectProfile(
            reads=everything, writes=everything, reaches=True, reversible=False, costs=True
        ),
        # The turn's own step — reaching, costing, writing the provider's state — is under the
        # line; a write to the workspace is above it and asked about.
        ask_above=EffectProfile(
            reads=everything,
            writes=ScopeSet.of("provider-state"),
            reaches=True,
            reversible=False,
            costs=True,
        ),
    )
    rules = ActRules()
    governance = ModeGovernance({"asking": asking}, default="asking", rules=rules)
    approvals = Approvals()
    store = InMemoryThreads()

    async def turn_as(principal: str) -> list[Any]:
        agent = Agent([("write_file", {"path": "a.txt"})])
        thread = await Thread.open(
            agent=cast(Any, agent),
            ports=_ports(governance),
            store=store,
            root=tmp_path,
            lease=_lease(),
            approvals=approvals,
            rules=rules,
            mode="asking",
            principal=principal,
        )
        agent.reach = thread.registry.call
        try:
            return [e async for e in thread.turn("write")]
        finally:
            await thread.close()

    async def answer_with_a_rule() -> None:
        asked = await approvals.next()
        approvals.answer(asked.handle, ApproveAndAddRule({"component": "write_file"}))

    answering = asyncio.create_task(answer_with_a_rule())
    await asyncio.wait_for(turn_as("alice"), 30)
    await answering
    (rule,) = rules.all()
    assert rule.scope == "alice", "the person who answered"

    asked_again: list[Any] = []

    async def bob_is_asked() -> None:
        asked = await approvals.next()
        asked_again.append(asked)
        approvals.answer(asked.handle, {"kind": "deny"})

    watching = asyncio.create_task(bob_is_asked())
    await asyncio.wait_for(turn_as("bob"), 30)
    await asyncio.wait_for(watching, 5)
    assert asked_again, "alice's rule did not speak for bob"

    alone: list[Any] = []

    async def nobody_asks() -> None:
        alone.append(await approvals.next())

    silent = asyncio.create_task(nobody_asks())
    await asyncio.wait_for(turn_as("alice"), 30)
    await asyncio.sleep(0.05)
    silent.cancel()
    assert not alone, "alice is not asked again"


async def test_a_mode_out_of_scope_cannot_be_set(tmp_path: Path) -> None:
    registry = ModeRegistry(
        [
            ModeSpec.of("open", environment="full"),
            ModeSpec.of("acme-only", environment="full", scope="tenant:acme"),
        ]
    )
    governance = ModeGovernance(registry, default="open")
    thread = await Thread.open(
        agent=cast(Any, Agent([])),
        ports=_ports(governance),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=_lease(),
        modes=registry,
        mode="open",
        principal="bob",
        attributes={"tenant": "beta"},
    )
    try:
        with pytest.raises(KeyError, match="acme-only"):
            await thread.set_mode("acme-only")
        assert thread.record.mode == "open"
    finally:
        await thread.close()
    acme = await Thread.open(
        agent=cast(Any, Agent([])),
        ports=_ports(governance),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=_lease(),
        modes=registry,
        mode="open",
        principal="bob",
        attributes={"tenant": "acme"},
    )
    try:
        await acme.set_mode("acme-only")
        assert acme.record.mode == "acme-only"
    finally:
        await acme.close()


def _unused(_: Ask) -> None:  # pragma: no cover — keeps the import honest for readers
    return None
