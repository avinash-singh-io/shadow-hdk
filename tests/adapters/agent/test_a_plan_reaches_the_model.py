"""What happened to an authored plan comes back to the model (BUG-012).

`compose` is the meta-tool that lets a model lay out several steps at once, and its own interface
promises *the plan runs and you see every result*. It did not. `carry_out` answered tool calls by
matching `call.id` against the step ids in the event stream — which works for one-call-per-step and
cannot work for a plan, whose step ids are the model's own (`s1`, `s2`) and belong to no call.

Worse than the results being missing: `compose` is a meta-tool, so the loop skipped it entirely and
the call was left **unanswered**. That is the dangling tool call every provider rejects outright —
the same rule BUG-005 was about — and four of the six shipped patterns are built on `compose`.
"""

from __future__ import annotations

from pydantic import JsonValue
from shadow_hdk.adapters.agent import AgentComponent, Pattern
from shadow_hdk.adapters.agent.component import _readable_plan
from shadow_hdk.adapters.agent.pattern import COMPOSE, DONE, PROPOSE
from shadow_hdk.adapters.basic import AllowAll, CallableComponents

from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Composition,
    Floor,
    Invoke,
    Lease,
    ScopeSet,
)
from shadow_hdk.kernel.contracts import load
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.observations import Completed
from shadow_hdk.kernel.ports import Context, Judgement, ModelResponse, Refuse, ToolCall
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

WORKSPACE = ScopeSet.of("workspace")


def look(topic: str) -> str:
    """Look a topic up."""
    return f"found {topic}"


def wipe(what: str) -> str:
    """Delete something."""
    return f"wiped {what}"


class NoWrites:
    async def judge(self, effects: EffectProfile, _context: Context) -> Judgement:
        from shadow_hdk.kernel.ports import Allow

        if effects.writes.names or effects.writes.everything:
            return Refuse("writing is not permitted in this deployment")
        return Allow()


def a_plan(*steps: dict[str, JsonValue]) -> dict[str, JsonValue]:
    return {"steps": list(steps)}


def _as_json_str(value: dict[str, JsonValue]) -> str:
    import json

    return json.dumps(value)


def looking(step_id: str, topic: str) -> dict[str, JsonValue]:
    return {
        "kind": "invoke",
        "id": step_id,
        "component": "look",
        "inputs": [{"name": "topic", "value": topic}],
    }


async def drive(plan: dict[str, JsonValue], *, governance: object | None = None) -> ScriptedModel:
    tools = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    tools.add(look, effects=EffectProfile(reads=WORKSPACE))
    tools.add(wipe, effects=EffectProfile(writes=WORKSPACE, reversible=False))
    agent = AgentComponent(
        pattern=Pattern(name="p", system="plan it", meta_tools=frozenset({COMPOSE, PROPOSE, DONE})),
        effects=EffectProfile(costs=True),
        at="2026-01-01T00:00:00+00:00",
    )
    model = ScriptedModel(
        [
            ModelResponse("planning", (ToolCall("c1", "compose", plan),)),
            ModelResponse("ok", (ToolCall("d1", "done", {"summary": "finished"}),)),
        ]
    )
    ports = Ports(
        model=model,
        components=(tools, agent),
        governance=governance or AllowAll(),  # type: ignore[arg-type]
        sink=ListSink(),
        clock=FixedClock(),
    )
    async for _ in run(
        Composition((Invoke("a1", agent.registration_id, (Binding(name="brief", value="go"),)),)),
        ports,
        options=RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0))),
    ):
        pass
    return model


def answers(model: ScriptedModel, turn: int = 1) -> dict[str | None, str]:
    return {m.tool_call_id: m.content for m in model.requests[turn].messages if m.role == "tool"}


def calls_made(model: ScriptedModel, turn: int = 1) -> list[str]:
    return [
        call.id
        for message in model.requests[turn].messages
        if message.role == "assistant" and message.tool_calls
        for call in message.tool_calls
    ]


