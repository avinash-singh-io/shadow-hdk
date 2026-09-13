"""A port that breaks is the host's failure, not the component's (TD-006, D7).

`step.py` says it in its own docstring: *A **component** raising is data — a `Failed` observation
the agent sees. A **port** raising is a failure: `PortFailure`, which the drive turns into
`Ended(reason="failed")`, because a broken host is not something the runtime can reason past.*

The step honours that. Three places outside it did not, and each inverts the rule in its own way.

**`visible()` called governance unwrapped.** It runs inside whatever component asked for a
catalogue, so a policy service that is down surfaced as *that component failed* — the agent saw a
`Failed`, wrote it off, and the run carried on under a policy nobody could reach. D7 exactly
backwards: the one thing that must stop a run became the one thing an agent routes around.

**`propose()` announced the proposal before the sink took it.** `Proposed` went on the record, then
the sink was called unwrapped. A sink that raised left a proposal on the record that never arrived
anywhere — the same bug `FileSink` had inside itself (BUG-014), one layer up.

**A component port that will not list its components was swallowed.** `refresh()` collects the
failure into `unreachable`, and **nothing reads that list** — grep says so. A vanished MCP server is
a catalogue that quietly shrinks, which reads exactly like a policy that narrowed.

And one that is not about ports at all: **the lease was charged before the step was judged**, so a
policy refusing everything drained the budget of a run that did nothing.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import JsonValue
from shadow_hdk.adapters.basic import AllowAll, CallableComponents

from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Composition,
    Ended,
    Event,
    Floor,
    Invoke,
    Lease,
    Registration,
    ScopeSet,
)
from shadow_hdk.kernel.components import Provenance
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.observations import Proposal
from shadow_hdk.kernel.ports import Allow, Context, Judgement, Refuse
from shadow_hdk.runtime import Ports, RunOptions, current_run, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

WORKSPACE = ScopeSet.of("workspace")
WHERE = Provenance(registered_by="tests", adapter="test", at="2026-01-01T00:00:00+00:00")


def look(topic: str) -> str:
    """Look a topic up."""
    return f"found {topic}"


class StopTheWorld(BaseException):
    """A `BaseException` the runtime has never heard of — `KeyboardInterrupt`'s shape without its
    effect on the test session, which pytest quite reasonably treats as *stop everything*."""


class PolicyIsDownForTheCatalogue:
    """Allows the step, then breaks when the catalogue asks.

    **The first version raised for everything**, and a mutation removing `visible()`'s wrapper
    survived it: the *step's* own judgement fails first, and `step.py` has always wrapped that — so
    the run ended `failed` for a reason that had nothing to do with the catalogue. To see the
    catalogue's wrapper at all, the policy has to answer the step and break only when `visible()`
    asks, which it does under the step name `<catalogue>`.
    """

    async def judge(self, _effects: EffectProfile, context: Context) -> Judgement:
        if context.step == "<catalogue>":
            raise RuntimeError("the policy service is down")
        return Allow()


class RefusesEverything:
    async def judge(self, _effects: EffectProfile, _context: Context) -> Judgement:
        return Refuse("not in this deployment")


class SinkIsDown:
    async def propose(self, _proposal: Proposal) -> None:
        raise RuntimeError("the sink is down")


class ComponentsAreDown:
    async def registrations(self) -> list[Registration]:
        raise ConnectionError("the component server went away")

    async def invoke(self, _registration: str, _inputs: JsonValue) -> Any:
        raise AssertionError("never reached")


def tools() -> CallableComponents:
    components = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    components.add(look, effects=EffectProfile(reads=WORKSPACE))
    return components


async def drive(
    *,
    governance: Any = None,
    sink: Any = None,
    components: Any = None,
    ceiling: Ceiling | None = None,
) -> list[Event]:
    ports = Ports(
        model=ScriptedModel(),
        components=(components or tools(),),
        governance=governance or AllowAll(),
        sink=sink or ListSink(),
        clock=FixedClock(),
    )
    return [
        event
        async for event in run(
            Composition((Invoke("s1", "look", (Binding(name="topic", value="x"),)),)),
            ports,
            options=RunOptions(lease=Lease(ceiling or Ceiling(10, 600, 10_000), Floor(0))),
        )
    ]


# ------------------------------------------------------------------ the catalogue


async def test_a_policy_that_is_down_stops_the_run_rather_than_the_component() -> None:
    """`visible()` is where a component asks what it may see, so a policy failure there arrived as
    that component's own `Failed` — an agent's cue to try something else, under a policy nobody
    could reach."""

    components = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")

    async def catalogue() -> str:
        """Ask the run what it may see."""
        context = current_run()
        assert context is not None
        await context.visible()
        return "asked"

    components.add(catalogue, effects=EffectProfile(reads=WORKSPACE))
    ports = Ports(
        model=ScriptedModel(),
        components=(components,),
        governance=PolicyIsDownForTheCatalogue(),
        sink=ListSink(),
        clock=FixedClock(),
    )

    events = [
        event
        async for event in run(
            Composition((Invoke("s1", "catalogue"),)),
            ports,
            options=RunOptions(lease=Lease(Ceiling(10, 600, 10_000), Floor(0))),
        )
    ]
    ended = [e for e in events if isinstance(e, Ended)][-1]

    assert ended.reason == "failed", "a policy that is down was written off as a component's fault"
    assert "governance" in str(ended.detail), (
        f"the run ended failed without naming the port: {ended.detail}"
    )


async def test_an_unrecognised_stop_still_reaches_the_caller() -> None:
    """`run()` turns every stop it knows into a reason on the record rather than a traceback. What
    it must **not** do is swallow one it does not know — a `KeyboardInterrupt` belongs to whoever is
    driving, and a run nobody can interrupt is worse than one that ends untidily.

    Found by a mutation: deleting that guard broke nothing, because no test asked for it.
    """
    components = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")

    def interrupted() -> str:
        """Stop the world."""
        raise StopTheWorld

    components.add(interrupted, effects=EffectProfile(reads=WORKSPACE))
    ports = Ports(
        model=ScriptedModel(),
        components=(components,),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )

    with pytest.raises(StopTheWorld):
        async for _event in run(
            Composition((Invoke("s1", "interrupted"),)),
            ports,
            options=RunOptions(lease=Lease(Ceiling(10, 600, 10_000), Floor(0))),
        ):
            pass


# ------------------------------------------------------------------ the sink


async def test_a_proposal_is_announced_only_once_the_sink_has_taken_it() -> None:
    """`Proposed` went on the record first and the sink was called after, so a sink that raised
    left a record of a proposal that never arrived. The same rule `FileSink` holds internally
    (BUG-014): what was not kept is not reported as kept."""
    proposing = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")

    async def propose_one() -> str:
        """Propose something."""
        context = current_run()
        assert context is not None
        await context.propose(Proposal(kind="claim", payload={"n": 1}, provenance=WHERE))
        return "ok"

    proposing.add(propose_one, effects=EffectProfile(reads=WORKSPACE))
    ports = Ports(
        model=ScriptedModel(),
        components=(proposing,),
        governance=AllowAll(),
        sink=SinkIsDown(),
        clock=FixedClock(),
    )

    events = [
        event
        async for event in run(
            Composition((Invoke("s1", "propose_one"),)),
            ports,
            options=RunOptions(lease=Lease(Ceiling(10, 600, 10_000), Floor(0))),
        )
    ]
    ended = [e for e in events if isinstance(e, Ended)][-1]

    assert ended.reason == "failed"
    assert "sink" in str(ended.detail)
    assert [e.kind for e in events].count("proposed") == 0, (
        "a proposal the sink never took was announced anyway"
    )


async def test_a_working_sink_still_puts_the_proposal_on_the_record() -> None:
    """The ordering change must not cost the event. A proposal that was kept is announced."""
    sink = ListSink()
    proposing = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")

    async def propose_one() -> str:
        """Propose something."""
        context = current_run()
        assert context is not None
        await context.propose(Proposal(kind="claim", payload={"n": 1}, provenance=WHERE))
        return "ok"

    proposing.add(propose_one, effects=EffectProfile(reads=WORKSPACE))
    ports = Ports(
        model=ScriptedModel(),
        components=(proposing,),
        governance=AllowAll(),
        sink=sink,
        clock=FixedClock(),
    )
    events = [
        event
        async for event in run(
            Composition((Invoke("s1", "propose_one"),)),
            ports,
            options=RunOptions(lease=Lease(Ceiling(10, 600, 10_000), Floor(0))),
        )
    ]

    assert [e.kind for e in events].count("proposed") == 1
    assert len(sink.proposals) == 1


# ------------------------------------------------------------------ the catalogue that vanished


async def test_a_component_port_that_will_not_answer_can_be_read() -> None:
    """Swallowed into a list nothing reads, a vanished server is a catalogue that quietly shrinks —
    indistinguishable from a policy that narrowed, which is the one thing `visible()` exists to make
    legible.

    Tolerating it is deliberate and stays: one broken server should not end a run that never needed
    it. What changes is that a host can now *see* it. Putting it on the **event stream**, where it
    belongs, needs a twelfth event kind and therefore a contract change — filed rather than
    smuggled in at the end of a phase.
    """
    seen: list[tuple[str, ...]] = []
    components = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")

    def note() -> str:
        """Look at what could not be reached."""
        context = current_run()
        assert context is not None
        seen.append(context.unreachable)
        return "ok"

    components.add(note, effects=EffectProfile(reads=WORKSPACE))
    ports = Ports(
        model=ScriptedModel(),
        components=(components, ComponentsAreDown()),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    async for _event in run(
        Composition((Invoke("s1", "note"),)),
        ports,
        options=RunOptions(lease=Lease(Ceiling(10, 600, 10_000), Floor(0))),
    ):
        pass

    assert seen and seen[0], "a port that would not answer left no trace a host can read"
    assert "ComponentsAreDown" in seen[0][0]
    assert "went away" in seen[0][0], f"the reason is not carried: {seen[0]}"


# ------------------------------------------------------------------ the lease


async def test_a_step_refused_before_it_ran_does_not_spend_the_lease() -> None:
    """The meter was charged at the top of the step, before the judgement. A policy refusing
    everything therefore drained the budget of a run that did nothing at all — the lease measures
    work, and a refusal is the absence of work."""
    events = await drive(governance=RefusesEverything(), ceiling=Ceiling(3, 600, 10_000))
    ended = [e for e in events if isinstance(e, Ended)][-1]

    assert ended.steps_taken == 0, "a refused step was charged to the lease"


async def test_a_step_that_ran_is_still_charged() -> None:
    """The other side, and the one that matters more: the bound must still bind."""
    events = await drive()
    ended = [e for e in events if isinstance(e, Ended)][-1]

    assert ended.steps_taken == 1


async def test_a_refuse_everything_policy_does_not_end_a_run_early() -> None:
    """What the charge cost in practice: with three steps of budget and a policy refusing all of
    them, the run used to end `lease_exhausted` — reporting a budget problem for a policy decision.
    """
    ports = Ports(
        model=ScriptedModel(),
        components=(tools(),),
        governance=RefusesEverything(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    events = [
        event
        async for event in run(
            Composition(
                tuple(
                    Invoke(f"s{n}", "look", (Binding(name="topic", value="x"),)) for n in range(5)
                )
            ),
            ports,
            options=RunOptions(lease=Lease(Ceiling(3, 600, 10_000), Floor(0))),
        )
    ]
    ended = [e for e in events if isinstance(e, Ended)][-1]

    assert ended.reason == "completed", (
        f"five refusals under a budget of three ended {ended.reason}"
    )
    assert [e.kind for e in events].count("refused") == 5
