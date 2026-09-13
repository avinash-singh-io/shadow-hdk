"""Another agent, driven as a component — over a real stdio pipe, against a real ACP agent.

`spikes/acp/agent.py` is a conformant agent in its own process. What is proven here is the whole
bridge: a child invoked as a step, its requests judged by our governance, its refusals arriving in
its own vocabulary, its cost reaching our meter, and its runaway stopped by our clock.

What is **not** proven is what Codex or Claude Code do, because neither speaks ACP on this machine
without a global install and a paid turn. `spikes/acp/drive_real.py` is the script that would.
"""

from __future__ import annotations

import asyncio
import sys
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import JsonValue
from shadow_hdk.adapters.acp import AcpAgent
from shadow_hdk.adapters.modes import Mode, ModeGovernance

from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Failed,
    Floor,
    Invoke,
    Lease,
    Observation,
    Observed,
    ScopeSet,
)
from shadow_hdk.kernel.ports import ComponentPort, GovernancePort
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel
from tests.adapters.acp.conftest import EVERYTHING, inside_a_run
from tests.adapters.contract import ComponentPortContract

WORKSPACE = ScopeSet.of("workspace")
OUTER_BOUND = 30.0
"""A backstop for the tests whose subject is the bridge's own clock: if that clock is broken they
must **fail**, not hang. A hanging test is a worse test than a failing one."""
SPIKE = (sys.executable, "-m", "spikes.acp.agent")

READING = Mode("reading", EffectProfile(reads=EVERYTHING, contained=False, costs=True))
WRITING = Mode(
    "writing",
    EffectProfile(reads=EVERYTHING, writes=WORKSPACE, reversible=True, contained=False, costs=True),
)

#: **What the child promises at the door.** A component's declared effects are judged before it is
#: invoked at all, so a child agent that claims only to read is admitted by a reading mode — and if
#: it then asks to write, the *inner* judgement catches it. Coarse at the door, fine inside.
READER = EffectProfile(reads=EVERYTHING, contained=False, costs=True)
WRITER = EffectProfile(reads=EVERYTHING, writes=WORKSPACE, contained=False, costs=True)


def child(root: Path | None = None, *, effects: EffectProfile = READER, **kw: object) -> AcpAgent:
    return AcpAgent(
        SPIKE[0],
        list(SPIKE[1:]),
        name="child",
        effects=effects,
        workspace=root,
        at="2026-09-10T00:00:00+00:00",
        **kw,  # type: ignore[arg-type]
    )


async def drive(
    brief: str,
    *,
    root: Path | None = None,
    governance: GovernancePort,
    effects: EffectProfile = READER,
    **kw: object,
) -> list[Observed]:
    async with child(root, effects=effects, **kw) as agent:
        ports = Ports(
            model=ScriptedModel(),
            components=(agent,),
            governance=governance,
            sink=ListSink(),
            clock=FixedClock(),
        )
        return [
            e
            async for e in run(
                Composition((Invoke("c1", "child", (Binding("brief", value=brief),)),)),
                ports,
                options=RunOptions(lease=Lease(Ceiling(20, 600, 10_000), Floor(0))),
            )
            if isinstance(e, Observed)
        ]


def outcome(events: list[Observed]) -> dict[str, JsonValue]:
    last = events[-1].observation
    assert isinstance(last, Completed), f"the child ended as {last!r}"
    assert isinstance(last.output, dict)
    return last.output


def mode(one: Mode) -> ModeGovernance:
    return ModeGovernance({one.name: one}, default=one.name)


class TestAcpAgentIsAComponentPort(ComponentPortContract):
    @asynccontextmanager
    async def using(self) -> AsyncIterator[ComponentPort]:
        async with child() as agent:
            yield agent

    def valid_call(self) -> tuple[str, JsonValue]:
        return "child", {"brief": "say something"}


# ---------------------------------------------------------------- it is a component


async def test_a_child_agent_answers_as_an_observation() -> None:
    events = await drive("just answer", governance=mode(READING))
    assert outcome(events)["stop_reason"] == "cancelled"


async def test_a_child_that_refuses_says_refusal_and_not_cancelled() -> None:
    """`refusal` is the agent declining; `cancelled` is it not being allowed. A meter that
    collapsed the two could not tell a governed stop from a model changing its mind."""
    events = await drive("refuse", governance=mode(READING))
    assert outcome(events)["stop_reason"] == "refusal"


async def test_the_session_is_resident_across_steps() -> None:
    """One process and one handshake for the whole session. A child agent is expensive to start,
    and respawning it per step would make a five-step composition five cold starts."""
    async with child() as agent:
        first = await agent.invoke("child", {"brief": "just answer"})
        second = await agent.invoke("child", {"brief": "just answer"})
    assert isinstance(first, Completed) and isinstance(second, Completed)
    assert agent.sessions_opened == 1, f"the session was reopened {agent.sessions_opened} times"


