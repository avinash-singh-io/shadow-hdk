"""A thread is the durable container; each turn is one run; the agent's tool calls are child steps
under the turn (D62).

Every product has this shape — Codex's thread/turn/item, the OpenAI Assistants API's
thread/run/step — and ours lived in an example. Now `Thread` is the harness's: it opens a
provider session once and holds it across turns, serves the run's registry to it for the thread's
lifetime under the host's name, runs each turn as its own run under a ceiling carved from the
thread's lease, and keeps the record through a `ThreadStore` the host may replace or ignore.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.kernel import (
    Ceiling,
    EffectProfile,
    Ended,
    Event,
    Floor,
    Invoked,
    Lease,
    ScopeSet,
    Started,
    ToolSource,
    Turn,
)
from shadow_hdk.kernel.ports import AgentSession, Allow, Context, Judgement
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)
from shadow_hdk.runtime.threads import InMemoryThreads, Thread
from tests.adapters.contract.suites import ComponentPortContract, ThreadStoreContract

pytestmark = pytest.mark.anyio

LOOK = make_registration("look", effects=EffectProfile(reads=ScopeSet.of("workspace")))
Reach = Callable[[str, dict[str, Any]], Awaitable[Any]]


class ScriptedAgent:
    """A provider double: each turn calls the tools it was scripted to, through the registry the
    thread served it — the way a CLI does through the relay — then says its line."""

    def __init__(self, turns: list[tuple[list[tuple[str, dict[str, Any]]], str]]) -> None:
        self.turns = list(turns)
        self.reach: Reach | None = None
        self.opened_with: tuple[ToolSource, ...] = ()
        self.closed = 0

    async def open(
        self,
        *,
        tools: tuple[ToolSource, ...] = (),
        workspace: str | None = None,
        behaviour: Any = None,
    ) -> AgentSession:
        self.opened_with = tools
        self.behaviour = behaviour
        return cast(AgentSession, _ScriptedSession(self))


class _ScriptedSession:
    def __init__(self, agent: ScriptedAgent) -> None:
        self.agent = agent

    async def turn(self, prompt: str) -> Turn:
        calls, line = self.agent.turns.pop(0)
        assert self.agent.reach is not None
        for name, arguments in calls:
            await self.agent.reach(name, arguments)
        return Turn(text=line, reasoning="thinking about " + prompt)

    async def close(self) -> None:
        self.agent.closed += 1

    async def stream(self, prompt: str) -> AsyncIterator[Any]:  # pragma: no cover
        raise NotImplementedError
        yield  # noqa: RET503 — an async generator's shape


class AllowAll:
    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        return Allow()


async def look(_inputs: Any) -> Any:
    from shadow_hdk.kernel import Completed

    return Completed({"found": 1})


def ports() -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(LOOK, look)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


def a_lease(steps: int = 40) -> Lease:
    return Lease(Ceiling(steps, 600, None), Floor(0))


async def open_thread(
    agent: ScriptedAgent, store: InMemoryThreads, tmp_path: Path, **kw: Any
) -> Thread:
    thread = await Thread.open(
        agent=cast(Any, agent), ports=ports(), store=store, root=tmp_path, lease=a_lease(), **kw
    )
    agent.reach = thread.registry.call
    return thread


async def test_each_turn_is_its_own_run_and_the_thread_remembers_it(tmp_path: Path) -> None:
    agent = ScriptedAgent([([("look", {})], "one"), ([], "two")])
    store = InMemoryThreads()
    thread = await open_thread(agent, store, tmp_path)
    try:
        first = [e async for e in thread.turn("first?")]
        second = [e async for e in thread.turn("second?")]
    finally:
        await thread.close()

    runs = {e.run_id for e in first if isinstance(e, Started)}
    assert len(runs) == 2, "a turn is one run, and its tool call is a child run"
    assert {e.run_id for e in second if isinstance(e, Started)}.isdisjoint(runs)
    record = await store.get(thread.id)
    assert record is not None
    assert [t.prompt for t in record.turns] == ["first?", "second?"]
    assert [t.text for t in record.turns] == ["one", "two"]
    assert all(t.outcome == "completed" for t in record.turns)
    assert record.turns[0].run_id == next(
        e.run_id for e in first if isinstance(e, Invoked) and e.step == "turn-1"
    )


async def test_the_agents_tool_call_is_a_child_step_under_the_turn(tmp_path: Path) -> None:
    from shadow_hdk.runtime.items import items

    agent = ScriptedAgent([([("look", {})], "done")])
    thread = await open_thread(agent, InMemoryThreads(), tmp_path)
    try:
        events = [e async for e in thread.turn("look")]
    finally:
        await thread.close()

    top = [i for i in items(events)]
    assert [i.step for i in top] == ["turn-1"]
    assert [c.component for c in top[0].children] == ["look"], "the tool call folds under the turn"
    assert "thinking about look" in top[0].reasoning


async def test_the_registry_is_served_under_the_hosts_name(tmp_path: Path) -> None:
    agent = ScriptedAgent([([("look", {})], "ok")])
    thread = await open_thread(agent, InMemoryThreads(), tmp_path, name="workspace")
    try:
        events = [e async for e in thread.turn("go")]
    finally:
        await thread.close()

    child_steps = [e.step for e in events if isinstance(e, Invoked) and e.component == "look"]
    assert child_steps == ["workspace__look__1"]
    assert agent.opened_with == (), "an in-process offer hands the agent no tool source"
    assert thread.registry.name == "workspace"


async def test_the_turn_itself_is_withheld_from_the_agent(tmp_path: Path) -> None:
    """The step holding the conversation is not a tool the agent may call back into."""
    agent = ScriptedAgent([([("turn", {"prompt": "again"})], "tried")])
    thread = await open_thread(agent, InMemoryThreads(), tmp_path)
    try:
        events = [e async for e in thread.turn("go")]
    finally:
        await thread.close()

    assert not [e for e in events if isinstance(e, Invoked) and e.step.endswith("__turn__1")]


async def test_turns_draw_on_one_lease_and_a_spent_thread_refuses_a_turn(tmp_path: Path) -> None:
    agent = ScriptedAgent([([], "a"), ([], "b"), ([], "c")])
    store = InMemoryThreads()
    thread = await Thread.open(
        agent=cast(Any, agent), ports=ports(), store=store, root=tmp_path, lease=a_lease(steps=2)
    )
    agent.reach = thread.registry.call
    try:
        [e async for e in thread.turn("1")]
        [e async for e in thread.turn("2")]
        assert thread.remaining().ceiling.max_steps == 0
        with pytest.raises(Exception, match="no steps left"):
            [e async for e in thread.turn("3")]
    finally:
        await thread.close()


async def test_a_thread_resumes_from_its_store_and_the_provider_is_reopened(tmp_path: Path) -> None:
    store = InMemoryThreads()
    first_agent = ScriptedAgent([([], "hello")])
    thread = await open_thread(first_agent, store, tmp_path)
    [e async for e in thread.turn("hi")]
    await thread.close()
    assert first_agent.closed == 1

    second_agent = ScriptedAgent([([], "again")])
    resumed = await Thread.resume(
        thread.id, agent=cast(Any, second_agent), ports=ports(), store=store, lease=a_lease()
    )
    second_agent.reach = resumed.registry.call
    try:
        [e async for e in resumed.turn("more")]
    finally:
        await resumed.close()
    record = await store.get(thread.id)
    assert record is not None and [t.prompt for t in record.turns] == ["hi", "more"]


async def test_fork_rollback_list_and_archive(tmp_path: Path) -> None:
    store = InMemoryThreads()
    agent = ScriptedAgent([([], "a"), ([], "b"), ([], "c")])
    thread = await open_thread(agent, store, tmp_path)
    try:
        for prompt in ("1", "2", "3"):
            [e async for e in thread.turn(prompt)]
        forked = await thread.fork()
        rolled = await thread.rollback(to_turn=1)
    finally:
        await thread.close()

    assert forked.forked_from == thread.id and [t.prompt for t in forked.turns] == ["1", "2", "3"]
    assert rolled.forked_from == thread.id and [t.prompt for t in rolled.turns] == ["1"]
    assert rolled.seeded_turns == 1, (
        "a rollback says it was seeded, because the provider's own transcript cannot be rewound"
    )
    listed = await store.list()
    assert {t.id for t in listed} == {thread.id, forked.id, rolled.id}
    await store.archive(rolled.id)
    assert {t.id for t in await store.list()} == {thread.id, forked.id}
    assert {t.id for t in await store.list(include_archived=True)} == {
        thread.id,
        forked.id,
        rolled.id,
    }


def _ended(events: list[Event]) -> Ended:
    return [e for e in events if isinstance(e, Ended)][-1]


async def test_a_turn_that_ends_badly_is_recorded_as_such(tmp_path: Path) -> None:
    class Broken(ScriptedAgent):
        async def open(
            self, *, tools: Any = (), workspace: Any = None, behaviour: Any = None
        ) -> AgentSession:
            self.opened_with = tools
            return cast(AgentSession, _BrokenSession())

    class _BrokenSession:
        async def turn(self, prompt: str) -> Turn:
            raise RuntimeError("the provider fell over")

        async def close(self) -> None:
            pass

        async def stream(self, prompt: str) -> AsyncIterator[Any]:  # pragma: no cover
            raise NotImplementedError
            yield

    store = InMemoryThreads()
    thread = await Thread.open(
        agent=cast(Any, Broken([])), ports=ports(), store=store, root=tmp_path, lease=a_lease()
    )
    try:
        events = [e async for e in thread.turn("hi")]
    finally:
        await thread.close()
    assert _ended(events).reason == "completed", (
        "a component failing is a Failed observation, not a crash (D7)"
    )
    record = await store.get(thread.id)
    assert record is not None and record.turns[0].outcome == "failed"


async def test_the_turn_itself_writes_nothing_to_the_world(tmp_path: Path) -> None:
    """The turn step declares `writes: {provider-state}` and nothing wider. The bound it must
    not cross: the root, and everything outside it. A turn with no tool calls leaves the root
    exactly as it was — whatever the provider wrote, it wrote to its own state, not here — and a
    tool call that does write goes through the environment's component, judged and denied or
    allowed there, never through the turn."""
    (tmp_path / "before.txt").write_text("untouched")
    agent = ScriptedAgent([([], "said nothing to the world")])
    thread = await open_thread(agent, InMemoryThreads(), tmp_path)
    try:
        events = [e async for e in thread.turn("hello")]
    finally:
        await thread.close()

    assert sorted(p.name for p in tmp_path.iterdir()) == ["before.txt"]
    assert (tmp_path / "before.txt").read_text() == "untouched"
    turn = [e for e in events if isinstance(e, Invoked) and e.step == "turn-1"][0]
    from shadow_hdk.runtime.threads import TURN_EFFECTS

    assert TURN_EFFECTS.writes == ScopeSet.of("provider-state")
    assert turn.component == "turn"


class TestTheTurnComponentsIsAComponentPort(ComponentPortContract):
    """The one component a turn's run has of its own is held to the port's contract like any."""

    def port(self) -> Any:
        from shadow_hdk.kernel import Completed
        from shadow_hdk.runtime.threads import _turn_registration, _TurnComponents

        async def handler(_inputs: Any) -> Any:
            return Completed({"text": "ok"})

        return _TurnComponents(_turn_registration("2026-01-01T00:00:00+00:00"), handler, "t")

    def valid_call(self) -> tuple[str, Any]:
        return "turn", {"prompt": "hi"}


class TestInMemoryThreadsIsAThreadStore(ThreadStoreContract):
    def store(self) -> InMemoryThreads:
        return InMemoryThreads()


async def test_a_refused_turn_is_recorded_as_refused_with_the_reason(tmp_path: Path) -> None:
    """Measured live: a thread whose `mode` named a policy that did not exist had its first turn
    refused — and the record said `completed` with an empty answer. A refusal is an outcome."""

    class RefusesTurns:
        async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
            from shadow_hdk.kernel.ports import Refuse

            return Refuse("not this mode") if context.step.startswith("turn-") else Allow()

    agent = ScriptedAgent([([], "never said")])
    store = InMemoryThreads()
    base = ports()
    from dataclasses import replace as _replace_ports

    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_replace_ports(base, governance=RefusesTurns()),
        store=store,
        root=tmp_path,
        lease=a_lease(),
    )
    agent.reach = thread.registry.call
    try:
        [e async for e in thread.turn("hi")]
    finally:
        await thread.close()
    record = await store.get(thread.id)
    assert record is not None
    assert record.turns[0].outcome == "refused"
    assert "not this mode" in record.turns[0].text


class SteerableAgent(ScriptedAgent):
    """A provider that takes text mid-turn and can be told to stop."""

    def __init__(self, turns: Any) -> None:
        super().__init__(turns)
        self.steered: list[str] = []
        self.interrupted = 0
        self.release = asyncio.Event()

    async def open(
        self, *, tools: Any = (), workspace: Any = None, behaviour: Any = None
    ) -> AgentSession:
        self.opened_with = tools
        return cast(AgentSession, _SteerableSession(self))


class _SteerableSession(_ScriptedSession):
    def __init__(self, agent: SteerableAgent) -> None:
        super().__init__(agent)
        self.steerable = agent

    async def turn(self, prompt: str) -> Turn:
        await self.steerable.release.wait()  # a turn that takes its time
        return await super().turn(prompt)

    async def steer(self, text: str) -> bool:
        self.steerable.steered.append(text)
        return True

    async def interrupt(self) -> bool:
        self.steerable.interrupted += 1
        self.steerable.release.set()
        return True


async def test_steer_reaches_a_provider_that_takes_it_mid_turn(tmp_path: Path) -> None:
    agent = SteerableAgent([([], "fine")])
    thread = await open_thread(agent, InMemoryThreads(), tmp_path)
    try:
        turning = asyncio.ensure_future(_collect(thread.turn("start")))
        await asyncio.sleep(0.05)
        assert await thread.steer("also do this") is True
        agent.release.set()
        await turning
    finally:
        await thread.close()
    assert agent.steered == ["also do this"]


async def test_steer_with_no_turn_running_is_kept_for_the_next_turn(tmp_path: Path) -> None:
    agent = ScriptedAgent([([], "ok")])
    seen: list[str] = []
    original = _ScriptedSession.turn

    async def spying(self: Any, prompt: str) -> Turn:
        seen.append(prompt)
        return await original(self, prompt)

    _ScriptedSession.turn = spying  # type: ignore[method-assign]
    try:
        thread = await open_thread(agent, InMemoryThreads(), tmp_path)
        try:
            assert await thread.steer("remember this") is False
            [e async for e in thread.turn("now")]
        finally:
            await thread.close()
    finally:
        _ScriptedSession.turn = original  # type: ignore[method-assign]
    assert seen == ["remember this\n\nnow"], "the steer is folded into the next prompt"


async def test_interrupt_ends_the_running_turn_and_the_record_says_cancelled(
    tmp_path: Path,
) -> None:
    agent = SteerableAgent([([], "never finished")])
    store = InMemoryThreads()
    thread = await open_thread(agent, store, tmp_path)
    try:
        turning = asyncio.ensure_future(_collect(thread.turn("start")))
        await asyncio.sleep(0.05)
        await thread.interrupt()
        events = await turning
    finally:
        await thread.close()
    assert agent.interrupted == 1
    record = await store.get(thread.id)
    assert record is not None
    assert record.turns[-1].outcome == "cancelled", record.turns[-1]
    # The run itself may still complete — a provider that was told returns what it had — so the
    # turn's outcome is the thread's to say, and the run's `Ended` says what the run did.
    assert events[-1].kind == "ended"


async def _collect(events: Any) -> list[Any]:
    return [e async for e in events]
