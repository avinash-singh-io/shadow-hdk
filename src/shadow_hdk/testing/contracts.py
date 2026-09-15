"""One abstract suite per port — shipped (D91), so a product proves its own implementation of a
port with the very tests the kit's adapters pass. Every adapter subclasses the one it implements.

    from shadow_hdk.testing.contracts import ThreadStoreContract

    class TestMyThreadsIsAThreadStore(ThreadStoreContract):
        def store(self) -> MyThreads:
            return MyThreads(fresh_database())

The suites are plain classes of `async def test_*` methods; run them with pytest and
`pytest-asyncio` or anyio (`pytestmark = pytest.mark.anyio`), as this kit does.

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

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from pydantic import JsonValue

from shadow_hdk.kernel.authority import (
    AuthoritySnapshot,
    EffectAuthorization,
    EffectEntry,
    StagedEffect,
)
from shadow_hdk.kernel.components import Provenance, RegistrationId
from shadow_hdk.kernel.contracts import CONTRACTS, round_trip
from shadow_hdk.kernel.effects import ASSUME_WORST, NOTHING, EffectProfile, ScopeSet
from shadow_hdk.kernel.events import Ended, Event, Started
from shadow_hdk.kernel.leases import Ceiling, Floor, Lease
from shadow_hdk.kernel.observations import Completed, Observation, Proposal
from shadow_hdk.kernel.ports import (
    Allow,
    Ask,
    AuthorityPort,
    AuthorizerPort,
    ClockPort,
    ComponentPort,
    Context,
    EffectJournalPort,
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
    """Override `port` and `valid_call` — or `using`, when the adapter has a lifetime.

    Some component ports are a live thing: an MCP server is a subprocess and a handshake. Those are
    entered and exited **inside each test**, because a session opened in one task and closed in
    another is exactly what anyio refuses.
    """

    def port(self) -> ComponentPort:
        raise NotImplementedError

    def valid_call(self) -> tuple[RegistrationId, JsonValue]:
        raise NotImplementedError

    @asynccontextmanager
    async def using(self) -> AsyncIterator[ComponentPort]:
        yield self.port()

    async def test_registrations_are_well_formed(self) -> None:
        async with self.using() as port:
            registrations = list(await port.registrations())
            assert registrations, "a component port with nothing in it cannot be contract-tested"
            assert len({r.id for r in registrations}) == len(registrations), "ids must be unique"
            for registration in registrations:
                assert registration.component.interface.name
                assert isinstance(registration.component.effects, EffectProfile)
                assert registration.component.provenance.adapter

    async def test_every_registration_round_trips_through_json(self) -> None:
        async with self.using() as port:
            for registration in await port.registrations():
                assert round_trip(registration, CONTRACTS["Registration"]) == registration

    async def test_an_unknown_id_is_an_observation_not_an_exception(self) -> None:
        async with self.using() as port:
            observation = await port.invoke("no-such-component", {})
        assert observation.kind == "failed", "an unknown id is data the agent can route around"

    async def test_a_known_call_returns_an_observation_that_round_trips(self) -> None:
        registration, inputs = self.valid_call()
        async with self.using() as port:
            observation = await port.invoke(registration, inputs)
        assert round_trip(observation, CONTRACTS["Observation"]) == observation

    async def test_inputs_of_the_wrong_shape_are_an_observation_not_an_exception(self) -> None:
        """D7 from the other side. An unknown **id** was already covered; a known id with inputs
        the component cannot use is the commoner case by far — it is what a model produces when it
        misreads a schema — and *the agent must be able to route around it*.

        Four shapes, because a component that guards `dict` and forgets `None` guards nothing: a
        model that omits the argument object entirely sends exactly that.
        """
        registration, _ = self.valid_call()
        async with self.using() as port:
            shapes: tuple[JsonValue, ...] = (
                None,
                "a string where an object goes",
                [],
                {"no": "such field"},
            )
            for nonsense in shapes:
                observation = await port.invoke(registration, nonsense)
                assert observation.kind in {"completed", "failed", "refused", "pending", "acted"}, (
                    f"{nonsense!r} produced {observation!r}"
                )
                assert round_trip(observation, CONTRACTS["Observation"]) == observation


class ModelPortContract:
    """Override `port` and `a_request` — or `using`, when the port has a lifetime (a model on the
    far side of a wire is reached through a session, entered and left inside each test)."""

    def port(self) -> ModelPort:
        raise NotImplementedError

    def a_request(self) -> ModelRequest:
        raise NotImplementedError

    @asynccontextmanager
    async def using(self) -> AsyncIterator[ModelPort]:
        yield self.port()

    async def test_a_request_returns_a_response(self) -> None:
        async with self.using() as port:
            response = await port.complete(self.a_request())
        assert isinstance(response.text, str)
        assert isinstance(response.tool_calls, tuple)

    async def test_a_response_round_trips_through_json(self) -> None:
        async with self.using() as port:
            response = await port.complete(self.a_request())
        assert round_trip(response, CONTRACTS["ModelResponse"]) == response

    async def test_streaming_yields_at_least_one_chunk(self) -> None:
        async with self.using() as port:
            chunks = [chunk async for chunk in port.stream(self.a_request())]
        assert chunks, "a stream that yields nothing is not a stream"

    async def test_exactly_one_chunk_says_it_is_the_last(self) -> None:
        """Written so it holds for a live model too: nothing here compares two calls, because two
        calls to a real provider are two different answers."""
        async with self.using() as port:
            chunks = [chunk async for chunk in port.stream(self.a_request())]
        assert chunks[-1].done, "the last chunk must say so"
        assert not any(chunk.done for chunk in chunks[:-1]), "only the last chunk is the last"

    async def test_what_the_call_cost_arrives_at_the_end_or_not_at_all(self) -> None:
        async with self.using() as port:
            chunks = [chunk async for chunk in port.stream(self.a_request())]
        priced = [chunk for chunk in chunks if chunk.usage is not None]
        assert priced in ([], [chunks[-1]]), "cost is not known until the call ends"
        for chunk in priced:
            usage = chunk.usage
            assert usage is not None
            for value in (usage.input_tokens, usage.output_tokens, usage.cost_cents):
                assert value is None or isinstance(value, int)

    async def test_usage_is_a_number_or_unknown_never_a_guess(self) -> None:
        async with self.using() as port:
            usage = (await port.complete(self.a_request())).usage
        if usage is None:
            return
        for value in (usage.input_tokens, usage.output_tokens, usage.cost_cents):
            assert value is None or isinstance(value, int), "unknown is None, never 0"


class GovernancePortContract:
    """Override `port` — or `using`, when the port has a lifetime."""

    def port(self) -> GovernancePort:
        raise NotImplementedError

    @asynccontextmanager
    async def using(self) -> AsyncIterator[GovernancePort]:
        yield self.port()

    async def test_it_answers_every_profile_shape_with_a_judgement(self) -> None:
        async with self.using() as port:
            for profile in PROFILE_SHAPES:
                judgement = await port.judge(profile, A_CONTEXT)
                assert isinstance(judgement, Allow | Ask | Refuse), f"{profile} got {judgement!r}"

    async def test_a_judgement_round_trips_through_json(self) -> None:
        async with self.using() as port:
            for profile in PROFILE_SHAPES:
                judgement = await port.judge(profile, A_CONTEXT)
                assert round_trip(judgement, CONTRACTS["Judgement"]) == judgement


class SinkPortContract:
    """Override `port` — or `using`, when the port has a lifetime."""

    def port(self) -> SinkPort:
        raise NotImplementedError

    @asynccontextmanager
    async def using(self) -> AsyncIterator[SinkPort]:
        yield self.port()

    async def test_it_accepts_every_proposal_shape(self) -> None:
        shapes: tuple[JsonValue, ...] = (None, 1, "text", ["a"], {"k": {"nested": True}})
        async with self.using() as port:
            for payload in shapes:
                await port.propose(Proposal(kind="claim", payload=payload, provenance=A_PROVENANCE))

    async def test_it_accepts_a_proposal_with_grounds(self) -> None:
        async with self.using() as port:
            await port.propose(
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


class AuthorityPortContract:
    """Override `authority` and the run/step whose current snapshot can be read."""

    def authority(self) -> AuthorityPort:
        raise NotImplementedError

    async def test_current_authority_is_stable_data_that_round_trips(self) -> None:
        port = self.authority()
        first = await port.current(run_id="run-1", step="s1")
        second = await port.current(run_id="run-1", step="s1")
        assert isinstance(first, AuthoritySnapshot)
        assert first == second
        assert round_trip(first, CONTRACTS["AuthoritySnapshot"]) == first
        assert not any(callable(value) for value in first.__dict__.values())


class AuthorizerPortContract:
    """Override `authorizer`, `effect` and `authority_snapshot`."""

    def authorizer(self) -> AuthorizerPort:
        raise NotImplementedError

    def effect(self) -> StagedEffect:
        raise NotImplementedError

    def authority_snapshot(self) -> AuthoritySnapshot:
        raise NotImplementedError

    async def test_authorization_is_a_bound_data_grant_or_a_typed_refusal(self) -> None:
        result = await self.authorizer().authorize(self.effect(), self.authority_snapshot())
        assert isinstance(result, EffectAuthorization | Refuse)
        if isinstance(result, EffectAuthorization):
            assert round_trip(result, CONTRACTS["EffectAuthorization"]) == result
            assert result.permits(self.effect(), self.authority_snapshot())


class EffectJournalContract:
    """Override `journal` and `entries` with one legal two-entry history."""

    def journal(self) -> EffectJournalPort:
        raise NotImplementedError

    def entries(self) -> tuple[EffectEntry, EffectEntry]:
        raise NotImplementedError

    async def test_append_is_ordered_and_every_entry_round_trips(self) -> None:
        journal = self.journal()
        first, second = self.entries()
        assert await journal.read(first.attempt_id) == ()
        await journal.append(first, expected_length=0)
        await journal.append(second, expected_length=1)
        assert await journal.read(first.attempt_id) == (first, second)
        for row in await journal.read(first.attempt_id):
            assert round_trip(row, CONTRACTS["EffectEntry"]) == row

    async def test_compare_and_append_refuses_a_stale_writer(self) -> None:
        journal = self.journal()
        first, second = self.entries()
        await journal.append(first, expected_length=0)
        try:
            await journal.append(second, expected_length=0)
        except Exception:  # noqa: BLE001 — products choose their conflict type
            pass
        else:
            raise AssertionError("a stale expected length appended an incompatible fact")


class ThreadStoreContract:
    """Override `store` with a fresh, empty store each call (D62)."""

    def store(self) -> Any:
        raise NotImplementedError

    async def test_a_record_round_trips_field_for_field(self) -> None:
        from shadow_hdk.kernel import PendingQuestion, ThreadRecord, TurnRecord

        store = self.store()
        record = ThreadRecord(
            id="t1",
            root="/work",
            created_at="2026-01-01T00:00:00+00:00",
            mode="confined",
            provider="scripted 0",
            turns=(
                TurnRecord(
                    id="turn-1",
                    run_id="r1",
                    prompt="p",
                    at="2026-01-01T00:00:01+00:00",
                    outcome="completed",
                    text="a",
                ),
            ),
            forked_from="t0",
            seeded_turns=1,
            session_id="s",
            pending=(
                PendingQuestion(
                    handle="r1:s1:3",
                    turn="turn-1",
                    step="s1",
                    question="may it?",
                    component="write_file",
                    inputs={"path": "a.txt"},
                    run_id="child-1",
                ),
            ),
        )
        await store.create(record)
        assert await store.get("t1") == record

    async def test_save_replaces_and_a_missing_thread_is_none(self) -> None:
        from dataclasses import replace

        from shadow_hdk.kernel import ThreadRecord

        store = self.store()
        record = ThreadRecord(id="t1", root="/w", created_at="2026-01-01T00:00:00+00:00")
        await store.create(record)
        await store.save(replace(record, mode="open"))
        found = await store.get("t1")
        assert found is not None and found.mode == "open"
        assert await store.get("nobody") is None

    async def test_listing_hides_archived_unless_asked(self) -> None:
        from shadow_hdk.kernel import ThreadRecord

        store = self.store()
        await store.create(ThreadRecord(id="a", root="/w", created_at="2026-01-01T00:00:00+00:00"))
        await store.create(ThreadRecord(id="b", root="/w", created_at="2026-01-01T00:00:01+00:00"))
        await store.archive("b")
        assert [t.id for t in await store.list()] == ["a"]
        assert sorted(t.id for t in await store.list(include_archived=True)) == ["a", "b"]

    async def test_one_holder_at_a_time_and_a_holder_keeps_its_own(self) -> None:
        """D81: a hold is exclusive while it lives; the holder may take it again and renew it;
        release frees it for the next; a stranger's release changes nothing."""
        from shadow_hdk.kernel import ThreadRecord

        store = self.store()
        await store.create(ThreadRecord(id="t", root="/w", created_at="2026-01-01T00:00:00+00:00"))
        assert await store.held_by("t") is None
        assert await store.hold("t", "alpha", ttl_seconds=30) is True
        assert await store.hold("t", "beta", ttl_seconds=30) is False
        assert await store.held_by("t") == "alpha"
        assert await store.hold("t", "alpha", ttl_seconds=30) is True, "its own, again"
        assert await store.renew("t", "alpha", ttl_seconds=30) is True
        assert await store.renew("t", "beta", ttl_seconds=30) is False
        await store.release("t", "beta")
        assert await store.held_by("t") == "alpha", "a stranger's release changes nothing"
        await store.release("t", "alpha")
        assert await store.held_by("t") is None
        assert await store.hold("t", "beta", ttl_seconds=30) is True

    async def test_a_hold_lapses_when_nobody_renews_it(self) -> None:
        """The process that held it died: after the ttl the thread is free, the next holder takes
        it, and the dead one's renewal says so."""
        import asyncio

        from shadow_hdk.kernel import ThreadRecord

        store = self.store()
        await store.create(ThreadRecord(id="t", root="/w", created_at="2026-01-01T00:00:00+00:00"))
        assert await store.hold("t", "alpha", ttl_seconds=0.2) is True
        await asyncio.sleep(0.35)
        assert await store.held_by("t") is None, "lapsed"
        assert await store.hold("t", "beta", ttl_seconds=30) is True
        assert await store.renew("t", "alpha", ttl_seconds=30) is False, "lost, and told"
        assert await store.held_by("t") == "beta"


