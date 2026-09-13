"""The agent as a component: what the model sees, what it may do, and what it costs.

Every test drives a scripted model, so what is asserted is the *adapter's* behaviour and never a
model's mood — which is also what makes these cost nothing to run.
"""

from __future__ import annotations

from pydantic import JsonValue

from shadow_hdk.adapters.agent import AgentComponent, Pattern, single
from shadow_hdk.adapters.agent.pattern import COMPOSE, DONE, PROPOSE
from shadow_hdk.adapters.basic import AllowAll, CallableComponents
from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Completed,
    Composed,
    Composition,
    EffectProfile,
    Event,
    FanOut,
    Floor,
    Invoke,
    Lease,
    Observation,
    Observed,
    ScopeSet,
    Sequence,
    Step,
)
from shadow_hdk.kernel.ports import ModelResponse, ToolCall, Usage
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListObserver, ListSink, ScriptedModel

READS = EffectProfile(reads=ScopeSet.of("workspace"))
AGENT_EFFECTS = EffectProfile(reads=ScopeSet.of("workspace"), costs=True)


def search(query: str) -> dict[str, JsonValue]:
    """Look something up."""
    return {"found": query}


def weigh(what: str) -> dict[str, JsonValue]:
    """Weigh something."""
    return {"kg": 12}


def build_ports(
    responses: list[ModelResponse],
    *,
    pattern: Pattern = single,
    sink: ListSink | None = None,
    observer: ListObserver | None = None,
) -> tuple[Ports, AgentComponent, ScriptedModel, ListSink]:
    tools = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    tools.add(search, effects=READS)
    tools.add(weigh, effects=READS)
    agent = AgentComponent(pattern=pattern, effects=AGENT_EFFECTS, at="2026-01-01T00:00:00+00:00")
    model = ScriptedModel(responses)
    the_sink = sink or ListSink()
    return (
        Ports(
            model=model,
            components=(tools, agent),
            governance=AllowAll(),
            sink=the_sink,
            clock=FixedClock(),
            observer=observer,
        ),
        agent,
        model,
        the_sink,
    )


async def drive_agent(
    responses: list[ModelResponse],
    *,
    pattern: Pattern = single,
    lease: Lease | None = None,
    sink: ListSink | None = None,
) -> tuple[list[Event], ScriptedModel, ListSink]:
    ports, agent, model, the_sink = build_ports(responses, pattern=pattern, sink=sink)
    composition = Composition(
        (
            Invoke(
                "a1",
                "agent",
                (
                    __import__("shadow_hdk.kernel", fromlist=["Binding"]).Binding(
                        name="brief", value="find the mass of the lathe"
                    ),
                ),
            ),
        )
    )
    events = [
        e
        async for e in run(
            composition,
            ports,
            options=RunOptions(lease=lease or Lease(Ceiling(40, 3600, 1000), Floor(0))),
        )
    ]
    return events, model, the_sink


def call(name: str, cid: str, **arguments: JsonValue) -> ToolCall:
    return ToolCall(id=cid, name=name, arguments=dict(arguments))


def says(*calls: ToolCall, text: str = "", usage: Usage | None = None) -> ModelResponse:
    return ModelResponse(text=text, tool_calls=calls, usage=usage)


# ---------------------------------------------------------------- reading the stream


def compositions(events: list[Event]) -> list[Composition]:
    return [e.composition for e in events if isinstance(e, Composed)]


def observations(events: list[Event], step: str | None = None) -> list[Observation]:
    return [
        e.observation
        for e in events
        if isinstance(e, Observed) and (step is None or e.step == step)
    ]


def outcome(events: list[Event], step: str = "a1") -> dict[str, JsonValue]:
    """What the agent component itself returned, as an object."""
    last = observations(events, step)[-1]
    assert isinstance(last, Completed), f"the agent ended as {last.kind}: {last!r}"
    assert isinstance(last.output, dict)
    return last.output


def invoked(step: Step) -> Invoke:
    assert isinstance(step, Invoke), f"expected an invoke, got {step.kind}"
    return step


def branches(step: Step) -> tuple[Step, ...]:
    assert isinstance(step, FanOut | Sequence), f"expected a composite, got {step.kind}"
    return step.steps


# ---------------------------------------------------------------- what the model may see


async def test_single_offers_propose_and_done_and_nothing_else() -> None:
    """D3: the pattern decides the model's verbs. `single` cannot compose, so it cannot change
    its own shape — which is the whole mechanism behind a deterministic one-agent product."""
    _events, model, _ = await drive_agent([says(call(DONE, "d1", summary="nothing to do"))])
    offered = {tool.name for tool in model.requests[0].tools}
    assert PROPOSE in offered and DONE in offered
    assert COMPOSE not in offered


async def test_a_pattern_that_composes_is_shown_compose() -> None:
    composer = Pattern("composer", "…", meta_tools=frozenset({COMPOSE, PROPOSE, DONE}))
    _events, model, _ = await drive_agent(
        [says(call(DONE, "d1", summary="done"))], pattern=composer
    )
    assert COMPOSE in {tool.name for tool in model.requests[0].tools}


