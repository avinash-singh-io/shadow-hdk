"""Money already spent is on the record even when the turn after it fails (BUG-012, D33).

`work()` called `ports.model.complete` unwrapped, so a provider that hung up on the third turn threw
straight out of the component. `step.py` turns a component raising into `Failed` (D7) — and a
`Failed` observation carries no usage, so the two paid turns before it were charged to nobody.

That is D33's rule from the other side. *What a run has spent survives a park* was about the
checkpoint; this is the same claim about a failure: spend that happened is spend that is recorded,
or a lease is not a bound and a bill is not a bill.

The outcome deliberately reads like every other way this loop stops early. `lease_exhausted` and
`out_of_turns` are already `Completed` carrying a `reason`, because the agent's job is to run a loop
and report what happened — and a report that costs the deployment its accounting to deliver is not
the better answer.
"""

from __future__ import annotations

from typing import Any

from shadow_hdk.adapters.agent import AgentComponent, Pattern
from shadow_hdk.adapters.basic import AllowAll, CallableComponents

from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Completed,
    Composition,
    Event,
    Floor,
    Invoke,
    Lease,
    Observed,
    ScopeSet,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import Spent
from shadow_hdk.kernel.ports import ModelRequest, ModelResponse, ToolCall, Usage
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListSink

WORKSPACE = ScopeSet.of("workspace")
A_TURN = Usage(input_tokens=1000, output_tokens=100, cost_cents=7)


def look(topic: str) -> str:
    """Look a topic up."""
    return f"found {topic}"


class HangsUpOn:
    """Real turns that cost real money, and then a provider that falls over."""

    def __init__(self, turn: int, broken: BaseException) -> None:
        self.turn, self.broken, self.turns = turn, broken, 0

    async def complete(self, _request: ModelRequest) -> ModelResponse:
        self.turns += 1
        if self.turns >= self.turn:
            raise self.broken
        return ModelResponse(
            "working", (ToolCall(f"t{self.turns}", "look", {"topic": "x"}),), usage=A_TURN
        )

    async def stream(self, _request: ModelRequest) -> Any:  # pragma: no cover — never streamed here
        raise NotImplementedError


async def drive(model: HangsUpOn) -> list[Event]:
    tools = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    tools.add(look, effects=EffectProfile(reads=WORKSPACE))
    agent = AgentComponent(
        pattern=Pattern(name="p", system="work"),
        effects=EffectProfile(costs=True),
        at="2026-01-01T00:00:00+00:00",
    )
    ports = Ports(
        model=model,  # type: ignore[arg-type]
        components=(tools, agent),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    return [
        event
        async for event in run(
            Composition(
                (Invoke("a1", agent.registration_id, (Binding(name="brief", value="go"),)),)
            ),
            ports,
            options=RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0))),
        )
    ]


def outcome(events: list[Event]) -> dict[str, Any]:
    """The agent's own output, which every way this loop ends is a `Completed` dict."""
    observation = [e for e in events if isinstance(e, Observed)][-1].observation
    assert isinstance(observation, Completed)
    assert isinstance(observation.output, dict)
    return observation.output


def spent(events: list[Event]) -> tuple[int, int]:
    charged = [e for e in events if isinstance(e, Spent)]
    return (
        sum(e.usage.input_tokens or 0 for e in charged),
        sum(e.usage.cost_cents or 0 for e in charged),
    )


async def test_the_turns_before_the_break_are_charged() -> None:
    """The bug, measured: two paid turns and a run that recorded nothing at all."""
    events = await drive(HangsUpOn(3, ConnectionError("the provider hung up")))

    assert spent(events) == (2000, 14), "two turns of real money went unrecorded"


async def test_a_break_on_the_very_first_turn_charges_nothing() -> None:
    """The other end, and the one that says the fix is a *record* rather than a guess: a provider
    that broke before it answered anything cost nothing, and nothing is what is charged.

    It is reported as a **known** zero rather than left unsaid. An agent component always makes
    model calls, so *this one made none and spent nothing* is a fact it can state — unlike a
    component that never had a model to call, which reports no usage at all (D20).
    """
    events = await drive(HangsUpOn(1, ConnectionError("the provider hung up")))

    assert spent(events) == (0, 0)
    assert [e.usage.cost_cents for e in events if isinstance(e, Spent)] == [0]


async def test_the_run_says_the_provider_broke_and_says_what_broke() -> None:
    """A reason a person can act on. *Failed* with no words sends whoever reads it to the logs, and
    an outage and a bad request want different responses."""
    events = await drive(HangsUpOn(3, ConnectionError("the provider hung up")))
    said = outcome(events)

    assert said["reason"] == "provider_failed"
    assert "ConnectionError" in str(said["text"])
    assert "hung up" in str(said["text"])


async def test_it_does_not_read_as_an_answer() -> None:
    """The risk of reporting this as `Completed`: a caller that reads only the kind would file a
    provider outage as a finished piece of work. The reason is the difference, and `answered` is
    the word this loop uses when it really has an answer."""
    events = await drive(HangsUpOn(2, ConnectionError("the provider hung up")))

    assert outcome(events)["reason"] != "answered"


async def test_the_turns_it_managed_are_counted() -> None:
    """`turns` is model calls made, whichever way it ended — so a run that broke on the third is
    distinguishable from one that broke on the first, without reading the text."""
    events = await drive(HangsUpOn(3, ConnectionError("the provider hung up")))

    assert outcome(events)["turns"] == 2


async def test_a_cancellation_is_not_reported_as_a_provider_failure() -> None:
    """A host stopping a run (D15) travels as `CancelledError`, which is a `BaseException` for
    exactly this reason — so the catch is on `Exception` and lets it past.

    A loop that caught it and reported `provider_failed` would turn *stop* into *carry on with the
    next step*, and the stop would be the only thing that did not happen. What the runtime then
    does with it is its own business and is asserted elsewhere; what matters here is that this
    component does not claim a provider broke when a person pressed stop.
    """
    import asyncio

    events = await drive(HangsUpOn(2, asyncio.CancelledError()))
    reasons = [
        e.observation.output.get("reason")
        for e in events
        if isinstance(e, Observed)
        and isinstance(e.observation, Completed)
        and isinstance(e.observation.output, dict)
    ]

    assert "provider_failed" not in reasons
    assert [e.kind for e in events][-1] == "ended"
