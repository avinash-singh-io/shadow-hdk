"""D116: amend is a host handle. A plan a CLI proposed through `compose` parks on a question
inside it; the person may settle it as it is, or hand the thread a different composition — which
is admitted like the original before the run takes it. Refused, the parked plan is untouched and
the question stays open.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec
from shadow_hdk.kernel import (
    Allow,
    Ask,
    Binding,
    Ceiling,
    Completed,
    Composition,
    Context,
    EffectProfile,
    FanOut,
    Floor,
    Invoke,
    Judgement,
    Lease,
    PlanLimits,
    ScopeSet,
)
from shadow_hdk.kernel.events import Composed, PlanAdmitted, PlanRefused
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.approvals import Approvals
from shadow_hdk.runtime.checkpoints import InMemoryRunStore, saver_over
from shadow_hdk.runtime.planning import plan_components
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink, make_registration
from shadow_hdk.runtime.threads import InMemoryThreads, Thread
from shadow_hdk.testing import ScriptedAgent

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
LOOK = make_registration("look", effects=EffectProfile(reads=WORKSPACE))
# A reversible write: the policy asks about it (the park under test); an irreversible one would
# also meet Phase 33's authority boundary, which is not what this file proves.
WIPE = make_registration("wipe", effects=EffectProfile(writes=WORKSPACE))
wiped: list[Any] = []


async def look(_inputs: Any) -> Any:
    return Completed({"found": True})


async def wipe(inputs: Any) -> Any:
    wiped.append(inputs)
    return Completed({"wiped": True})


class AskBeforeWorkspaceWrites:
    """Asks about a write to the workspace — not about the turn step itself, which declares a
    write to the provider's own state."""

    async def judge(self, effects: EffectProfile, _context: Context) -> Judgement:
        if "workspace" in effects.writes.names or effects.writes.everything:
            return Ask("a write — a person decides")
        return Allow()


def a_plan(*steps: dict[str, Any]) -> dict[str, Any]:
    return {"steps": list(steps)}


def invoke(step_id: str, component: str) -> dict[str, Any]:
    return {"kind": "invoke", "id": step_id, "component": component, "inputs": []}


async def _thread(
    tmp_path: Path, agent: ScriptedAgent, *, limits: PlanLimits | None = None
) -> Thread:
    ports = Ports(
        model=None,
        components=(InMemoryComponents([(LOOK, look), (WIPE, wipe)]), plan_components()),
        governance=AskBeforeWorkspaceWrites(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=ports,
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(60, 600, None), Floor(0)),
        approvals=Approvals(),
        checkpointer=saver_over(InMemoryRunStore()),
        modes=ModeRegistry((ModeSpec.of("m", plan=limits),)),
        mode="m",
    )
    agent.reach = thread.registry.call
    return thread


async def test_a_plan_parked_inside_compose_is_settled_on_the_same_shape(tmp_path: Path) -> None:
    """The question a step inside the plan raises becomes the compose call's own (D57); parked on
    purpose, it is settled later and the plan continues on the composition it parked with."""
    wiped.clear()
    agent = ScriptedAgent(
        [([("compose", a_plan(invoke("a", "look"), invoke("w", "wipe")))], "one")]
    )
    thread = await _thread(tmp_path, agent)
    try:
        first = [e async for e in thread.turn("plan it", on_question="park")]
        assert thread.record.turns[-1].outcome == "parked"
        [question] = thread.pending
        assert question.component == "compose", "the person is asked about the call that parked"
        assert "a write" in question.question, "with the question the step inside raised"
        assert wiped == [], "nothing wrote before anybody answered"
        settled = await thread.settle(question.handle, Allow())
    finally:
        await thread.close()
    assert any(isinstance(e, PlanAdmitted) for e in first)
    assert not any(isinstance(e, PlanAdmitted) and e.amendment for e in settled), (
        "the same plan resumed is no amendment"
    )
    assert wiped == [{}], "the write ran once, after the person's yes"


async def test_an_amendment_is_admitted_and_the_plan_continues_on_the_new_shape(
    tmp_path: Path,
) -> None:
    wiped.clear()
    agent = ScriptedAgent(
        [([("compose", a_plan(invoke("a", "look"), invoke("w", "wipe")))], "one")]
    )
    thread = await _thread(tmp_path, agent)
    try:
        [e async for e in thread.turn("plan it", on_question="park")]
        [question] = thread.pending
        amended = Composition(
            (
                Invoke("a", "look"),
                Invoke("w", "wipe"),
                Invoke("after", "look", (Binding(name="topic", value="after"),)),
            )
        )
        events = await thread.amend(question.handle, amended, Allow())
        assert thread.pending == (), "settled by the amendment"
    finally:
        await thread.close()
    assert next(e for e in events if isinstance(e, PlanAdmitted)).amendment is True
    assert next(e for e in events if isinstance(e, Composed)).composition == amended
    below = [e.step for e in events if e.kind == "invoked" and e.step != "tools__compose__1"]
    assert below == ["w", "after"], "continued where it parked, then the new step"
    assert wiped == [{}]