async def test_the_agent_is_not_offered_itself() -> None:
    _events, model, _ = await drive_agent([says(call(DONE, "d1", summary="done"))])
    assert "agent" not in {tool.name for tool in model.requests[0].tools}
    assert {"search", "weigh"} <= {tool.name for tool in model.requests[0].tools}


async def test_a_pattern_may_narrow_which_tools_this_role_sees() -> None:
    narrow = Pattern("narrow", "…", tool_names=frozenset({"search"}))
    _events, model, _ = await drive_agent([says(call(DONE, "d1", summary="done"))], pattern=narrow)
    assert {tool.name for tool in model.requests[0].tools} == {"search", PROPOSE, DONE}


# ---------------------------------------------------------------- one call, several, a plan


async def test_one_tool_call_becomes_a_plan_of_one_step() -> None:
    events, _, _ = await drive_agent(
        [says(call("search", "t1", query="lathe")), says(call(DONE, "d1", summary="found it"))]
    )
    child_plan = compositions(events)[-1]
    assert len(child_plan.steps) == 1
    assert invoked(child_plan.steps[0]).component == "search"


async def test_several_tool_calls_at_once_become_a_fan_out() -> None:
    events, _, _ = await drive_agent(
        [
            says(call("search", "t1", query="lathe"), call("weigh", "t2", what="lathe")),
            says(call(DONE, "d1", summary="done")),
        ]
    )
    child_plan = compositions(events)[-1]
    assert child_plan.steps[0].kind == "fan_out"
    assert {invoked(s).component for s in branches(child_plan.steps[0])} == {"search", "weigh"}


async def test_what_a_tool_returned_comes_back_to_the_model() -> None:
    _events, model, _ = await drive_agent(
        [says(call("search", "t1", query="lathe")), says(call(DONE, "d1", summary="done"))]
    )
    tool_messages = [m for m in model.requests[-1].messages if m.role == "tool"]
    assert tool_messages and "lathe" in tool_messages[-1].content
    assert tool_messages[-1].tool_call_id == "t1"


async def test_a_plan_the_model_authored_runs_verbatim() -> None:
    composer = Pattern("composer", "…", meta_tools=frozenset({COMPOSE, PROPOSE, DONE}))
    plan: JsonValue = {
        "steps": [
            {
                "kind": "sequence",
                "id": "seq",
                "steps": [
                    {
                        "kind": "invoke",
                        "id": "x",
                        "component": "search",
                        "inputs": [{"name": "query", "value": "lathe"}],
                    },
                    {
                        "kind": "invoke",
                        "id": "y",
                        "component": "weigh",
                        "inputs": [{"name": "what", "value": "lathe"}],
                    },
                ],
            }
        ]
    }
    events, _, _ = await drive_agent(
        [
            says(ToolCall(id="c1", name=COMPOSE, arguments=plan)),
            says(call(DONE, "d1", summary="done")),
        ],
        pattern=composer,
    )
    child_plan = compositions(events)[-1]
    assert child_plan.steps[0].kind == "sequence"
    assert [s.id for s in branches(child_plan.steps[0])] == ["x", "y"]


async def test_a_plan_that_does_not_parse_is_told_to_the_model_not_raised() -> None:
    composer = Pattern("composer", "…", meta_tools=frozenset({COMPOSE, PROPOSE, DONE}))
    _events, model, _ = await drive_agent(
        [
            says(ToolCall(id="c1", name=COMPOSE, arguments={"steps": [{"kind": "nonsense"}]})),
            says(call(DONE, "d1", summary="gave up on that")),
        ],
        pattern=composer,
    )
    tool_messages = [m for m in model.requests[-1].messages if m.role == "tool"]
    assert any("does not parse" in m.content for m in tool_messages)


# ---------------------------------------------------------------- propose, done, the floor


async def test_propose_reaches_the_sink_and_the_stream() -> None:
    events, _, sink = await drive_agent(
        [
            says(call(PROPOSE, "p1", kind="claim", payload={"mass_kg": 12})),
            says(call(DONE, "d1", summary="done")),
        ]
    )
    assert [p.kind for p in sink.proposals] == ["claim"]
    assert sink.proposals[0].payload == {"mass_kg": 12}
    assert [e.kind for e in events].count("proposed") == 1


async def test_done_finishes_and_says_why() -> None:
    events, _, _ = await drive_agent([says(call(DONE, "d1", summary="the lathe is 12 kg"))])
    assert outcome(events)["reason"] == "done"
    assert outcome(events)["text"] == "the lathe is 12 kg"


async def test_no_tool_calls_at_all_is_an_answer() -> None:
    events, _, _ = await drive_agent([says(text="it is 12 kg")])
    assert outcome(events)["reason"] == "answered"
    assert outcome(events)["text"] == "it is 12 kg"


