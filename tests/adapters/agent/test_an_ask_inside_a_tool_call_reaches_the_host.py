"""An Ask for a tool call inside an agent reaches the host, and the answer reaches the tool
(BUG-020, D57).

Before: the policy asked about `write_file`, the child parked, `carry_out` saw no `observed` for
the call, and the model was told *that step did not run* — then went on to say it had written the
file. The run ended `completed`; the host was never in the loop.

Now: a held child that asked becomes the agent's own question. The agent keeps its transcript,
answers `Asked`, and the run parks at the top. The host answers; the agent is invoked again,
restores its transcript, sends the judgement into the held child, and continues its turn with the
child's result — the tool ran, or was refused, and the model is told which. Nested agents get it
for free: each level uses the same mechanism.
"""

from __future__ import annotations

from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from shadow_hdk.adapters.agent import AgentComponent, Pattern
from shadow_hdk.adapters.basic import CallableComponents
from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Composition,
    Ended,
    Event,
    Floor,
    Invoke,
    Lease,
    ScopeSet,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import ApprovalRequested
from shadow_hdk.kernel.ports import (
    Allow,
    Ask,
    Context,
    Judgement,
    ModelResponse,
    Refuse,
    ToolCall,
)
from shadow_hdk.runtime import Ports, RunOptions, resume, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

pytestmark = pytest.mark.anyio

AT = "2026-01-01T00:00:00+00:00"
WORKSPACE = ScopeSet.of("workspace")
EVERYTHING = ScopeSet(everything=True)

written: list[str] = []


def write_file(path: str, content: str) -> dict[str, Any]:
    """Write a file — anywhere, which is why the policy asks."""
    written.append(path)
    return {"path": path, "bytes": len(content)}


def look(topic: str) -> str:
    """Look something up."""
    return f"found {topic}"


class AsksAboutWrites:
    """Reads are fine; a write outside the workspace is the host's to decide."""

    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        if not (effects.writes <= WORKSPACE):
            return Ask(f"{context.step} wants to write outside the workspace; allow?")
        return Allow()


def _ports(script: list[ModelResponse], *, agents: tuple[AgentComponent, ...]) -> Ports:
    tools = CallableComponents(registered_by="tests", at=AT)
    tools.add(look, effects=EffectProfile(reads=WORKSPACE))
    tools.add(write_file, effects=EffectProfile(writes=EVERYTHING, reversible=False))
    return Ports(
        model=ScriptedModel(script),
        components=(tools, *agents),
        governance=AsksAboutWrites(),
        sink=ListSink(),
        clock=FixedClock(),
    )


def worker(name: str = "worker") -> AgentComponent:
    return AgentComponent(
        pattern=Pattern(name=name, system="do the work"),
        effects=EffectProfile(writes=WORKSPACE, costs=True),
        name=name,
        at=AT,
    )


def says(*calls: ToolCall, text: str = "") -> ModelResponse:
    return ModelResponse(text, calls)


WRITES_THEN_DONE = [
    says(ToolCall("w1", "write_file", {"path": "/elsewhere/notes.md", "content": "hi"})),
    says(ToolCall("d1", "done", {"summary": "wrote the notes"})),
]
PLAN = Composition((Invoke("w", "worker", (Binding(name="brief", value="go"),)),))


def _options(saver: Any) -> RunOptions:
    return RunOptions(
        lease=Lease(Ceiling(40, 3600, 10_000), Floor(0)), run_id="host", checkpointer=saver
    )


async def _collect(events: Any) -> list[Event]:
    return [e async for e in events]


def _tool_answers(model: ScriptedModel) -> list[str]:
    return [
        m.content
        for r in model.requests
        for m in r.messages
        if m.role == "tool" and m.tool_call_id == "w1"
    ]


# ---------------------------------------------------------------- the run parks at the top


async def test_the_tool_calls_question_parks_the_whole_run_with_the_question() -> None:
    written.clear()
    ports = _ports(WRITES_THEN_DONE, agents=(worker(),))

    parked = await _collect(run(PLAN, ports, options=_options(InMemorySaver())))

    asked = [e for e in parked if isinstance(e, ApprovalRequested)]
    assert [e.run_id for e in asked][-1] == "host", "the question must be the top run's to answer"
    assert "outside the workspace" in asked[-1].question
    assert not [e for e in parked if isinstance(e, Ended) and e.run_id == "host"]
    assert written == [], "the write happened before anybody answered"
    model = ports.model
    assert isinstance(model, ScriptedModel)
    assert len(model.requests) == 1, "the model was asked again before the host answered"


# -------------------------------------------------------- allowed: the tool ran, the model was told


async def test_an_allow_lets_the_tool_run_and_the_model_hears_the_result() -> None:
    written.clear()
    saver = InMemorySaver()
    ports = _ports(WRITES_THEN_DONE, agents=(worker(),))
    await _collect(run(PLAN, ports, options=_options(saver)))

    after = await _collect(resume(PLAN, Allow(), ports, options=_options(saver)))

    assert written == ["/elsewhere/notes.md"]
    model = ports.model
    assert isinstance(model, ScriptedModel)
    assert _tool_answers(model) == ['{"path": "/elsewhere/notes.md", "bytes": 2}']
    ended = [e for e in after if isinstance(e, Ended) and e.run_id == "host"]
    assert ended and ended[-1].reason == "completed"
    done = [e for e in after if e.kind == "observed" and e.step == "w"][-1]
    output = getattr(done.observation, "output", {})
    assert isinstance(output, dict)
    assert (output["reason"], output["turns"]) == ("done", 2)