async def test_a_refused_amendment_leaves_the_plan_parked_and_the_question_open(
    tmp_path: Path,
) -> None:
    wiped.clear()
    agent = ScriptedAgent(
        [([("compose", a_plan(invoke("a", "look"), invoke("w", "wipe")))], "one")]
    )
    thread = await _thread(tmp_path, agent, limits=PlanLimits(fan_out=1))
    try:
        [e async for e in thread.turn("plan it", on_question="park")]
        [question] = thread.pending
        too_wide = Composition((FanOut("f", (Invoke("w", "wipe"), Invoke("x", "look"))),))
        events = await thread.amend(question.handle, too_wide, Allow())
        kinds = [e.kind for e in events]
        refused = next(e for e in events if isinstance(e, PlanRefused))
        assert refused.amendment is True
        assert [(m.axis, m.required, m.found) for m in refused.mismatches] == [
            ("fan_out", "1", "2")
        ]
        assert "invoked" not in kinds[kinds.index("plan_refused") :], "nothing of the plan ran"
        assert kinds[-1] == "approval_requested", "the compose call parked again on its question"
        [still] = thread.pending
        assert still.component == "compose" and "a write" in still.question, "still open"
        assert wiped == []
    finally:
        await thread.close()


async def test_a_plan_that_asks_twice_parks_twice_and_runs_both_after_two_answers(
    tmp_path: Path,
) -> None:
    """A step that parks a second time in the same leg (D57): LangGraph replays a task's earlier
    answers by index on every resume, so the executor drains the replayed ones and hands the
    component only the newest — the first answer is never applied twice, and the second park
    parks rather than returning."""
    wiped.clear()
    agent = ScriptedAgent(
        [([("compose", a_plan(invoke("w1", "wipe"), invoke("w2", "wipe")))], "one")]
    )
    thread = await _thread(tmp_path, agent)
    try:
        [e async for e in thread.turn("plan it", on_question="park")]
        [first] = thread.pending
        assert first.component == "compose"
        again = await thread.settle(first.handle, Allow())
        assert [e.kind for e in again][-1] == "approval_requested", "parked on the second write"
        assert wiped == [{}], "the first write ran once"
        [second] = thread.pending
        assert second.handle == first.handle, "the same run, the same step: one handle (D57)"
        assert "a write" in second.question
        done = await thread.settle(second.handle, Allow())
        assert thread.pending == ()
        assert wiped == [{}, {}], "the second write ran once, after its own answer"
        assert any(e.kind == "observed" and e.step == "tools__compose__1" for e in done)
    finally:
        await thread.close()


async def test_a_refused_amendment_then_an_admitted_one_on_the_same_thread(tmp_path: Path) -> None:
    wiped.clear()
    agent = ScriptedAgent(
        [([("compose", a_plan(invoke("a", "look"), invoke("w", "wipe")))], "one")]
    )
    thread = await _thread(tmp_path, agent, limits=PlanLimits(fan_out=1))
    try:
        [e async for e in thread.turn("plan it", on_question="park")]
        [question] = thread.pending
        too_wide = Composition((FanOut("f", (Invoke("w", "wipe"), Invoke("x", "look"))),))
        refused = await thread.amend(question.handle, too_wide, Allow())
        assert [e.kind for e in refused][-1] == "approval_requested"
        [still] = thread.pending
        fine = Composition((Invoke("a", "look"), Invoke("w", "wipe"), Invoke("after", "look")))
        events = await thread.amend(still.handle, fine, Allow())
        mismatches = [
            (m.axis, m.found) for e in events if isinstance(e, PlanRefused) for m in e.mismatches
        ]
        assert mismatches == [], "the refused shape is not replayed onto the next amendment"
        assert next(e for e in events if isinstance(e, PlanAdmitted)).amendment is True
        assert thread.pending == ()
        below = [e.step for e in events if e.kind == "invoked" and e.step != "tools__compose__1"]
        assert below == ["w", "after"]
        assert wiped == [{}]
    finally:
        await thread.close()
