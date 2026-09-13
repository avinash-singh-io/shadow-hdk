"""The small real adapters, against their ports' contracts and their own behaviour."""

from __future__ import annotations

import io

import pytest
from pydantic import JsonValue

from shadow_hdk.adapters.basic import (
    AllowAll,
    CallableComponents,
    CallbackObserver,
    CallbackSink,
    StdoutObserver,
    StdoutSink,
    SystemClock,
)
from shadow_hdk.kernel import (
    ASSUME_WORST,
    Completed,
    EffectProfile,
    Failed,
    Proposal,
    Refused,
    ScopeSet,
)
from shadow_hdk.kernel.ports import ClockPort, ComponentPort, GovernancePort
from shadow_hdk.testing.contracts import (
    A_CONTEXT,
    A_PROVENANCE,
    ClockPortContract,
    ComponentPortContract,
    GovernancePortContract,
    ObserverPortContract,
    SinkPortContract,
    an_event,
)

WRITES_RECORD = EffectProfile(writes=ScopeSet.of("record"), reversible=True)


def note_fact(subject: str, text: str, confidence: float = 1.0) -> dict[str, JsonValue]:
    """Note something about a subject."""
    return {"subject": subject, "text": text, "confidence": confidence}


async def read_facts(subject: str) -> list[str]:
    """Everything settled about a subject."""
    return [f"a fact about {subject}"]


def always_breaks() -> None:
    raise RuntimeError("the vendor is down")


def refuses_itself(why: str) -> Refused:
    return Refused(why)


def _components() -> CallableComponents:
    components = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    components.add(note_fact, effects=WRITES_RECORD)
    components.add(read_facts, effects=EffectProfile(reads=ScopeSet.of("workspace")))
    components.add(always_breaks, effects=WRITES_RECORD)
    components.add(refuses_itself, effects=WRITES_RECORD)
    return components


# ---------------------------------------------------------------- the contracts


class TestAllowAllIsAGovernancePort(GovernancePortContract):
    def port(self) -> GovernancePort:
        return AllowAll()


class TestSystemClockIsAClockPort(ClockPortContract):
    def port(self) -> ClockPort:
        return SystemClock()


class TestStdoutSinkIsASinkPort(SinkPortContract):
    def port(self) -> StdoutSink:
        return StdoutSink(io.StringIO())


class TestStdoutObserverIsAnObserverPort(ObserverPortContract):
    def port(self) -> StdoutObserver:
        return StdoutObserver(io.StringIO())


class TestCallableComponentsIsAComponentPort(ComponentPortContract):
    def port(self) -> ComponentPort:
        return _components()

    def valid_call(self) -> tuple[str, JsonValue]:
        return "note_fact", {"subject": "Line 3", "text": "3 of 1842"}


# ---------------------------------------------------------------- their own behaviour


async def test_allow_all_permits_even_the_worst_profile() -> None:
    """Including the profile of a component that declined to declare one — which is the point:
    allow-all is a starting point and a demo, and never a policy."""
    assert (await AllowAll().judge(ASSUME_WORST, A_CONTEXT)).kind == "allow"


def _json_object(value: JsonValue) -> dict[str, JsonValue]:
    assert isinstance(value, dict), f"expected a JSON object, got {type(value).__name__}"
    return value


async def test_the_schema_comes_from_the_signature() -> None:
    registrations = {r.component.interface.name: r for r in await _components().registrations()}
    interface = registrations["note_fact"].component.interface
    properties = _json_object(interface.input_schema["properties"])
    assert set(properties) == {"subject", "text", "confidence"}
    assert interface.input_schema["required"] == ["subject", "text"]
    assert _json_object(properties["confidence"])["type"] == "number"
    assert (
        registrations["note_fact"].component.interface.description
        == "Note something about a subject."
    )


async def test_a_call_that_does_not_fit_the_schema_is_data_not_a_type_error() -> None:
    observation = await _components().invoke("note_fact", {"subject": "Line 3"})
    assert isinstance(observation, Failed)
    assert "text" in observation.error


async def test_a_callable_that_raises_becomes_a_failed_observation() -> None:
    observation = await _components().invoke("always_breaks", {})
    assert isinstance(observation, Failed)
    assert "RuntimeError: the vendor is down" in observation.error


async def test_an_async_callable_works_the_same_as_a_sync_one() -> None:
    observation = await _components().invoke("read_facts", {"subject": "Line 3"})
    assert observation == Completed(["a fact about Line 3"])


async def test_a_callable_may_return_its_own_observation() -> None:
    observation = await _components().invoke("refuses_itself", {"why": "not in this mode"})
    assert observation == Refused("not in this mode")


async def test_a_removed_callable_is_neither_listed_nor_invocable() -> None:
    """The mirror of `add`: what a closed battery (BUG-037's neighbour) uses to be gone, so a port
    a host still holds after `close` offers nothing — the same as a stopped MCP server's."""
    components = _components()
    components.remove("note_fact")

    assert "note_fact" not in {r.id for r in await components.registrations()}
    assert (await components.invoke("note_fact", {"text": "x"})).kind == "failed"
    with pytest.raises(KeyError):
        components.remove("note_fact")


async def test_effects_are_carried_verbatim_and_never_guessed() -> None:
    registrations = {r.component.interface.name: r for r in await _components().registrations()}
    assert registrations["note_fact"].component.effects == WRITES_RECORD
    assert registrations["read_facts"].component.effects.writes == ScopeSet()


async def test_the_stdout_sink_writes_one_json_line_per_proposal() -> None:
    stream = io.StringIO()
    sink = StdoutSink(stream)
    await sink.propose(Proposal(kind="claim", payload={"a": 1}, provenance=A_PROVENANCE))
    await sink.propose(Proposal(kind="claim", payload={"b": 2}, provenance=A_PROVENANCE))
    lines = stream.getvalue().strip().split("\n")
    assert len(lines) == 2
    import json

    assert json.loads(lines[0])["payload"] == {"a": 1}


async def test_the_callback_sink_and_observer_pass_things_straight_through() -> None:
    seen: list[object] = []
    await CallbackSink(seen.append).propose(
        Proposal(kind="claim", payload=None, provenance=A_PROVENANCE)
    )
    await CallbackObserver(seen.append).on(an_event())
    assert [type(x).__name__ for x in seen] == ["Proposal", "Started"]


async def test_a_callback_may_be_async() -> None:
    seen: list[object] = []

    async def note(thing: object) -> None:
        seen.append(thing)

    await CallbackObserver(note).on(an_event())
    assert len(seen) == 1


def test_the_system_clock_reports_a_timezone() -> None:
    from datetime import datetime

    assert datetime.fromisoformat(SystemClock().now()).tzinfo is not None
