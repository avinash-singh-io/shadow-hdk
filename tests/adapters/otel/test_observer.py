"""The shape of a run as a trace, over the OpenTelemetry API alone (D28).

Everything here is driven through a real run where the runtime can produce the event, and fed by
hand only where the environment is the point: a stream this process did not see start, a tracer
that raises, a provider that was never configured.
"""

from __future__ import annotations

import typing
from collections.abc import Sequence

import pytest
from opentelemetry import trace
from opentelemetry.trace import StatusCode
from pydantic import JsonValue

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.adapters.otel import OpenTelemetryObserver
from shadow_hdk.kernel import (
    Acted,
    Await,
    Binding,
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Ended,
    Event,
    Floor,
    Invoke,
    Lease,
    Observation,
    Observed,
    Pending,
    ScopeSet,
)
from shadow_hdk.kernel.events import EndReason, Started
from shadow_hdk.kernel.ports import Ask, Context, GovernancePort, Judgement, Refuse
from shadow_hdk.runtime import Ports, RunOptions, current_run, resume, run
from shadow_hdk.runtime.emit import Emitter
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)
from tests.adapters.otel.conftest import RaisingTracer, RecordingTracer, Stamp

LOOK = make_registration("look", effects=EffectProfile(reads=ScopeSet.of("workspace")))
SEND = make_registration("send_mail", effects=EffectProfile(reaches=True, reversible=False))
WAIT = make_registration("wait")
PARENT = make_registration("parent")
BRIEF = make_registration("brief")
CHILD = Composition((Invoke("brief", BRIEF.id), Await("inbox", WAIT.id)))
LEASE = Lease(Ceiling(10, 600, 100), Floor(0))


async def _look(inputs: JsonValue) -> Observation:
    return Completed({"found": inputs, "usage": {"input_tokens": 3, "output_tokens": 5}})


async def _send(_inputs: JsonValue) -> Observation:
    return Acted(
        foreign_id="msg-1",
        idempotency_key="r/s1",
        exit="accepted",
        grounds={"lease": {"max_wall_seconds": 599}, "argv": {"token": "GROUNDS-ONLY"}},
    )


async def _waits(_inputs: JsonValue) -> Observation:
    return Pending("inbox")


async def _spawns(_inputs: JsonValue) -> Observation:
    context = current_run()
    assert context is not None
    await context.children.spawn(CHILD, Ceiling(5, 600, 50))
    return Completed(None)


class Governs:
    def __init__(self, judgement: Judgement) -> None:
        self._judgement = judgement

    async def judge(self, effects: EffectProfile, _context: Context) -> Judgement:
        from shadow_hdk.kernel.ports import Allow

        return self._judgement if effects.reaches or effects.reads.names else Allow()


def _ports(observer: OpenTelemetryObserver, governance: GovernancePort | None = None) -> Ports:
    return Ports(
        model=ScriptedModel(),
        components=(
            InMemoryComponents(
                [(LOOK, _look), (SEND, _send), (WAIT, _waits), (PARENT, _spawns), (BRIEF, _look)]
            ),
        ),
        governance=governance if governance is not None else AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
        observer=observer,
    )


async def _run(
    composition: Composition, tracer: RecordingTracer, **kw: typing.Any
) -> tuple[OpenTelemetryObserver, list[Event]]:
    observer = OpenTelemetryObserver(tracer=tracer)
    governance = kw.pop("governance", None)
    events = [
        e
        async for e in run(
            composition, _ports(observer, governance), options=RunOptions(lease=LEASE, **kw)
        )
    ]
    return observer, events


def _one[T](items: Sequence[T]) -> T:
    assert len(items) == 1, items
    return items[0]


ONE = Composition((Invoke("s1", LOOK.id, (Binding(name="topic", value="lathes"),)),))


# ---------------------------------------------------------------- the shape


async def test_a_run_is_one_span_and_a_step_is_its_child() -> None:
    tracer = RecordingTracer()
    await _run(ONE, tracer, run_id="r-1")
    run_span = _one(tracer.named("shadow_hdk.run"))
    assert run_span.attributes["shadow_hdk.run_id"] == "r-1"
    assert run_span.attributes["shadow_hdk.lease.max_steps"] == 10
    assert run_span.attributes["shadow_hdk.lease.max_wall_seconds"] == 600
    assert run_span.attributes["shadow_hdk.lease.max_cost_cents"] == 100
    assert run_span.attributes["shadow_hdk.reason"] == "completed"
    assert run_span.attributes["shadow_hdk.steps_taken"] == 1
    assert run_span.ended and run_span.status.status_code is StatusCode.UNSET
    step = _one(tracer.named("shadow_hdk.step"))
    assert step.parent is run_span
    assert step.attributes["shadow_hdk.step"] == "s1"
    assert step.attributes["shadow_hdk.component"] == "look"
    assert step.ended
    observed = [e for e in step.events if e.name == "observed"]
    assert (
        len(observed) == 1 and observed[0].attributes["shadow_hdk.observation.kind"] == "completed"
    )


