"""A runtime you connect to rather than launch — over a real socket on localhost.

Phase 5 found the gap this closes. The RecordingServer can only be *connected to*, never launched:
a server holding a live `RunContext` cannot be started fresh by somebody else, so a child on another
machine had no way in. `serve` is that way in.

**The awkward part is the direction.** The ports invert — the runtime calls the host — but over HTTP
the server cannot call its client. So the two directions take different paths, the same split MCP's
streamable HTTP uses: the host POSTs its messages, and everything travelling the other way (the
runtime's callbacks *and* its events) comes back down one SSE stream. `Channel` already hides that
from the protocol, so `RuntimeSide` is untouched.

Every test here binds **127.0.0.1 on port 0** and bounds itself with `anyio.fail_after(30)`. Thirty
rather than a hundred and twenty: the global pytest timeout is sixty, so a longer bound could never
fire, and a mutation run pays every bound in full on each broken variant — the first one took over
ten minutes for eight mutations.
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
from shadow_hdk.wire import connect_to, served_over_http

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
LOOK = make_registration("look", effects=EffectProfile(reads=WORKSPACE))
WIPE = make_registration("wipe", effects=EffectProfile(writes=WORKSPACE, reversible=False))


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


async def test_a_client_that_did_not_launch_it_can_run_a_composition() -> None:
    """The whole point of a listening transport, and Phase 5's debt paid."""
    with anyio.fail_after(30):
        async with served_over_http() as address:
            assert address.startswith("http://127.0.0.1:"), address
            async with connect_to(address, _ports()) as host:
                await host.initialize()
                await host.run(TWO, RunOptions(lease=a_lease(), run_id="over-a-socket"))
                events = list(host.events)

    assert [e.step for e in events if e.kind == "invoked"] == ["a", "b"]
    assert [e for e in events if isinstance(e, Observed)][-1].observation == Completed(
        {"found": {}}
    )
    assert {e.run_id for e in events} == {"over-a-socket"}


async def test_the_events_arrive_while_the_run_is_still_going() -> None:
    """A stream that only delivered at the end would be a response, not a stream — and a host
    watching a long run would see nothing until there was nothing left to watch."""
    seen_during: list[int] = []

    async def counting(_inputs: JsonValue) -> Observation:
        seen_during.append(len(seen_during))
        return Completed(None)

    slow = make_registration("slow")
    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(slow, counting)]),),
        governance=_ports().governance,
        sink=ListSink(),
        clock=FixedClock(),
    )
    plan = Composition((Sequence("seq", tuple(Invoke(f"s{i}", slow.id, ()) for i in range(4))),))
    arrived: list[int] = []

    with anyio.fail_after(30):
        async with served_over_http() as address:
            async with connect_to(address, ports) as host:
                await host.initialize()
                host.watching = lambda _e: arrived.append(len(seen_during))
                await host.run(plan, RunOptions(lease=a_lease()))

    assert arrived, "no events arrived at all"
    assert min(arrived) < max(arrived), (
        "every event arrived at the same moment, so nothing was streaming"
    )


async def test_the_host_policy_refuses_across_the_socket() -> None:
    with anyio.fail_after(30):
        async with served_over_http() as address:
            async with connect_to(address, _ports(governance=NoWrites())) as host:
                await host.initialize()
                await host.run(
                    Composition((Invoke("s1", WIPE.id, ()),)), RunOptions(lease=a_lease())
                )
                events = list(host.events)

    refusals = [e for e in events if e.kind == "refused"]
    assert refusals and "does not write" in refusals[0].reason


async def test_a_proposal_from_the_hosts_component_lands_on_the_runs_record() -> None:
    """D21 across a socket."""
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
    with anyio.fail_after(30):
        async with served_over_http() as address:
            async with connect_to(address, ports) as host:
                await host.initialize()
                await host.run(
                    Composition((Invoke("s1", proposing.id, ()),)), RunOptions(lease=a_lease())
                )
                events = list(host.events)

    assert [p.kind for p in kept.proposals] == ["finding"]
    assert [e.kind for e in events if e.kind == "proposed"] == ["proposed"]


async def test_two_clients_get_their_own_sessions() -> None:
    """A listening runtime serves more than one host, and one host's run is not another's.

    Without this a second connection would join the first's session and answer its callbacks —
    which is a confused deputy with a nice error message.
    """
    with anyio.fail_after(30):
        async with served_over_http() as address:
            async with connect_to(address, _ports()) as first:
                async with connect_to(address, _ports()) as second:
                    await first.initialize()
                    await second.initialize()
                    assert first.session_id and second.session_id
                    assert first.session_id != second.session_id
                    await first.run(TWO, RunOptions(lease=a_lease(), run_id="first"))
                    await second.run(TWO, RunOptions(lease=a_lease(), run_id="second"))
                    mine = {e.run_id for e in first.events}
                    theirs = {e.run_id for e in second.events}

    assert mine == {"first"}, mine
    assert theirs == {"second"}, theirs


async def test_a_client_without_a_session_is_refused() -> None:
    """A POST carrying somebody else's session id, or none at all, is not a run."""
    import httpx

    with anyio.fail_after(30):
        async with served_over_http() as address:
            async with httpx.AsyncClient() as client:
                nowhere = await client.post(
                    f"{address}/rpc",
                    json={"jsonrpc": "2.0", "id": "x", "method": "initialize", "params": {}},
                )
                assert nowhere.status_code == 400, nowhere.text
                invented = await client.post(
                    f"{address}/rpc",
                    headers={"x-shadow-hdk-session": "not-a-session"},
                    json={"jsonrpc": "2.0", "id": "x", "method": "initialize", "params": {}},
                )
                assert invented.status_code == 404, invented.text
