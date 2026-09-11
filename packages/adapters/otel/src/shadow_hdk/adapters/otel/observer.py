"""The shape of a run as a trace, over the OpenTelemetry API alone (D28).

One span per run, one per step. `Started` opens the run span — a child's parented on its parent's
— and `Ended` closes it with the reason; `Invoked` and `Observed` bracket a step span under it;
`Spent` sets usage on the open step; `Composed`, `Proposed`, `Refused`, `Asked`, `Spawned` and
`Held` are span events carrying their own fields. Names are the events' field names under
`shadow_hdk.`. **Never on a span:** inputs, an observation's output, a proposal's payload, a
composition, an act's grounds — the record has those, and a trace goes where the deployment
pointed it.

Spans open lazily on first sight of a run or a step, so a stream this process did not see start
— a run parked elsewhere and resumed here — still traces. Only *recording* spans are kept: with no
provider configured the API hands back non-recording spans, nothing is stored, and the observer
costs a dictionary lookup per event. Timestamps are the record's own `at`, not the moment this
observer drained its queue.

A tracer that raises is not caught here: the emitter counts it (D6), and hiding it would make a
silent trace look like a quiet run.
"""

from __future__ import annotations

from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Final

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode, Tracer
from opentelemetry.util.types import AttributeValue

from shadow_hdk.kernel.events import Event, RunId
from shadow_hdk.kernel.leases import Lease
from shadow_hdk.kernel.observations import Acted, Observation
from shadow_hdk.kernel.ports import ObserverPort
from shadow_hdk.kernel.usage import Usage

try:
    VERSION: str | None = version("shadow-hdk-adapters-otel")
except PackageNotFoundError:  # pragma: no cover — an unbuilt checkout
    VERSION = None

RUN: Final = "shadow_hdk.run"
STEP: Final = "shadow_hdk.step"

Attributes = dict[str, AttributeValue]