async def test_the_spans_carry_the_records_time_not_the_observers() -> None:
    """The observer drains a queue in its own task; the record's `at` is when it happened."""
    tracer = RecordingTracer()
    await _run(ONE, tracer)
    run_span = _one(tracer.named("shadow_hdk.run"))
    assert run_span.start_time == Stamp().ns
    assert run_span.end_time == Stamp().ns


async def test_what_a_step_spent_lands_on_its_span() -> None:
    tracer = RecordingTracer()
    await _run(ONE, tracer)
    step = _one(tracer.named("shadow_hdk.step"))
    assert step.attributes["shadow_hdk.usage.input_tokens"] == 3
    assert step.attributes["shadow_hdk.usage.output_tokens"] == 5
    assert "shadow_hdk.usage.cost_cents" not in step.attributes, "an unknown cost is not a number"


async def test_the_composition_is_counted_not_copied() -> None:
    tracer = RecordingTracer()
    await _run(ONE, tracer)
    run_span = _one(tracer.named("shadow_hdk.run"))
    composed = [e for e in run_span.events if e.name == "composed"]
    assert len(composed) == 1 and composed[0].attributes == {"shadow_hdk.composition.steps": 1}


async def test_a_refusal_is_an_event_on_the_run_span_with_the_reason() -> None:
    tracer = RecordingTracer()
    await _run(ONE, tracer, governance=Governs(Refuse("reading is not permitted here")))
    run_span = _one(tracer.named("shadow_hdk.run"))
    refused = _one([e for e in run_span.events if e.name == "refused"])
    assert refused.attributes["shadow_hdk.step"] == "s1"
    assert refused.attributes["shadow_hdk.reason"] == "reading is not permitted here"
    assert tracer.named("shadow_hdk.step") == [], "a refused step was never invoked, so has no span"


async def test_an_ask_is_an_event_and_the_run_span_stays_open() -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    tracer = RecordingTracer()
    _, events = await _run(
        ONE, tracer, governance=Governs(Ask("may it read?")), checkpointer=InMemorySaver()
    )
    assert not [e for e in events if isinstance(e, Ended)]
    run_span = _one(tracer.named("shadow_hdk.run"))
    asked = _one([e for e in run_span.events if e.name == "approval_requested"])
    assert asked.attributes["shadow_hdk.step"] == "s1"
    assert asked.attributes["shadow_hdk.question"] == "may it read?"
    assert isinstance(asked.attributes["shadow_hdk.handle"], str)
    assert not run_span.ended


async def test_a_parked_step_ends_its_span_and_a_resume_opens_another() -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    tracer = RecordingTracer()
    observer = OpenTelemetryObserver(tracer=tracer)
    waiting = Composition((Await("w1", WAIT.id),))
    options = RunOptions(lease=LEASE, run_id="w", checkpointer=InMemorySaver())
    ports = _ports(observer)
    async for _ in run(waiting, ports, options=options):
        pass
    parked = _one(tracer.named("shadow_hdk.step"))
    assert parked.ended
    assert parked.events[-1].attributes["shadow_hdk.observation.kind"] == "pending"
    assert not _one(tracer.named("shadow_hdk.run")).ended
    async for _ in resume(waiting, {"done": True}, ports, options=options):
        pass
    steps = tracer.named("shadow_hdk.step")
    assert (
        len(steps) == 2
        and steps[1].events[-1].attributes["shadow_hdk.observation.kind"] == "completed"
    )
    assert _one(tracer.named("shadow_hdk.run")).attributes["shadow_hdk.reason"] == "completed"


async def test_a_child_run_is_a_span_under_its_parents_run_span() -> None:
    tracer = RecordingTracer()
    await _run(Composition((Invoke("p1", PARENT.id),)), tracer, run_id="parent")
    runs = tracer.named("shadow_hdk.run")
    assert len(runs) == 2, [r.attributes for r in runs]
    parent = next(r for r in runs if r.attributes["shadow_hdk.run_id"] == "parent")
    child = next(r for r in runs if r is not parent)
    assert child.parent is parent
    assert child.attributes["shadow_hdk.parent_run_id"] == "parent"
    assert child.attributes["shadow_hdk.lease.max_steps"] == 5
    spawned = _one([e for e in parent.events if e.name == "spawned"])
    assert spawned.attributes["shadow_hdk.child_run_id"] == child.attributes["shadow_hdk.run_id"]
    assert spawned.attributes["shadow_hdk.lease.max_steps"] == 5
    held = _one([e for e in parent.events if e.name == "held"])
    assert held.attributes["shadow_hdk.child_run_id"] == child.attributes["shadow_hdk.run_id"]
    assert held.attributes["shadow_hdk.steps_spent"] == 2
    assert isinstance(held.attributes["shadow_hdk.handle"], str)
    assert not child.ended, "a held child has not ended"