async def test_done_before_the_floor_is_nudged_exactly_once_then_accepted() -> None:
    """A model trained to be agreeable gives up early; the floor is the honest counter, and one
    nudge is the whole of it — a second would be nagging, and the run would never end."""
    events, model, _ = await drive_agent(
        [
            says(call(DONE, "d1", summary="cannot do it")),
            says(call(DONE, "d2", summary="really cannot do it")),
        ],
        lease=Lease(Ceiling(40, 3600, 1000), Floor(min_steps=5)),
    )
    nudges = [
        m
        for m in model.requests[-1].messages
        if m.role == "tool" and "not done enough" in m.content
    ]
    assert len(nudges) == 1
    assert outcome(events)["reason"] == "gave_up"


async def test_the_floor_being_met_means_done_is_taken_at_its_word() -> None:
    events, model, _ = await drive_agent(
        [says(call("search", "t1", query="a")), says(call(DONE, "d1", summary="found"))],
        lease=Lease(Ceiling(40, 3600, 1000), Floor(min_steps=1)),
    )
    assert not [
        m
        for m in model.requests[-1].messages
        if m.role == "tool" and "not done enough" in m.content
    ]
    assert outcome(events)["reason"] == "done"


# ---------------------------------------------------------------- leases and cost


async def test_the_model_s_cost_reaches_the_run_s_meter() -> None:
    events, _, _ = await drive_agent(
        [says(call(DONE, "d1", summary="done"), usage=Usage(100, 20, 7))]
    )
    usage = outcome(events)["usage"]
    assert isinstance(usage, dict) and usage["cost_cents"] == 7


async def test_cost_accumulates_across_turns() -> None:
    events, _, _ = await drive_agent(
        [
            says(call("search", "t1", query="a"), usage=Usage(10, 5, 3)),
            says(call(DONE, "d1", summary="done"), usage=Usage(10, 5, 4)),
        ]
    )
    usage = outcome(events)["usage"]
    assert isinstance(usage, dict) and usage["cost_cents"] == 7


async def test_a_turn_loop_that_runs_out_of_lease_ends_cleanly() -> None:
    """Not an exception, not a hang: the agent notices there is nothing left and says so."""
    events, _, _ = await drive_agent(
        [says(call("search", f"t{i}", query="a")) for i in range(10)]
        + [says(call(DONE, "d9", summary="done"))],
        lease=Lease(Ceiling(6, 3600, 1000), Floor(0)),
    )
    assert events[-1].kind == "ended"
    assert observations(events, "a1")[-1].kind == "completed"


async def test_max_turns_stops_a_model_that_never_finishes() -> None:
    patient = Pattern("patient", "…", max_turns=3)
    events, model, _ = await drive_agent(
        [says(call("search", f"t{i}", query="a")) for i in range(6)], pattern=patient
    )
    assert outcome(events)["reason"] == "out_of_turns"
    assert outcome(events)["turns"] == 3


async def test_a_sub_agent_gets_what_is_left_rather_than_a_guess() -> None:
    """A turn's plan was carved `len(steps) + 1`, which is right for tool calls and wrong the moment
    a step is itself an agent: a sub-agent needs steps for its own turns, and got two. It died
    `lease_exhausted` after one turn, and — worse — silently, because a lease ending a run is not an
    error. Turns are sequential and each settles before the next, so the honest ceiling is whatever
    the parent has left; the parent's own ceiling still bounds the lot.
    """
    tools = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    tools.add(search, effects=READS)
    junior = AgentComponent(
        pattern=Pattern("junior", "…", tool_names=frozenset({"search"})),
        effects=AGENT_EFFECTS,
        name="junior",
        at="2026-01-01T00:00:00+00:00",
    )
    senior = AgentComponent(
        pattern=Pattern("senior", "…", tool_names=frozenset({"junior"})),
        effects=AGENT_EFFECTS,
        name="senior",
        at="2026-01-01T00:00:00+00:00",
    )
    model = ScriptedModel(
        [
            says(call("junior", "s1", brief="look it up twice")),  # senior turn 1
            says(call("search", "j1", query="a")),  # junior turn 1
            says(call("search", "j2", query="b")),  # junior turn 2
            says(call(DONE, "j3", summary="both found")),  # junior turn 3
            says(call(DONE, "s2", summary="delegated")),  # senior turn 2
        ]
    )
    ports = Ports(
        model=model,
        components=(tools, junior, senior),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    events = [
        e
        async for e in run(
            Composition((Invoke("top", "senior", (Binding(name="brief", value="go"),)),)),
            ports,
            options=RunOptions(lease=Lease(Ceiling(40, 3600, 1000), Floor(0))),
        )
    ]
    junior_result = observations(events, "s1")[-1]
    assert isinstance(junior_result, Completed)
    assert isinstance(junior_result.output, dict)
    assert junior_result.output["reason"] == "done", junior_result.output
    assert junior_result.output["turns"] == 3