class OpenTelemetryObserver(ObserverPort):
    HANDLED: Final = frozenset(
        {
            "started",
            "composed",
            "invoked",
            "observed",
            "proposed",
            "refused",
            "asked",
            "spawned",
            "spent",
            "held",
            "reasoned",
            "ended",
        }
    )

    def __init__(self, tracer: Tracer | None = None) -> None:
        # Through the API's proxy when not given, so a provider configured later is honoured.
        self._tracer = tracer if tracer is not None else trace.get_tracer("shadow_hdk", VERSION)
        self._runs: dict[RunId, Span] = {}
        self._steps: dict[tuple[RunId, str], Span] = {}

    @property
    def open_runs(self) -> int:
        return len(self._runs)

    @property
    def open_steps(self) -> int:
        return len(self._steps)

    async def on(self, event: Event) -> None:
        at = _nanoseconds(event.at)
        match event.kind:
            case "started":
                parent = self._runs.get(event.parent_run_id) if event.parent_run_id else None
                attributes: Attributes = {"shadow_hdk.run_id": event.run_id, **_lease(event.lease)}
                if event.parent_run_id is not None:
                    attributes["shadow_hdk.parent_run_id"] = event.parent_run_id
                self._open_run(event.run_id, attributes, parent, at)
            case "composed":
                self._run(event.run_id, at).add_event(
                    "composed", {"shadow_hdk.composition.steps": len(event.composition.steps)}, at
                )
            case "invoked":
                run_span = self._run(event.run_id, at)
                self._open_step(
                    event.run_id,
                    event.step,
                    {"shadow_hdk.step": event.step, "shadow_hdk.component": event.component},
                    run_span,
                    at,
                )
            case "observed":
                step_span = self._step(event.run_id, event.step, at)
                step_span.add_event("observed", _observation(event.observation), at)
                step_span.end(at)
                self._steps.pop((event.run_id, event.step), None)
            case "proposed":
                self._innermost(event.run_id, at).add_event(
                    "proposed", {"shadow_hdk.proposal.kind": event.proposal.kind}, at
                )
            case "refused":
                self._run(event.run_id, at).add_event(
                    "refused", {"shadow_hdk.step": event.step, "shadow_hdk.reason": event.reason}, at
                )
            case "asked":
                self._run(event.run_id, at).add_event(
                    "asked",
                    {
                        "shadow_hdk.step": event.step,
                        "shadow_hdk.question": event.question,
                        "shadow_hdk.handle": event.handle,
                    },
                    at,
                )
            case "spawned":
                self._run(event.run_id, at).add_event(
                    "spawned",
                    {"shadow_hdk.child_run_id": event.child_run_id, **_lease(event.lease)},
                    at,
                )
            case "reasoned":
                # Length, never the text (D28): a trace carries the *shape* of a run, and a
                # model's reasoning is a payload — often the most sensitive one on the record.
                self._run(event.run_id, at).add_event(
                    "reasoned", {"shadow_hdk.step": event.step, "shadow_hdk.chars": len(event.text)}, at
                )
            case "spent":
                self._innermost(event.run_id, at, step=event.step).set_attributes(
                    _usage(event.usage)
                )
            case "held":
                self._run(event.run_id, at).add_event(
                    "held",
                    {
                        "shadow_hdk.child_run_id": event.child_run_id,
                        "shadow_hdk.handle": event.handle,
                        "shadow_hdk.steps_spent": event.steps_spent,
                    },
                    at,
                )
            case "ended":
                run_span = self._run(event.run_id, at)
                ending: Attributes = {
                    "shadow_hdk.reason": event.reason,
                    "shadow_hdk.steps_taken": event.steps_taken,
                }
                if event.detail is not None:
                    ending["shadow_hdk.detail"] = event.detail
                run_span.set_attributes(ending)
                if event.reason == "failed":
                    run_span.set_status(Status(StatusCode.ERROR, event.detail))
                for key in [k for k in self._steps if k[0] == event.run_id]:
                    self._steps.pop(key).end(at)
                run_span.end(at)
                self._runs.pop(event.run_id, None)

    # ------------------------------------------------------------------ spans, lazily

    def _open_run(
        self, run_id: RunId, attributes: Attributes, parent: Span | None, at: int | None
    ) -> Span:
        context = trace.set_span_in_context(parent) if parent is not None else None
        span = self._tracer.start_span(RUN, context=context, attributes=attributes, start_time=at)
        if span.is_recording():
            self._runs[run_id] = span
        return span

    def _run(self, run_id: RunId, at: int | None) -> Span:
        """The run's span, opened on first sight if this process never saw it start."""
        span = self._runs.get(run_id)
        return (
            span
            if span is not None
            else self._open_run(run_id, {"shadow_hdk.run_id": run_id}, None, at)
        )

    def _open_step(
        self, run_id: RunId, step: str, attributes: Attributes, parent: Span, at: int | None
    ) -> Span:
        span = self._tracer.start_span(
            STEP, context=trace.set_span_in_context(parent), attributes=attributes, start_time=at
        )
        if span.is_recording():
            self._steps[(run_id, step)] = span
        return span

    def _step(self, run_id: RunId, step: str, at: int | None) -> Span:
        span = self._steps.get((run_id, step))
        if span is not None:
            return span
        return self._open_step(run_id, step, {"shadow_hdk.step": step}, self._run(run_id, at), at)

    def _innermost(self, run_id: RunId, at: int | None, *, step: str | None = None) -> Span:
        """The open step span if there is one — the named one, or the run's only one — else the
        run's."""
        if step is not None:
            named = self._steps.get((run_id, step))
            if named is not None:
                return named
        open_steps = [span for (rid, _), span in self._steps.items() if rid == run_id]
        return open_steps[0] if len(open_steps) == 1 else self._run(run_id, at)


# ---------------------------------------------------------------------- the shape of a field


def _lease(lease: Lease) -> Attributes:
    attributes: Attributes = {
        "shadow_hdk.lease.max_steps": lease.ceiling.max_steps,
        "shadow_hdk.lease.max_wall_seconds": lease.ceiling.max_wall_seconds,
    }
    if lease.ceiling.max_cost_cents is not None:
        attributes["shadow_hdk.lease.max_cost_cents"] = lease.ceiling.max_cost_cents
    return attributes


def _usage(usage: Usage) -> Attributes:
    attributes: Attributes = {}
    for name in ("input_tokens", "output_tokens", "cost_cents"):
        value = getattr(usage, name)
        if value is not None:
            attributes[f"shadow_hdk.usage.{name}"] = value
    return attributes


def _observation(observation: Observation) -> Attributes:
    """The kind, and for an act its receipt. Never an output, a reason's payload, or grounds."""
    attributes: Attributes = {"shadow_hdk.observation.kind": observation.kind}
    if isinstance(observation, Acted):
        attributes["shadow_hdk.observation.foreign_id"] = observation.foreign_id
        attributes["shadow_hdk.observation.idempotency_key"] = observation.idempotency_key
        attributes["shadow_hdk.observation.exit"] = observation.exit
    return attributes


def _nanoseconds(at: str) -> int | None:
    """The record's own time, for the span; `None` leaves the stamp to whoever exports it."""
    try:
        return int(datetime.fromisoformat(at).timestamp() * 1_000_000_000)
    except ValueError:
        return None


__all__ = ["OpenTelemetryObserver"]