# ---------------------------------------------------------------- D28


async def test_an_act_carries_its_receipt_and_not_its_grounds() -> None:
    tracer = RecordingTracer()
    await _run(Composition((Invoke("s1", SEND.id),)), tracer)
    step = _one(tracer.named("shadow_hdk.step"))
    observed = _one([e for e in step.events if e.name == "observed"])
    assert observed.attributes["shadow_hdk.observation.kind"] == "acted"
    assert observed.attributes["shadow_hdk.observation.foreign_id"] == "msg-1"
    assert observed.attributes["shadow_hdk.observation.idempotency_key"] == "r/s1"
    assert observed.attributes["shadow_hdk.observation.exit"] == "accepted"
    assert "GROUNDS-ONLY" not in tracer.everything_recorded()


async def test_a_secret_in_an_input_or_an_output_is_on_no_span() -> None:
    """D28, held by a test: the record has it; the trace does not."""
    tracer = RecordingTracer()
    secret = Composition((Invoke("s1", LOOK.id, (Binding(name="topic", value="hunter2-token"),)),))
    _, events = await _run(secret, tracer)
    assert any(
        isinstance(e, Observed) and "hunter2-token" in repr(e.observation) for e in events
    ), "the record itself must carry the value, or the test proves nothing"
    assert "hunter2-token" not in tracer.everything_recorded()
    assert "lathes" not in tracer.everything_recorded()


# ---------------------------------------------------------------- the environment


async def test_a_stream_this_process_did_not_see_start_still_traces() -> None:
    """A run parked elsewhere and resumed here: `Observed` arrives before any `Started`."""
    tracer = RecordingTracer()
    observer = OpenTelemetryObserver(tracer=tracer)
    at = Stamp().at
    await observer.on(Observed(run_id="r", seq=7, at=at, step="w1", observation=Completed(1)))
    await observer.on(Ended(run_id="r", seq=8, at=at, reason="completed", steps_taken=3))
    run_span = _one(tracer.named("shadow_hdk.run"))
    assert run_span.attributes["shadow_hdk.run_id"] == "r" and run_span.ended
    assert "shadow_hdk.lease.max_steps" not in run_span.attributes, (
        "no lease was seen; none invented"
    )
    step = _one(tracer.named("shadow_hdk.step"))
    assert step.parent is run_span and step.ended
    assert observer.open_runs == 0


async def test_with_no_provider_nothing_raises_and_nothing_is_kept() -> None:
    """The API with no provider is a no-op by design; the observer must not keep state for it."""
    assert isinstance(trace.get_tracer("probe").start_span("probe"), trace.NonRecordingSpan)
    observer = OpenTelemetryObserver()
    ports = _ports(observer)
    events = [e async for e in run(ONE, ports, options=RunOptions(lease=LEASE))]
    assert [e for e in events if isinstance(e, Ended)][-1].reason == "completed"
    assert observer.open_runs == 0
    assert observer.open_steps == 0


async def test_an_observed_step_is_released_before_the_run_ends() -> None:
    """Not at `Ended`, which sweeps whatever is left: at `Observed`, or a long run grows."""
    from shadow_hdk.kernel.events import Invoked

    tracer = RecordingTracer()
    observer = OpenTelemetryObserver(tracer=tracer)
    at = Stamp().at
    await observer.on(Invoked(run_id="r", seq=1, at=at, step="s1", component="look", inputs={}))
    assert observer.open_steps == 1
    await observer.on(Observed(run_id="r", seq=2, at=at, step="s1", observation=Completed(1)))
    assert observer.open_steps == 0 and observer.open_runs == 1


async def test_with_no_provider_nothing_is_kept_even_mid_run() -> None:
    """A parked run is never `Ended` here; a non-recording span kept for it would be a leak."""
    from shadow_hdk.kernel.events import Invoked

    observer = OpenTelemetryObserver()
    at = Stamp().at
    await observer.on(Started(run_id="r", seq=0, at=at, lease=LEASE))
    await observer.on(Invoked(run_id="r", seq=1, at=at, step="s1", component="look", inputs={}))
    assert observer.open_runs == 0 and observer.open_steps == 0


async def test_nothing_is_kept_after_a_run_ends() -> None:
    tracer = RecordingTracer()
    observer, _ = await _run(ONE, tracer)
    assert observer.open_runs == 0 and observer.open_steps == 0


