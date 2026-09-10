"""A runtime a child process can drive — over a real pipe, to a real second process.

`wire.md`: *`shadow-hdk --stdio` · JSON-RPC 2.0 over stdio · a child process; the same shape MCP
and ACP use.* The runtime is the **child** here: the host spawns it and holds the real ports, so the
child writes its callbacks and its events up the pipe and the host answers down it.

Every test in this file bounds itself with `anyio.fail_after`. A process test that hangs takes the
whole suite with it, and this one starts an interpreter.
"""

from __future__ import annotations

import anyio
import pytest
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Floor,
    Invoke,
    Lease,
    Observation,
    Observed,
    Proposal,
    ScopeSet,
    Sequence,
)
from shadow_hdk.kernel.ports import Context, Judgement, Refuse
from shadow_hdk.runtime import Ports, RunOptions
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)
from shadow_hdk.wire import over_a_child_process

WORKSPACE = ScopeSet.of("workspace")
LOOK = make_registration("look", effects=EffectProfile(reads=WORKSPACE))
WIPE = make_registration("wipe", effects=EffectProfile(writes=WORKSPACE, reversible=False))

pytestmark = pytest.mark.anyio


async def _look(inputs: JsonValue) -> Observation:
    return Completed({"found": inputs})


async def _wipe(_inputs: JsonValue) -> Observation:
    return Completed({"wiped": True})


class NoWrites:
    async def judge(self, effects: EffectProfile, _context: Context) -> Judgement:
        from shadow_hdk.kernel.ports import Allow

        if effects.writes.names or effects.writes.everything:
            return Refuse("this deployment does not write")
        return Allow()


def _ports(governance: object | None = None, sink: ListSink | None = None) -> Ports:
    from shadow_hdk.adapters.basic import AllowAll

    return Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(LOOK, _look), (WIPE, _wipe)]),),
        governance=governance or AllowAll(),  # type: ignore[arg-type]
        sink=sink or ListSink(),
        clock=FixedClock(),
    )


def a_lease(steps: int = 20) -> Lease:
    return Lease(Ceiling(steps, 3600, 10_000), Floor(0))


TWO = Composition((Sequence("seq", (Invoke("a", LOOK.id, ()), Invoke("b", LOOK.id, ()))),))


async def test_a_composition_runs_in_a_child_process() -> None:
    """A second interpreter, a real pipe, and the ports answered back up it."""
    with anyio.fail_after(120):
        async with over_a_child_process(_ports()) as host:
            await host.initialize()
            await host.run(TWO, RunOptions(lease=a_lease(), run_id="over-a-pipe"))
            events = list(host.events)

    steps = [e.step for e in events if e.kind == "invoked"]
    assert steps == ["a", "b"], steps
    observed = [e for e in events if isinstance(e, Observed)]
    assert observed[-1].observation == Completed({"found": {}})
    assert {e.run_id for e in events} == {"over-a-pipe"}


async def test_the_host_policy_refuses_a_step_in_the_child() -> None:
    """The judgement crosses a process boundary, not just a function call."""
    with anyio.fail_after(120):
        async with over_a_child_process(_ports(governance=NoWrites())) as host:
            await host.initialize()
            await host.run(Composition((Invoke("s1", WIPE.id, ()),)), RunOptions(lease=a_lease()))
            events = list(host.events)

    refusals = [e for e in events if e.kind == "refused"]
    assert refusals, "the host's policy never got asked across the pipe"
    assert "does not write" in refusals[0].reason


