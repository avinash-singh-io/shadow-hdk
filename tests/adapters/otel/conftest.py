"""A tracer that records, over the API's abstract classes — test-local on purpose.

The SDK is not a dependency of the adapter and must not become one to test it; a tracer written
against `opentelemetry.trace.{TracerProvider, Tracer, Span}` proves the observer uses the API
alone, and gives a test the spans as objects instead of an exporter's bytes.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace import (
    INVALID_SPAN,
    Link,
    Span,
    SpanContext,
    SpanKind,
    Status,
    StatusCode,
    TraceFlags,
    Tracer,
    TracerProvider,
)
from opentelemetry.util import types

_IDS = itertools.count(1)


@dataclass
class Recorded:
    name: str
    attributes: dict[str, Any]


class RecordingSpan(Span):
    def __init__(
        self,
        name: str,
        parent: RecordingSpan | None,
        attributes: Mapping[str, Any] | None,
        start_time: int | None,
    ) -> None:
        self.name = name
        self.parent = parent
        self.attributes: dict[str, Any] = dict(attributes or {})
        self.events: list[Recorded] = []
        self.links: list[SpanContext] = []
        self.status: Status = Status(StatusCode.UNSET)
        self.start_time = start_time
        self.end_time: int | None = None
        self.ended = False
        self._context = SpanContext(
            trace_id=parent.get_span_context().trace_id if parent else next(_IDS),
            span_id=next(_IDS),
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )

    def end(self, end_time: int | None = None) -> None:
        self.ended = True
        self.end_time = end_time

    def get_span_context(self) -> SpanContext:
        return self._context

    def set_attributes(self, attributes: Mapping[str, types.AttributeValue]) -> None:
        self.attributes.update(attributes)

    def set_attribute(self, key: str, value: types.AttributeValue) -> None:
        self.attributes[key] = value

    def add_event(
        self,
        name: str,
        attributes: types.Attributes = None,
        timestamp: int | None = None,
    ) -> None:
        self.events.append(Recorded(name, dict(attributes or {})))

    def add_link(self, context: SpanContext, attributes: types.Attributes = None) -> None:
        self.links.append(context)

    def update_name(self, name: str) -> None:
        self.name = name

    def is_recording(self) -> bool:
        return not self.ended

    def set_status(self, status: Status | StatusCode, description: str | None = None) -> None:
        self.status = status if isinstance(status, Status) else Status(status, description)

    def record_exception(
        self,
        exception: BaseException,
        attributes: types.Attributes = None,
        timestamp: int | None = None,
        escaped: bool = False,
    ) -> None:
        self.events.append(Recorded("exception", {"type": type(exception).__name__}))


class RecordingTracer(Tracer):
    def __init__(self) -> None:
        self.spans: list[RecordingSpan] = []

    def start_span(
        self,
        name: str,
        context: Context | None = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: types.Attributes = None,
        links: Sequence[Link] | None = None,
        start_time: int | None = None,
        record_exception: bool = True,
        set_status_on_exception: bool = True,
    ) -> Span:
        parent = trace.get_current_span(context) if context is not None else INVALID_SPAN
        span = RecordingSpan(
            name, parent if isinstance(parent, RecordingSpan) else None, attributes, start_time
        )
        self.spans.append(span)
        return span

    @contextmanager
    def start_as_current_span(  # type: ignore[override]
        self, name: str, *args: Any, **kwargs: Any
    ) -> Iterator[Span]:
        span = self.start_span(name, *args, **kwargs)
        with trace.use_span(span, end_on_exit=True):
            yield span

    # ---- what a test asks

    def named(self, name: str) -> list[RecordingSpan]:
        return [s for s in self.spans if s.name == name]

    def everything_recorded(self) -> str:
        """Every attribute and event value, as one string — for asserting a secret is nowhere."""
        parts: list[str] = []
        for span in self.spans:
            parts.append(repr(span.attributes))
            parts.extend(repr(e.attributes) for e in span.events)
        return "\n".join(parts)


class RecordingProvider(TracerProvider):
    def __init__(self, tracer: RecordingTracer) -> None:
        self.tracer = tracer

    def get_tracer(
        self,
        instrumenting_module_name: str,
        instrumenting_library_version: str | None = None,
        schema_url: str | None = None,
        attributes: types.Attributes = None,
    ) -> Tracer:
        return self.tracer


class RaisingTracer(RecordingTracer):
    """The collector is down, and the client library says so by raising."""

    def start_span(self, name: str, *args: Any, **kwargs: Any) -> Span:
        raise RuntimeError("the collector is down")


@dataclass
class Stamp:
    """`at` for hand-built events, and the nanoseconds a span should carry for it."""

    at: str = "2026-01-01T00:00:00+00:00"
    ns: int = field(default=1_767_225_600_000_000_000)
