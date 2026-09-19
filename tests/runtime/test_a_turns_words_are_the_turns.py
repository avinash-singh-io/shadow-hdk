"""A turn's words are the turn's (ENH-037, D140).

`Thread.open(attributes=)` put the product's words on every judgement (D82); `resume` rebuilt
from the record's alone and `turn` took none, so a fact the product learnt after opening — the
workspace, the run in scope — never reached a judgement, and a rule scoped by it *asked* where it
should have *allowed* (measured by the product on kit 0.31). Now `turn(attributes=)` merges the
turn's words over the record's for that turn's judgements — and only that turn's; they are never
written back. `resume(attributes=)` replaces the record's words, and the record shows it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.kernel import Ceiling, Completed, EffectProfile, Floor, Lease, ScopeSet, Turn
from shadow_hdk.kernel.ports import AgentSession, Allow, Context, Judgement, ToolSource
from shadow_hdk.runtime import Approvals, Ports
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink, make_registration
from shadow_hdk.runtime.threads import InMemoryThreads, Thread

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
WRITE = make_registration("write_file", effects=EffectProfile(writes=WORKSPACE, reversible=False))


class Seen:
    def __init__(self) -> None:
        self.contexts: list[Context] = []

    async def judge(self, _effects: EffectProfile, context: Context) -> Judgement:
        self.contexts.append(context)
        return Allow()

    def words_at(self, step_prefix: str) -> list[dict[str, Any]]:
        return [dict(c.attributes) for c in self.contexts if c.step.startswith(step_prefix)]


class Agent:
    def __init__(self) -> None:
        self.reach: Any = None

    async def open(self, *, tools: tuple[ToolSource, ...] = (), **_: Any) -> AgentSession:
        agent = self

        class _Session:
            async def turn(self, prompt: str) -> Turn:
                await agent.reach("write_file", {"path": "a.txt"})
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


async def _open(tmp_path: Path, seen: Seen, agent: Agent, store: InMemoryThreads) -> Thread:
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(seen),
        store=store,
        root=tmp_path,
        lease=_lease(),
        approvals=Approvals(),
        principal="alice",
        attributes={"tenant": "acme"},
    )
    agent.reach = thread.registry.call
    return thread


async def test_the_turns_words_reach_that_turns_judgements_and_not_the_next(
    tmp_path: Path,
) -> None:
    seen, agent, store = Seen(), Agent(), InMemoryThreads()
    thread = await _open(tmp_path, seen, agent, store)
    try:
        [e async for e in thread.turn("one", attributes={"workspace": "w-1"})]
        first_tool = seen.words_at("tools__write_file")
        assert first_tool and all(w.get("workspace") == "w-1" for w in first_tool)
        assert all(w.get("tenant") == "acme" for w in first_tool), "merged over the record's"

        seen.contexts.clear()
        await thread.tools()  # the catalogue judged between turns: the turn's words are gone
        assert seen.contexts and all("workspace" not in c.attributes for c in seen.contexts)

        seen.contexts.clear()
        [e async for e in thread.turn("two")]
        second_tool = seen.words_at("tools__write_file")
        assert second_tool and all("workspace" not in w for w in second_tool), (
            "a turn's words are the turn's — never written back"
        )
        assert thread.record.attributes == {"tenant": "acme"}
        kept = await store.get(thread.id)
        assert kept is not None and kept.attributes == {"tenant": "acme"}
    finally:
        await thread.close()


async def test_the_turns_words_override_the_records_for_that_turn(tmp_path: Path) -> None:
    seen, agent, store = Seen(), Agent(), InMemoryThreads()
    thread = await _open(tmp_path, seen, agent, store)
    try:
        [e async for e in thread.turn("one", attributes={"tenant": "other"})]
        assert seen.words_at("tools__write_file")[0]["tenant"] == "other"
        assert thread.record.attributes["tenant"] == "acme"
    finally:
        await thread.close()


async def test_a_reserved_name_is_refused_on_a_turn_as_at_open(tmp_path: Path) -> None:
    seen, agent, store = Seen(), Agent(), InMemoryThreads()
    thread = await _open(tmp_path, seen, agent, store)
    try:
        with pytest.raises(ValueError, match="runtime's own"):
            [e async for e in thread.turn("one", attributes={"mode": "full"})]
        assert not thread.record.turns or thread.record.turns[-1].outcome != "completed"
    finally:
        await thread.close()


async def test_resume_with_words_replaces_the_records_and_the_record_says_so(
    tmp_path: Path,
) -> None:
    seen, agent, store = Seen(), Agent(), InMemoryThreads()
    thread = await _open(tmp_path, seen, agent, store)
    await thread.close()

    again, agent2 = Seen(), Agent()
    resumed = await Thread.resume(
        thread.id,
        agent=cast(Any, agent2),
        ports=_ports(again),
        store=store,
        lease=_lease(),
        attributes={"tenant": "acme", "workspace": "w-2"},
    )
    agent2.reach = resumed.registry.call
    try:
        assert resumed.record.attributes == {"tenant": "acme", "workspace": "w-2"}
        kept = await store.get(thread.id)
        assert kept is not None and kept.attributes["workspace"] == "w-2", "durable"
        [e async for e in resumed.turn("again")]
        assert all(w.get("workspace") == "w-2" for w in again.words_at("tools__write_file"))
    finally:
        await resumed.close()


async def test_resume_without_words_keeps_the_records(tmp_path: Path) -> None:
    seen, agent, store = Seen(), Agent(), InMemoryThreads()
    thread = await _open(tmp_path, seen, agent, store)
    await thread.close()

    resumed = await Thread.resume(
        thread.id, agent=cast(Any, Agent()), ports=_ports(Seen()), store=store, lease=_lease()
    )
    try:
        assert resumed.record.attributes == {"tenant": "acme"}
    finally:
        await resumed.close()


async def test_an_attribute_named_mode_cannot_switch_the_policy(tmp_path: Path) -> None:
    """BUG-061: `mode` is the key the shipped governance selects its policy by, and the
    conversation writes it onto every judgement — a host's attribute of that name overrode it,
    so a `read-only` thread was judged as `full`. Refused at open, at a turn, at a resume."""
    seen, agent, store = Seen(), Agent(), InMemoryThreads()
    with pytest.raises(ValueError, match="mode"):
        await Thread.open(
            agent=cast(Any, agent),
            ports=_ports(seen),
            store=store,
            root=tmp_path,
            lease=_lease(),
            approvals=Approvals(),
            mode="read-only",
            attributes={"mode": "full"},
        )
    thread = await _open(tmp_path, seen, agent, store)
    try:
        with pytest.raises(ValueError, match="thread"):
            [e async for e in thread.turn("x", attributes={"thread": "other"})]
    finally:
        await thread.close()
    with pytest.raises(ValueError, match="turn"):
        await Thread.resume(
            thread.id,
            agent=cast(Any, Agent()),
            ports=_ports(Seen()),
            store=store,
            lease=_lease(),
            attributes={"turn": "t-9"},
        )