async def test_the_compose_call_is_answered_at_all() -> None:
    """The pairing rule, which the refusal tests already hold for ordinary calls. A transcript with
    a tool call and no result beside it is rejected by Anthropic, OpenAI and Google alike — so this
    was not a degraded second turn, it was a request no provider would have accepted."""
    model = await drive(a_plan(looking("s1", "one"), looking("s2", "two")))

    assert calls_made(model) == ["c1"]
    assert set(answers(model)) == {"c1"}, "the plan's own call was left unanswered"


async def test_every_step_of_the_plan_comes_back() -> None:
    """The interface's promise, in its own words: *the plan runs and you see every result*."""
    model = await drive(a_plan(looking("s1", "one"), looking("s2", "two")))
    answer = answers(model)["c1"]

    assert "s1" in answer and "found one" in answer
    assert "s2" in answer and "found two" in answer


async def test_a_refused_step_of_a_plan_says_why() -> None:
    """A plan is not all-or-nothing, and a model told only that *the plan ran* cannot tell which
    step it must do differently. The refusal reaches it with the step's name and the reason."""
    model = await drive(
        a_plan(
            looking("s1", "one"),
            {
                "kind": "invoke",
                "id": "s2",
                "component": "wipe",
                "inputs": [{"name": "what", "value": "the lathe"}],
            },
        ),
        governance=NoWrites(),
    )
    answer = answers(model)["c1"]

    assert "found one" in answer
    assert "s2" in answer and "writing is not permitted" in answer
    assert "refused" in answer


async def test_a_plan_of_one_step_still_names_it() -> None:
    """A one-step plan is the case most likely to be answered by accident — with a bare result that
    happens to read correctly — so it is asserted to carry the step's name like any other."""
    model = await drive(a_plan(looking("only", "one")))
    answer = answers(model)["c1"]

    assert "only" in answer and "found one" in answer


async def test_ordinary_tool_calls_are_still_answered_one_by_one() -> None:
    """The path that already worked, held while the other is added: a model calling tools directly
    gets one result per call, keyed to that call, and not a summary of all of them."""
    tools = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    tools.add(look, effects=EffectProfile(reads=WORKSPACE))
    agent = AgentComponent(
        pattern=Pattern(name="p", system="work", meta_tools=frozenset({PROPOSE, DONE})),
        effects=EffectProfile(costs=True),
        at="2026-01-01T00:00:00+00:00",
    )
    model = ScriptedModel(
        [
            ModelResponse(
                "looking",
                (
                    ToolCall("t1", "look", {"topic": "one"}),
                    ToolCall("t2", "look", {"topic": "two"}),
                ),
            ),
            ModelResponse("ok", (ToolCall("d1", "done", {"summary": "finished"}),)),
        ]
    )
    ports = Ports(
        model=model,
        components=(tools, agent),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    async for _ in run(
        Composition((Invoke("a1", agent.registration_id, (Binding(name="brief", value="go"),)),)),
        ports,
        options=RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0))),
    ):
        pass

    assert answers(model) == {"t1": '"found one"', "t2": '"found two"'}


def test_a_step_the_plan_never_reached_is_reported_as_such() -> None:
    """Found by a mutation that survived: leaving unobserved steps out of the answer passed every
    test, because no plan in the suite had a step that did not run.

    **Asserted at the helper rather than through a run, and the reason is worth recording.** The
    one arrangement that leaves a plan's step unobserved is a lease ending in the middle of it —
    and `carry_out` hands the plan whatever the parent has left, so a lease that stops the plan has
    stopped the agent too, and there is no second turn for the answer to arrive on. The branch is
    what a longer-leased or resumed run would deliver, and *this did not run* is exactly what a
    model needs in order to pick a plan up where it stopped. Silence reads as a step that ran and
    returned nothing.
    """
    plan = load(_as_json_str(a_plan(looking("s1", "one"), looking("s2", "two"))), Composition)

    answer = _readable_plan(plan, {"s1": Completed("found one")})

    assert "s1" in answer and "found one" in answer
    assert "s2" in answer, "a step the plan never reached was left out of the answer"
    assert "did not run" in answer
