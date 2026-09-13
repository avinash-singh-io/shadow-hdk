"""The ports invert, and the same run happens on the other side of a wire.

`specs/architecture/wire.md` fixes the shape: *the host **drives**; the runtime **calls
back**. `run` and `resume` are host → runtime. The six ports invert: when the runtime needs a
judgement, a model completion, a component invocation or a sink write, it issues a request the
host answers. Events stream host-ward continuously.*

The loopback carries **JSON text**, not live objects. A loopback that passed Python objects between
two halves of one process would prove the plumbing and nothing about the boundary — and the boundary
is the entire subject.
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
    Event,
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
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)
from shadow_hdk.wire import PROTOCOL_VERSION, VersionMismatch, drive, loopback

WORKSPACE = ScopeSet.of("workspace")
LOOK = make_registration("look", effects=EffectProfile(reads=WORKSPACE))
WIPE = make_registration("wipe", effects=EffectProfile(writes=WORKSPACE, reversible=False))


async def _look(inputs: JsonValue) -> Observation:
    return Completed({"found": inputs})


async def _wipe(_inputs: JsonValue) -> Observation:
    return Completed({"wiped": True})


class NoWrites:
    """A policy that lives on the **host** — so a refusal here proves the judgement crossed."""

    async def judge(self, effects: EffectProfile, _context: Context) -> Judgement:
        if effects.writes.names or effects.writes.everything:
            return Refuse("this deployment does not write")
        from shadow_hdk.kernel.ports import Allow

        return Allow()


def a_lease(steps: int = 20) -> Lease:
    return Lease(Ceiling(steps, 3600, 10_000), Floor(0))


def _ports(sink: ListSink | None = None, governance: object | None = None) -> Ports:
    from shadow_hdk.adapters.basic import AllowAll

    return Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(LOOK, _look), (WIPE, _wipe)]),),
        governance=governance or AllowAll(),  # type: ignore[arg-type]
        sink=sink or ListSink(),
        clock=FixedClock(),
    )


ONE = Composition((Invoke("s1", LOOK.id, ()),))
TWO = Composition((Sequence("seq", (Invoke("a", LOOK.id, ()), Invoke("b", LOOK.id, ()))),))


def _shape(events: list[Event]) -> list[tuple[str, str]]:
    return [(e.kind, getattr(e, "step", "")) for e in events]


# ---------------------------------------------------------------- initialize


async def test_initialize_agrees_on_a_version() -> None:
    async with loopback() as (host, runtime):
        agreed = await host.initialize()
        assert agreed.protocol_version == PROTOCOL_VERSION
        assert runtime.initialized


async def test_a_version_mismatch_is_refused_rather_than_degraded() -> None:
    """wire.md: *negotiated at `initialize`, refusing rather than degrading on a version mismatch.*
    Degrading silently is how two peers come to disagree about what a message means."""
    async with loopback() as (host, _runtime):
        with pytest.raises(VersionMismatch) as refused:
            await host.initialize(protocol_version="0.0.1-from-the-future")
        assert PROTOCOL_VERSION in str(refused.value), str(refused.value)
        assert "0.0.1-from-the-future" in str(refused.value)


# ---------------------------------------------------------------- the run crosses


async def test_a_composition_runs_over_the_wire_and_produces_the_same_events() -> None:
    """The claim in one line: a composition root over the same package, not a redesign."""
    with anyio.fail_after(30):
        here = [
            e async for e in run(TWO, _ports(), options=RunOptions(lease=a_lease(), run_id="r"))
        ]
        there = [
            e async for e in drive(TWO, _ports(), options=RunOptions(lease=a_lease(), run_id="r"))
        ]
    assert _shape(there) == _shape(here)
    last = [e for e in there if isinstance(e, Observed)][-1]
    assert last.observation == Completed({"found": {}})


async def test_the_model_port_inverts() -> None:
    """The runtime asks; the host's model answers. The scripted model lives host-side only."""
    from shadow_hdk.kernel.ports import ModelResponse

    ports = _ports()
    scripted = ScriptedModel([ModelResponse("from the host")])
    ports = Ports(
        model=scripted,
        components=ports.components,
        governance=ports.governance,
        sink=ports.sink,
        clock=ports.clock,
    )

    async def asks(_inputs: JsonValue) -> Observation:
        from shadow_hdk.kernel.ports import Message, ModelRequest
        from shadow_hdk.runtime import current_run

        context = current_run()
        assert context is not None
        # `Ports.model` is optional since ENH-004 — a run with no model is ordinary. This one has
        # one, and says so rather than reaching through a `None` the type system now knows about.
        assert context.ports.model is not None, "this run was given a model"
        answer = await context.ports.model.complete(ModelRequest((Message("user", "hello"),)))
        return Completed(answer.text)

    asking = make_registration("asking", effects=EffectProfile(costs=True))
    ports = Ports(
        model=scripted,
        components=(InMemoryComponents([(asking, asks)]),),
        governance=ports.governance,
        sink=ports.sink,
        clock=ports.clock,
    )
    with anyio.fail_after(30):
        events = [
            e
            async for e in drive(
                Composition((Invoke("s1", asking.id, ()),)),
                ports,
                options=RunOptions(lease=a_lease()),
            )
        ]
    observed = [e for e in events if isinstance(e, Observed)]
    assert observed[-1].observation == Completed("from the host")
    assert scripted.requests, "the model was never asked, so nothing crossed"


async def test_the_governance_port_inverts() -> None:
    """A policy that only exists on the host refuses a step the runtime wanted to take."""
    with anyio.fail_after(30):
        events = [
            e
            async for e in drive(
                Composition((Invoke("s1", WIPE.id, ()),)),
                _ports(governance=NoWrites()),
                options=RunOptions(lease=a_lease()),
            )
        ]
    refusals = [e for e in events if e.kind == "refused"]
    assert refusals, "the host's policy never got asked"
    assert "does not write" in refusals[0].reason