# ---------------------------------------------------------------- our governance, their agent


async def test_a_child_may_write_under_a_writing_mode() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        events = await drive("write a file", root=root, governance=mode(WRITING), effects=WRITER)
        assert outcome(events)["stop_reason"] == "end_turn"
        assert (root / "from-the-child.md").read_text() == "# hello\n"


async def test_a_child_that_promised_to_only_read_is_caught_when_it_writes() -> None:
    """Defence in depth, and the reason the inner judgement is not redundant.

    The component declares it only reads, so a reading mode lets it in. Then it asks to write a
    file — and the *inner* judgement refuses, because a promise at the door is not a permission
    inside. A mode written for the harness governs somebody else's agent without knowing it exists.
    """
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        events = await drive("write a file", root=root, governance=mode(READING))
        assert outcome(events)["stop_reason"] == "refusal"
        assert not (root / "from-the-child.md").exists()
        assert "reading" in str(outcome(events)["text"])


async def test_a_child_asking_for_a_terminal_is_judged_by_our_policy() -> None:
    with TemporaryDirectory() as tmp:
        events = await drive("terminal", root=Path(tmp), governance=mode(READING))
        assert outcome(events)["stop_reason"] == "refusal"


# ---------------------------------------------------------------- our clock, their runaway


async def test_a_child_that_loops_on_refusals_is_stopped_by_our_clock() -> None:
    """Phase 2 measured that nothing in ACP stops this. The bridge's own wall clock is what does,
    and it is **measured** rather than asserted — a test that only checked for `Failed` would pass
    even if the stop came from somewhere else entirely."""
    started = time.perf_counter()
    # **An outer bound, because the thing under test *is* the clock.** Without it a broken bridge
    # would hang this test rather than fail it — which is the lesson Phase 2 wrote down and this
    # test then ignored until a mutation stalled the suite for ten minutes.
    events = await asyncio.wait_for(
        drive("loop", governance=mode(READING), timeout_s=2.0), OUTER_BOUND
    )
    elapsed = time.perf_counter() - started
    last = events[-1].observation
    assert isinstance(last, Failed)
    assert "did not finish" in last.error
    assert elapsed < 20.0, f"the clock did not stop it: {elapsed:.1f}s"


async def test_a_child_that_ran_out_of_time_is_actually_dead() -> None:
    """Stopping the turn is not enough — the **process** has to go.

    A wedged child left running is a leaked process holding a subscription seat, and the next step
    would inherit somebody else's problem. Added after a mutation removed the kill and nothing
    failed: every test checked the observation, none checked the machine.
    """
    async with child(timeout_s=1.0) as agent:

        async def loop_forever() -> Observation:
            return await agent.invoke("child", {"brief": "loop"})

        outcome_of = await asyncio.wait_for(
            inside_a_run(loop_forever, governance=mode(READING)), OUTER_BOUND
        )
        assert isinstance(outcome_of, Failed)
        assert agent.process_is_running is False, "the child was left running"


async def test_the_lease_can_be_tighter_than_the_configured_timeout() -> None:
    """The bridge takes `min(configured, what the lease has left)`, so a run cannot be extended by
    an adapter constructed with a generous timeout."""
    async with child(timeout_s=600.0) as agent:
        ports = Ports(
            model=ScriptedModel(),
            components=(agent,),
            governance=mode(READING),
            sink=ListSink(),
            clock=FixedClock(),
        )
        started = time.perf_counter()

        async def drive_it() -> list[Observed]:
            return [
                e
                async for e in run(
                    Composition((Invoke("c1", "child", (Binding("brief", value="loop"),)),)),
                    ports,
                    options=RunOptions(lease=Lease(Ceiling(20, 2, 10_000), Floor(0))),
                )
                if isinstance(e, Observed)
            ]

        events = await asyncio.wait_for(drive_it(), OUTER_BOUND)
        elapsed = time.perf_counter() - started
    assert isinstance(events[-1].observation, Failed)
    assert elapsed < 20.0


# ---------------------------------------------------------------- what it cost


async def test_what_the_child_spent_reaches_our_meter() -> None:
    """In the shape `_usage_of` reads, so the parent's meter charges without knowing ACP."""
    events = await drive("just answer", governance=mode(READING))
    usage = outcome(events)["usage"]
    assert isinstance(usage, dict)
    assert usage["input_tokens"] == 1200
    assert usage["output_tokens"] == 200


async def test_what_the_child_said_comes_back() -> None:
    with TemporaryDirectory() as tmp:
        events = await drive("write a file", root=Path(tmp), governance=mode(WRITING))
        assert "trying it" in str(outcome(events)["text"])