async def test_ended_reasons_map_to_status() -> None:
    """`failed` is the only reason that is an error; the rest are the runtime stopping on
    purpose."""
    tracer = RecordingTracer()
    observer = OpenTelemetryObserver(tracer=tracer)
    at = Stamp().at
    reasons: list[EndReason] = ["completed", "lease_exhausted", "gave_up", "cancelled", "failed"]
    for i, reason in enumerate(reasons):
        await observer.on(
            Ended(run_id=f"r{i}", seq=1, at=at, reason=reason, steps_taken=0, detail="why")
        )
    by_reason = {s.attributes["shadow_hdk.reason"]: s for s in tracer.named("shadow_hdk.run")}
    assert by_reason["failed"].status.status_code is StatusCode.ERROR
    assert by_reason["failed"].status.description == "why"
    assert by_reason["failed"].attributes["shadow_hdk.detail"] == "why"
    for stopped in ["completed", "lease_exhausted", "gave_up", "cancelled"]:
        assert by_reason[stopped].status.status_code is StatusCode.UNSET, stopped


async def test_a_tracer_that_raises_does_not_fail_the_run_and_is_counted() -> None:
    """Through the emitter, where D6 lives: the failure is counted, not hidden."""
    observer = OpenTelemetryObserver(tracer=RaisingTracer())
    emitter = Emitter("r", FixedClock(), observer)
    await emitter.emit(lambda **k: Started(lease=LEASE, **k))
    await emitter.emit(lambda **k: Ended(reason="completed", steps_taken=0, **k))
    emitter.close()
    await emitter.drained()
    assert emitter.observer_failures == 2

    raising = OpenTelemetryObserver(tracer=RaisingTracer())
    events = [e async for e in run(ONE, _ports(raising), options=RunOptions(lease=LEASE))]
    assert [e for e in events if isinstance(e, Ended)][-1].reason == "completed"


def test_every_event_kind_is_accounted_for() -> None:
    """A new kind must say what the trace does with it, or this fails. The twelfth, `Reasoning`,
    arrived in Phase 21 and this said so before anything else did: it carries length, never text
    (D28)."""
    import dataclasses

    from shadow_hdk.kernel import events as module

    kinds = {
        cls.kind
        for cls in vars(module).values()
        if isinstance(cls, type) and dataclasses.is_dataclass(cls) and hasattr(cls, "kind")
    }
    assert kinds == OpenTelemetryObserver.HANDLED
    assert len(kinds) == 15  # input_requested (D61), mode_changed (D64), workspace_changed (D76)


async def test_a_run_that_fails_mid_step_ends_the_step_span() -> None:
    """A port failure lands between `Invoked` and `Observed`; the step span must not leak."""
    from shadow_hdk.kernel.events import Invoked

    tracer = RecordingTracer()
    observer = OpenTelemetryObserver(tracer=tracer)
    at = Stamp().at
    await observer.on(Invoked(run_id="r", seq=1, at=at, step="s1", component="look", inputs={}))
    await observer.on(
        Ended(run_id="r", seq=2, at=at, reason="failed", steps_taken=1, detail="model port down")
    )
    assert _one(tracer.named("shadow_hdk.step")).ended
    assert observer.open_steps == 0 and observer.open_runs == 0


async def test_a_proposal_is_an_event_on_the_step_that_made_it_with_its_kind_only() -> None:
    from shadow_hdk.kernel import Proposal

    async def proposes(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        await context.propose(
            Proposal(
                kind="finding",
                payload={"secret": "PAYLOAD-ONLY"},
                provenance=LOOK.component.provenance,
            )
        )
        return Completed(None)

    tracer = RecordingTracer()
    observer = OpenTelemetryObserver(tracer=tracer)
    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(LOOK, proposes)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
        observer=observer,
    )
    async for _ in run(ONE, ports, options=RunOptions(lease=LEASE)):
        pass
    step = _one(tracer.named("shadow_hdk.step"))
    proposed = _one([e for e in step.events if e.name == "proposed"])
    assert proposed.attributes == {"shadow_hdk.proposal.kind": "finding"}
    assert "PAYLOAD-ONLY" not in tracer.everything_recorded()


@pytest.mark.parametrize("bad", ["not a time", ""])
async def test_an_unparseable_at_leaves_the_time_to_the_sdk(bad: str) -> None:
    tracer = RecordingTracer()
    observer = OpenTelemetryObserver(tracer=tracer)
    await observer.on(Ended(run_id="r", seq=1, at=bad, reason="completed", steps_taken=0))
    assert _one(tracer.named("shadow_hdk.run")).end_time is None
