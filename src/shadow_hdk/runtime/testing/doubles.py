"""The five doubles, and one helper that builds a registration without ceremony."""

from __future__ import annotations

import itertools
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from datetime import datetime, timedelta

from pydantic import JsonValue

from shadow_hdk.kernel.components import (
    Component,
    Interface,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.effects import NOTHING, EffectProfile
from shadow_hdk.kernel.events import Event
from shadow_hdk.kernel.observations import Completed, Failed, Observation, Proposal
from shadow_hdk.kernel.ports import (
    Allow,
    ClockPort,
    ComponentPort,
    Context,
    GovernancePort,
    Judgement,
    ModelChunk,
    ModelPort,
    ModelRequest,
    ModelResponse,
    ObserverPort,
    SinkPort,
)


class FixedClock(ClockPort):
    """Time that only moves when you move it, and ids that count."""

    def __init__(self, start: str = "2026-01-01T00:00:00+00:00") -> None:
        self._now = datetime.fromisoformat(start)
        self._ids = itertools.count(1)

    def now(self) -> str:
        return self._now.isoformat()

    def new_id(self) -> str:
        return f"id-{next(self._ids):04d}"

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


def make_registration(
    name: str,
    *,
    effects: EffectProfile = NOTHING,
    description: str = "",
    labels: frozenset[str] = frozenset({"tool"}),
    registration_id: RegistrationId | None = None,
    input_schema: dict[str, JsonValue] | None = None,
    output_schema: dict[str, JsonValue] | None = None,
) -> Registration:
    return Registration(
        id=registration_id or name,
        component=Component(
            interface=Interface(
                name=name,
                description=description or f"the {name} component",
                input_schema=input_schema or {"type": "object"},
                output_schema=output_schema or {"type": "object"},
            ),
            effects=effects,
            provenance=Provenance(
                registered_by="tests", adapter="in-memory", at="2026-01-01T00:00:00+00:00"
            ),
            labels=labels,
        ),
    )


Handler = Callable[[JsonValue], Awaitable[Observation]]


class InMemoryComponents(ComponentPort):
    """A component port over a dict. `add` takes a registration and what to run."""

    def __init__(self, entries: Sequence[tuple[Registration, Handler]] = ()) -> None:
        self._entries: dict[RegistrationId, tuple[Registration, Handler]] = {}
        for registration, handler in entries:
            self.add(registration, handler)
        self.calls: list[tuple[RegistrationId, JsonValue]] = []

    def add(self, registration: Registration, handler: Handler) -> Registration:
        self._entries[registration.id] = (registration, handler)
        return registration

    async def registrations(self) -> Sequence[Registration]:
        return [registration for registration, _ in self._entries.values()]

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        self.calls.append((registration, inputs))
        entry = self._entries.get(registration)
        if entry is None:
            return Failed(f"no component registered as {registration!r}")
        return await entry[1](inputs)


async def echo(inputs: JsonValue) -> Observation:
    """The no-op handler the benchmark and most tests use."""
    return Completed(inputs)


class ScriptedModel(ModelPort):
    """Says exactly what it was told to, in order, and records what it was asked."""

    def __init__(self, responses: Sequence[ModelResponse] = ()) -> None:
        self._responses = list(responses)
        self.requests: list[ModelRequest] = []

    def then(self, response: ModelResponse) -> ScriptedModel:
        self._responses.append(response)
        return self

    async def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError("the scripted model ran out of responses")
        return self._responses.pop(0)

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelChunk]:
        """The scripted answer, cut into deltas at word boundaries — deterministically, so a replay
        of a streamed run is still byte-for-byte the same as the one before it."""
        response = await self.complete(request)
        words = response.text.split(" ")
        for index, word in enumerate(words):
            if word or index:
                yield ModelChunk(text=word if index == 0 else " " + word)
        yield ModelChunk(tool_calls=response.tool_calls, usage=response.usage, done=True)


class ListSink(SinkPort):
    def __init__(self) -> None:
        self.proposals: list[Proposal] = []

    async def propose(self, proposal: Proposal) -> None:
        self.proposals.append(proposal)


class ListObserver(ObserverPort):
    def __init__(self, *, raises: bool = False) -> None:
        self.events: list[Event] = []
        self._raises = raises

    async def on(self, event: Event) -> None:
        if self._raises:
            raise RuntimeError("this observer is broken on purpose")
        self.events.append(event)


class Judge(GovernancePort):
    """Governance as a function of the six fields, so a test states its policy in one line.

    The decision function is **sync** on purpose: a test that wants the port to fail writes a
    function that raises, and the executor's `PortFailure` wrapping is what is under test.
    """

    def __init__(self, decide: Callable[[EffectProfile, Context], Judgement]) -> None:
        self._decide = decide
        self.calls: list[tuple[EffectProfile, Context]] = []

    @classmethod
    def allow_all(cls) -> Judge:
        return cls(lambda _effects, _context: Allow())

    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        self.calls.append((effects, context))
        return self._decide(effects, context)
