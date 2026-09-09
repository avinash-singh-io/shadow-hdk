"""One abstract suite per port. Every adapter subclasses the one it implements.

*"It implements the port"* is then a test result rather than a claim, and a new adapter cannot ship
having satisfied only the parts of a protocol its author remembered.

The suites assert what the runtime **relies on**, and nothing more. They do not assert that a
governance port allows anything (a deny-all policy is legitimate) or that a model says something in
particular (that is the model's business). What they assert is that the runtime's own assumptions
hold: an unknown component is data rather than an exception, an unpriced call says unknown rather
than zero, a clock never goes backwards.

Subclass with a name starting `Test` so pytest collects the inherited methods.
"""

from __future__ import annotations

from pydantic import JsonValue

from shadow_hdk.kernel.components import Provenance, RegistrationId
from shadow_hdk.kernel.contracts import CONTRACTS, round_trip
from shadow_hdk.kernel.effects import ASSUME_WORST, NOTHING, EffectProfile, ScopeSet
from shadow_hdk.kernel.events import Ended, Event, Started
from shadow_hdk.kernel.leases import Ceiling, Floor, Lease
from shadow_hdk.kernel.observations import Completed, Observation, Proposal
from shadow_hdk.kernel.ports import (
    Allow,
    Ask,
    ClockPort,
    ComponentPort,
    Context,
    GovernancePort,
    ModelPort,
    ModelRequest,
    ObserverPort,
    Refuse,
    SinkPort,
)

A_CONTEXT = Context(run_id="run-1", step="s1", principal="person:1", attributes={"mode": "build"})
A_LEASE = Lease(Ceiling(10, 600, 100), Floor(0))
A_PROVENANCE = Provenance(registered_by="tests", adapter="contract", at="2026-01-01T00:00:00+00:00")

PROFILE_SHAPES: tuple[EffectProfile, ...] = (
    NOTHING,
    ASSUME_WORST,
    EffectProfile(reads=ScopeSet.of("workspace")),
    EffectProfile(writes=ScopeSet.of("record"), reversible=True),
    EffectProfile(reaches=True, reversible=False, contained=False, costs=True),
    EffectProfile(reads=ScopeSet(everything=True), writes=ScopeSet(everything=True)),
)


class ComponentPortContract:
    """Override `port` and `valid_call`."""

    def port(self) -> ComponentPort:
        raise NotImplementedError

    def valid_call(self) -> tuple[RegistrationId, JsonValue]:
        raise NotImplementedError

    async def test_registrations_are_well_formed(self) -> None:
        registrations = list(await self.port().registrations())
        assert registrations, "a component port with nothing in it cannot be contract-tested"
        assert len({r.id for r in registrations}) == len(registrations), "ids must be unique"
        for registration in registrations:
            assert registration.component.interface.name
            assert isinstance(registration.component.effects, EffectProfile)
            assert registration.component.provenance.adapter

    async def test_every_registration_round_trips_through_json(self) -> None:
        for registration in await self.port().registrations():
            assert round_trip(registration, CONTRACTS["Registration"]) == registration

    async def test_an_unknown_id_is_an_observation_not_an_exception(self) -> None:
        observation = await self.port().invoke("no-such-component", {})
        assert observation.kind == "failed", "an unknown id is data the agent can route around"

    async def test_a_known_call_returns_an_observation_that_round_trips(self) -> None:
        registration, inputs = self.valid_call()
        observation = await self.port().invoke(registration, inputs)
        assert round_trip(observation, CONTRACTS["Observation"]) == observation