async def test_what_a_component_proposes_in_the_child_reaches_the_hosts_record() -> None:
    """D21 across a process: the component runs in the **host**, and its proposal still has to be
    on the run's record — which lives in the child."""
    kept = ListSink()

    async def proposes(_inputs: JsonValue) -> Observation:
        from shadow_hdk.kernel.components import Provenance
        from shadow_hdk.runtime import current_run

        context = current_run()
        assert context is not None
        await context.propose(
            Proposal(
                kind="finding",
                payload={"mass": 12},
                provenance=Provenance(registered_by="test", adapter="test", at="t"),
            )
        )
        return Completed(None)

    proposing = make_registration("proposing")
    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(proposing, proposes)]),),
        governance=_ports().governance,
        sink=kept,
        clock=FixedClock(),
    )
    with anyio.fail_after(120):
        async with over_a_child_process(ports) as host:
            await host.initialize()
            await host.run(
                Composition((Invoke("s1", proposing.id, ()),)), RunOptions(lease=a_lease())
            )
            events = list(host.events)

    assert [p.kind for p in kept.proposals] == ["finding"]
    assert [e.kind for e in events if e.kind == "proposed"] == ["proposed"]


async def test_the_child_is_a_genuinely_separate_process() -> None:
    """Worth asserting, because a test that quietly ran in-process would pass everything above and
    prove none of it."""
    import os

    seen: list[int] = []

    async def tells_its_pid(_inputs: JsonValue) -> Observation:
        return Completed(os.getpid())

    telling = make_registration("telling")
    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(telling, tells_its_pid)]),),
        governance=_ports().governance,
        sink=ListSink(),
        clock=FixedClock(),
    )
    with anyio.fail_after(120):
        async with over_a_child_process(ports) as host:
            await host.initialize()
            assert host.child_pid is not None
            seen.append(host.child_pid)
            await host.run(
                Composition((Invoke("s1", telling.id, ()),)), RunOptions(lease=a_lease())
            )

    assert seen[0] != os.getpid(), "the runtime ran in this process, so nothing crossed"


async def test_a_child_that_dies_is_an_error_rather_than_a_hang() -> None:
    """A dead peer is a failure a caller can act on; a hang is not.

    Without this the host waits for a reply from a process that is already a zombie — and a hang has
    no stack trace, no log line and no upper bound. This kills the child mid-session and asks for
    something.
    """
    import os
    import signal

    from shadow_hdk.wire.peer import RemoteError

    with anyio.fail_after(120):
        async with over_a_child_process(_ports()) as host:
            await host.initialize()
            assert host.child_pid is not None
            os.kill(host.child_pid, signal.SIGKILL)
            await anyio.sleep(0.3)
            with pytest.raises(RemoteError) as gone:
                await host.run(TWO, RunOptions(lease=a_lease()))
    assert "closed" in str(gone.value).lower(), str(gone.value)


async def test_a_peer_that_dies_mid_call_raises_rather_than_waiting_for_ever() -> None:
    """The in-flight case, which killing a child does not reach.

    Killing the child and *then* calling fails at the write — a broken pipe, caught elsewhere. The
    case this covers is a call already sent and waiting for a reply when the other end goes away.
    A mutation removing the hang-up survived every process test precisely because none of them
    could get here.
    """
    from shadow_hdk.wire.peer import Peer, RemoteError

    class _Dies:
        """Accepts one frame, then reports the other end gone."""

        def __init__(self) -> None:
            self.gone = anyio.Event()

        async def send(self, _frame: str) -> None:
            return None

        async def receive(self) -> str:
            await self.gone.wait()
            raise anyio.EndOfStream

        async def aclose(self) -> None:
            return None

    channel = _Dies()
    peer = Peer(channel, name="lonely")
    with anyio.fail_after(30):
        async with anyio.create_task_group() as group:
            group.start_soon(peer.serve_forever, group)

            async def ask() -> None:
                with pytest.raises(RemoteError) as gone:
                    await peer.call("never.answered", {})
                assert "closed" in str(gone.value).lower(), str(gone.value)

            group.start_soon(ask)
            await anyio.sleep(0.05)
            channel.gone.set()


def test_the_module_refuses_to_run_without_being_asked_for_stdio() -> None:
    """`--stdio` is a mode, not a default. A module that served a wire on being imported-and-run
    with no arguments would take over stdout of anything that touched it."""
    from shadow_hdk.wire.__main__ import main

    assert main([]) == 2
    assert main(["--help"]) == 2