class StoreContract:
    """Override `store` with a fresh, empty store each call (D66)."""

    def store(self) -> Any:
        raise NotImplementedError

    async def test_rows_round_trip_and_versions_move_per_collection(self) -> None:
        store = self.store()
        assert await store.version("a") == 0
        await store.put("a", "k", {"x": [1, 2, {"y": None}]})
        assert await store.get("a", "k") == {"x": [1, 2, {"y": None}]}
        assert await store.version("a") == 1 and await store.version("b") == 0
        await store.put("a", "k", {"x": 2})
        assert await store.get("a", "k") == {"x": 2}, "put replaces"
        assert await store.version("a") == 2

    async def test_list_delete_and_a_missing_row(self) -> None:
        store = self.store()
        await store.put("c", "one", 1)
        await store.put("c", "two", 2)
        assert sorted(await store.list("c")) == [("one", 1), ("two", 2)]
        await store.delete("c", "one")
        assert await store.list("c") == (("two", 2),)
        assert await store.get("c", "one") is None
        before = await store.version("c")
        await store.delete("c", "nobody")
        assert await store.version("c") == before, "deleting nothing changes nothing"


class RunStoreContract:
    """Override `run_store` with a fresh, empty store each call (D93)."""

    def run_store(self) -> Any:
        raise NotImplementedError

    async def test_bytes_round_trip_by_run_and_key_and_list_is_sorted(self) -> None:
        store = self.run_store()
        assert await store.get("r1", "cp/a") is None
        await store.put("r1", "cp/b", b"two")
        await store.put("r1", "cp/a", b"one")
        await store.put("r1", "wr/a/1", b"w")
        await store.put("r2", "cp/a", b"other")
        assert await store.get("r1", "cp/a") == b"one"
        assert await store.list("r1") == (("cp/a", b"one"), ("cp/b", b"two"), ("wr/a/1", b"w"))
        assert await store.list("r1", prefix="cp/") == (("cp/a", b"one"), ("cp/b", b"two"))
        await store.put("r1", "cp/a", b"replaced")
        assert await store.get("r1", "cp/a") == b"replaced", "put replaces"

    async def test_delete_forgets_one_run_and_leaves_the_rest(self) -> None:
        store = self.run_store()
        await store.put("r1", "cp/a", b"one")
        await store.put("r2", "cp/a", b"two")
        await store.delete("r1")
        assert await store.list("r1") == () and await store.get("r1", "cp/a") is None
        assert await store.list("r2") == (("cp/a", b"two"),)
        await store.delete("nobody")  # nothing to forget is not an error