class ModelPortContract:
    """Override `port` and `a_request`."""

    def port(self) -> ModelPort:
        raise NotImplementedError

    def a_request(self) -> ModelRequest:
        raise NotImplementedError

    async def test_a_request_returns_a_response(self) -> None:
        response = await self.port().complete(self.a_request())
        assert isinstance(response.text, str)
        assert isinstance(response.tool_calls, tuple)

    async def test_a_response_round_trips_through_json(self) -> None:
        response = await self.port().complete(self.a_request())
        assert round_trip(response, CONTRACTS["ModelResponse"]) == response

    async def test_streaming_yields_at_least_one_chunk(self) -> None:
        chunks = [chunk async for chunk in self.port().stream(self.a_request())]
        assert chunks, "a stream that yields nothing is not a stream"

    async def test_exactly_one_chunk_says_it_is_the_last(self) -> None:
        """Written so it holds for a live model too: nothing here compares two calls, because two
        calls to a real provider are two different answers."""
        chunks = [chunk async for chunk in self.port().stream(self.a_request())]
        assert chunks[-1].done, "the last chunk must say so"
        assert not any(chunk.done for chunk in chunks[:-1]), "only the last chunk is the last"

    async def test_what_the_call_cost_arrives_at_the_end_or_not_at_all(self) -> None:
        chunks = [chunk async for chunk in self.port().stream(self.a_request())]
        priced = [chunk for chunk in chunks if chunk.usage is not None]
        assert priced in ([], [chunks[-1]]), "cost is not known until the call ends"
        for chunk in priced:
            usage = chunk.usage
            assert usage is not None
            for value in (usage.input_tokens, usage.output_tokens, usage.cost_cents):
                assert value is None or isinstance(value, int)

    async def test_usage_is_a_number_or_unknown_never_a_guess(self) -> None:
        usage = (await self.port().complete(self.a_request())).usage
        if usage is None:
            return
        for value in (usage.input_tokens, usage.output_tokens, usage.cost_cents):
            assert value is None or isinstance(value, int), "unknown is None, never 0"


class GovernancePortContract:
    """Override `port`."""

    def port(self) -> GovernancePort:
        raise NotImplementedError

    async def test_it_answers_every_profile_shape_with_a_judgement(self) -> None:
        for profile in PROFILE_SHAPES:
            judgement = await self.port().judge(profile, A_CONTEXT)
            assert isinstance(judgement, Allow | Ask | Refuse), f"{profile} got {judgement!r}"

    async def test_a_judgement_round_trips_through_json(self) -> None:
        for profile in PROFILE_SHAPES:
            judgement = await self.port().judge(profile, A_CONTEXT)
            assert round_trip(judgement, CONTRACTS["Judgement"]) == judgement


class SinkPortContract:
    """Override `port`."""

    def port(self) -> SinkPort:
        raise NotImplementedError

    async def test_it_accepts_every_proposal_shape(self) -> None:
        shapes: tuple[JsonValue, ...] = (None, 1, "text", ["a"], {"k": {"nested": True}})
        for payload in shapes:
            await self.port().propose(
                Proposal(kind="claim", payload=payload, provenance=A_PROVENANCE)
            )

    async def test_it_accepts_a_proposal_with_grounds(self) -> None:
        await self.port().propose(
            Proposal(kind="claim", payload={}, provenance=A_PROVENANCE, grounds=("s1", "s2"))
        )


class ObserverPortContract:
    """Override `port`."""

    def port(self) -> ObserverPort:
        raise NotImplementedError

    async def test_it_accepts_the_events_that_bracket_every_run(self) -> None:
        at = "2026-01-01T00:00:00+00:00"
        await self.port().on(Started(run_id="run-1", seq=0, at=at, lease=A_LEASE))
        await self.port().on(Ended(run_id="run-1", seq=1, at=at, reason="completed", steps_taken=0))

    async def test_it_accepts_an_observation_carrying_event(self) -> None:
        from shadow_hdk.kernel.events import Observed

        await self.port().on(
            Observed(
                run_id="run-1",
                seq=2,
                at="2026-01-01T00:00:00+00:00",
                step="s1",
                observation=Completed({"n": 1}),
            )
        )


class ClockPortContract:
    """Override `port`."""

    def port(self) -> ClockPort:
        raise NotImplementedError

    def test_now_is_parseable_and_never_goes_backwards(self) -> None:
        from datetime import datetime

        clock = self.port()
        readings = [datetime.fromisoformat(clock.now()) for _ in range(5)]
        assert readings == sorted(readings), "a clock that goes backwards breaks every lease"

    def test_new_id_does_not_repeat(self) -> None:
        clock = self.port()
        ids = [clock.new_id() for _ in range(50)]
        assert len(set(ids)) == 50


def an_observation() -> Observation:
    return Completed({"ok": True})


def an_event() -> Event:
    return Started(run_id="run-1", seq=0, at="2026-01-01T00:00:00+00:00", lease=A_LEASE)