async def test_the_sink_port_inverts() -> None:
    """A proposal made inside the runtime reaches the host's sink — the record is the host's."""
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
        events = [
            e
            async for e in drive(
                Composition((Invoke("s1", proposing.id, ()),)),
                ports,
                options=RunOptions(lease=a_lease()),
            )
        ]
    assert [p.kind for p in kept.proposals] == ["finding"]
    assert kept.proposals[0].payload == {"mass": 12}
    # And it is **on the run's record**, which is the reason `propose` crosses back rather than
    # writing to the host sink one hop cheaper: `RunContext.propose` emits `Proposed` as well as
    # calling the sink, and an event emitted host-side lands on a stream nobody reads.
    assert [e.kind for e in events if e.kind == "proposed"] == ["proposed"]


async def test_a_component_failure_crosses_as_a_failure_not_as_a_broken_wire() -> None:
    """D7 all the way out: a component is untrusted, and its raising is data on both sides."""

    async def breaks(_inputs: JsonValue) -> Observation:
        raise RuntimeError("the component is unwell")

    breaking = make_registration("breaking")
    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(breaking, breaks)]),),
        governance=_ports().governance,
        sink=ListSink(),
        clock=FixedClock(),
    )
    with anyio.fail_after(30):
        events = [
            e
            async for e in drive(
                Composition((Invoke("s1", breaking.id, ()),)),
                ports,
                options=RunOptions(lease=a_lease()),
            )
        ]
    observed = [e for e in events if isinstance(e, Observed)]
    assert observed[-1].observation.kind == "failed"
    assert "unwell" in observed[-1].observation.error


async def test_everything_that_crosses_is_json_text() -> None:
    """The loopback carries text. A loopback passing live objects between two halves of one process
    would prove the plumbing and nothing about the boundary — and the boundary is the subject."""
    seen: list[str] = []
    with anyio.fail_after(30):
        async for _ in drive(
            TWO, _ports(), options=RunOptions(lease=a_lease()), watching=seen.append
        ):
            pass
    assert seen, "nothing crossed at all"
    assert all(isinstance(frame, str) for frame in seen)
    import json

    for frame in seen:
        json.loads(frame)


async def test_a_component_the_host_does_not_have_is_a_failure_that_says_so() -> None:
    """The registry is the host's, and a runtime asking for something absent must be told, not
    quietly told yes — a `Completed` here would put a step on the record that never ran."""
    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(LOOK, _look)]),),
        governance=_ports().governance,
        sink=ListSink(),
        clock=FixedClock(),
    )
    with anyio.fail_after(30):
        events = [
            e
            async for e in drive(
                Composition((Invoke("s1", "not_registered", ()),)),
                ports,
                options=RunOptions(lease=a_lease()),
            )
        ]
    observed = [e for e in events if isinstance(e, Observed)]
    assert observed, "nothing was observed at all"
    assert observed[-1].observation.kind == "failed"
    assert "not_registered" in observed[-1].observation.error


async def test_a_port_that_raises_crosses_as_a_failure_rather_than_a_broken_wire() -> None:
    """D7 at the **port** boundary, which is a different boundary from the component's.

    `InMemoryComponents` already catches a component raising and returns `Failed`, so a test built
    on it never exercises the wire's own guard — which is why the mutation removing that guard
    survived. This uses a port that raises outright: the host's handler fails, the failure comes
    back as a JSON-RPC error, and the runtime must turn it into an observation rather than letting
    the run die of a port.
    """
    from collections.abc import Sequence as _Sequence

    from shadow_hdk.kernel.components import Registration, RegistrationId

    class Unwell:
        async def registrations(self) -> _Sequence[Registration]:
            return [LOOK]

        async def invoke(self, _registration: RegistrationId, _inputs: JsonValue) -> Observation:
            raise RuntimeError("the port itself is unwell")

    ports = Ports(
        model=ScriptedModel(),
        components=(Unwell(),),
        governance=_ports().governance,
        sink=ListSink(),
        clock=FixedClock(),
    )
    with anyio.fail_after(30):
        events = [e async for e in drive(ONE, ports, options=RunOptions(lease=a_lease()))]
    observed = [e for e in events if isinstance(e, Observed)]
    assert observed, "the run died of a port instead of observing it"
    assert observed[-1].observation.kind == "failed"
    assert "unwell" in observed[-1].observation.error


async def test_the_host_refuses_a_component_it_does_not_have() -> None:
    """The guard, tested where it lives.

    A whole run cannot reach it: the runtime resolves against the registry it was given, which is
    the host's own list, so a name that is not there fails at resolution and never crosses. The
    guard exists for the gap between a refresh and an invoke — a component the host had a moment
    ago and does not have now — and a mutation turning it into a `Completed` survived every
    end-to-end test precisely because none of them can get there.
    """
    from shadow_hdk.adapters.basic import AllowAll
    from shadow_hdk.wire.sides import HostSide

    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(LOOK, _look)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )

    class _Nowhere:
        """A channel that is never used — this call never leaves the host."""

        async def send(self, _frame: str) -> None:
            raise AssertionError("nothing should cross for a component the host does not have")

        async def receive(self) -> str:
            raise AssertionError("nothing should cross for a component the host does not have")

        async def aclose(self) -> None:
            return None

    host = HostSide(_Nowhere(), ports)
    answered = await host._invoke({"registration": "vanished", "inputs": {}, "run_id": "r"})
    assert answered["kind"] == "failed"
    assert "vanished" in answered["error"]