async def test_a_refusal_reaches_the_tool_and_the_model_is_told_it_was_refused() -> None:
    written.clear()
    saver = InMemorySaver()
    ports = _ports(WRITES_THEN_DONE, agents=(worker(),))
    await _collect(run(PLAN, ports, options=_options(saver)))

    await _collect(resume(PLAN, Refuse("not on my machine"), ports, options=_options(saver)))

    assert written == []
    model = ports.model
    assert isinstance(model, ScriptedModel)
    (answer,) = _tool_answers(model)
    assert "refused" in answer and "not on my machine" in answer
    assert "did not run" not in answer, (
        "the model must be told it was refused, not that nothing happened"
    )


# ---------------------------------------------------------------- the transcript survives the park


async def test_the_agent_resumes_mid_conversation_not_from_the_top() -> None:
    """Turn one looked something up; turn two asked to write. After the answer, turn three sees
    both — the transcript survived the park, and the model was not re-asked turn one."""
    written.clear()
    saver = InMemorySaver()
    script = [
        says(ToolCall("l1", "look", {"topic": "lathe"})),
        says(ToolCall("w1", "write_file", {"path": "/elsewhere/notes.md", "content": "12kg"})),
        says(ToolCall("d1", "done", {"summary": "noted"})),
    ]
    ports = _ports(script, agents=(worker(),))
    await _collect(run(PLAN, ports, options=_options(saver)))
    await _collect(resume(PLAN, Allow(), ports, options=_options(saver)))

    model = ports.model
    assert isinstance(model, ScriptedModel)
    assert len(model.requests) == 3, "the model was asked more turns than it took"
    third = model.requests[2].messages
    roles = [(m.role, getattr(m, "tool_call_id", None)) for m in third]
    assert ("tool", "l1") in roles and ("tool", "w1") in roles


# -------------------------------------------------------------- nested: an orchestrator's sub-agent


async def test_a_question_two_levels_down_reaches_the_host_and_the_answer_reaches_the_tool() -> (
    None
):
    written.clear()
    saver = InMemorySaver()
    lead = AgentComponent(
        pattern=Pattern(name="lead", system="delegate", tool_names=frozenset({"worker"})),
        effects=EffectProfile(writes=WORKSPACE, costs=True),
        name="lead",
        at=AT,
    )
    script = [
        says(ToolCall("s1", "worker", {"brief": "write the notes"})),  # the lead delegates
        says(
            ToolCall("w1", "write_file", {"path": "/elsewhere/notes.md", "content": "hi"})
        ),  # the worker
        says(ToolCall("d2", "done", {"summary": "wrote"})),  # the worker, after the answer
        says(ToolCall("d1", "done", {"summary": "delegated"})),  # the lead
    ]
    ports = _ports(script, agents=(worker(), lead))
    plan = Composition((Invoke("top", "lead", (Binding(name="brief", value="go"),)),))

    parked = await _collect(run(plan, ports, options=_options(saver)))
    asked = [e for e in parked if isinstance(e, ApprovalRequested) and e.run_id == "host"]
    assert asked and "outside the workspace" in asked[-1].question

    after = await _collect(resume(plan, Allow(), ports, options=_options(saver)))
    assert written == ["/elsewhere/notes.md"]
    ended = [e for e in after if isinstance(e, Ended) and e.run_id == "host"]
    assert ended and ended[-1].reason == "completed"


# ------------------------------------------------------------ a plan that asks twice parks twice


async def test_a_plan_whose_second_step_also_asks_parks_the_run_a_second_time() -> None:
    """The model authored a two-step plan and both steps write outside the workspace. The first
    parks the run; after the answer the child continues and the second asks — and the agent
    parks again rather than reporting the plan half-done."""
    import json

    from shadow_hdk.kernel.contracts import dump

    written.clear()
    saver = InMemorySaver()
    two_writes = Composition(
        (
            Invoke(
                "a", "write_file", (Binding("path", value="/x/a"), Binding("content", value="1"))
            ),
            Invoke(
                "b", "write_file", (Binding("path", value="/x/b"), Binding("content", value="2"))
            ),
        )
    )
    authored = ToolCall("c1", "compose", json.loads(dump(two_writes, Composition)))
    plan_pattern = Pattern(name="planner", system="plan", meta_tools=frozenset({"compose", "done"}))
    planner = AgentComponent(
        pattern=plan_pattern,
        effects=EffectProfile(writes=WORKSPACE, costs=True),
        name="worker",
        at=AT,
    )
    script = [says(authored), says(ToolCall("d1", "done", {"summary": "both written"}))]
    ports = _ports(script, agents=(planner,))

    first = await _collect(run(PLAN, ports, options=_options(saver)))
    assert [e.step for e in first if isinstance(e, ApprovalRequested) and e.run_id != "host"] == [
        "a"
    ]

    second = await _collect(resume(PLAN, Allow(), ports, options=_options(saver)))
    assert written == ["/x/a"], "the first answer let only the first write through"
    assert [e.step for e in second if isinstance(e, ApprovalRequested) and e.run_id != "host"] == [
        "b"
    ]
    assert not [e for e in second if isinstance(e, Ended) and e.run_id == "host"], "parked again"

    third = await _collect(resume(PLAN, Allow(), ports, options=_options(saver)))
    assert written == ["/x/a", "/x/b"]
    assert [e for e in third if isinstance(e, Ended) and e.run_id == "host"][
        -1
    ].reason == "completed"