class QuestionsContract:
    """Override `questions` with a fresh implementation of the `Questions` port (D91), and
    `answer(questions, request, answer)` with how a person answers on it — the host's side,
    which the port does not fix."""

    def questions(self) -> Any:
        raise NotImplementedError

    async def answer(self, questions: Any, request: Any, answer: Any) -> None:
        raise NotImplementedError

    async def test_a_question_waits_for_its_answer_and_gets_it(self) -> None:
        import asyncio

        from shadow_hdk.kernel.questions import Request

        questions = self.questions()
        request = Request(handle="h1", run_id="r", step="s", question="may it?")
        asking = asyncio.create_task(questions.ask(request))
        await asyncio.sleep(0)
        assert not asking.done(), "asked, not yet answered: the run waits"
        await self.answer(questions, request, {"kind": "approve"})
        assert await asyncio.wait_for(asking, 5) == {"kind": "approve"}

    async def test_two_questions_are_answered_each_by_its_handle(self) -> None:
        import asyncio

        from shadow_hdk.kernel.questions import Request

        questions = self.questions()
        first = Request(handle="h1", run_id="r", step="s1", question="a?")
        second = Request(handle="h2", run_id="r", step="s2", question="b?")
        one = asyncio.create_task(questions.ask(first))
        two = asyncio.create_task(questions.ask(second))
        await asyncio.sleep(0)
        await self.answer(questions, second, "B")
        await self.answer(questions, first, "A")
        assert await asyncio.wait_for(one, 5) == "A"
        assert await asyncio.wait_for(two, 5) == "B"


def an_observation() -> Observation:
    return Completed({"ok": True})


def an_event() -> Event:
    return Started(run_id="run-1", seq=0, at="2026-01-01T00:00:00+00:00", lease=A_LEASE)


__all__ = [
    "A_CONTEXT",
    "A_LEASE",
    "A_PROVENANCE",
    "ClockPortContract",
    "AuthorityPortContract",
    "AuthorizerPortContract",
    "ComponentPortContract",
    "GovernancePortContract",
    "EffectJournalContract",
    "ModelPortContract",
    "ObserverPortContract",
    "QuestionsContract",
    "RunStoreContract",
    "SinkPortContract",
    "StoreContract",
    "ThreadStoreContract",
    "an_event",
    "an_observation",
]
