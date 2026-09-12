"""A component may ask on its own behalf, and the run parks on it as if governance had (D57).

`Asked` has been an observation kind since Phase 0 — *the step paused; whoever implements
governance decides what asking means* — and nothing ever produced one. BUG-020 is why it has to
exist: an agent whose tool call was asked about has a question that is not the policy's and is
not the agent's own to answer. It parks the run with it. On resume the component is invoked
again, and finds the answer and whatever it `kept` before parking — both carried in the interrupt
payload the checkpointer already holds, so the runtime keeps nothing durable (`09` §6) and a
process may end between the question and the answer.
"""

from __future__ import annotations

from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Completed,
    Composition,
    Ended,
    Event,
    Floor,
    Invoke,
    Lease,
    Observation,
)
from shadow_hdk.kernel.events import ApprovalRequested
from shadow_hdk.kernel.observations import ApprovalRequest, Refused
from shadow_hdk.kernel.ports import Allow, Refuse
from shadow_hdk.runtime import Ports, RunOptions, current_run, resume, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)

pytestmark = pytest.mark.anyio

ASKER = make_registration("asker")
WORK = make_registration("work")


async def plain_work(_inputs: JsonValue) -> Observation:
    return Completed("worked")


class AsksOnce:
    """First leg: keep some state and ask. Second leg: read both back and finish."""

    def __init__(self) -> None:
        self.legs: list[dict[str, Any]] = []

    async def __call__(self, inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        back = await context.resumed()
        self.legs.append(
            {"answer": back.answer if back else None, "kept": back.kept if back else None}
        )
        if back is None:
            await context.keep({"draft": "half done", "n": 3})
            return ApprovalRequest(question="may I finish?", handle="mine-1")
        if isinstance(back.answer, Refuse):
            return Refused(back.answer.reason)
        return Completed({"finished": True, "from": back.kept})


def _ports(asker: AsksOnce) -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(ASKER, asker), (WORK, plain_work)]),),
        governance=_AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


class _AllowAll:
    async def judge(self, effects: Any, context: Any) -> Allow:
        return Allow()


PLAN = Composition((Invoke("s1", "asker", (Binding("brief", value="go"),)),))


def _options(saver: Any) -> RunOptions:
    return RunOptions(
        lease=Lease(Ceiling(10, 60, None), Floor(0)), run_id="asks", checkpointer=saver
    )


async def _collect(events: Any) -> list[Event]:
    return [e async for e in events]


async def test_a_component_that_asks_parks_the_run_with_its_question() -> None:
    asker, saver = AsksOnce(), InMemorySaver()

    parked = await _collect(run(PLAN, _ports(asker), options=_options(saver)))

    asked = [e for e in parked if isinstance(e, ApprovalRequested)]
    assert [a.question for a in asked] == ["may I finish?"]
    assert asked[0].step == "s1" and asked[0].handle == "asks:s1"
    assert not [e for e in parked if isinstance(e, Ended)], "a parked run must not report Ended"
    assert asker.legs == [{"answer": None, "kept": None}], "the first leg sees no answer"


async def test_the_resumed_component_finds_the_answer_and_what_it_kept() -> None:
    asker, saver = AsksOnce(), InMemorySaver()
    await _collect(run(PLAN, _ports(asker), options=_options(saver)))

    after = await _collect(resume(PLAN, Allow(), _ports(asker), options=_options(saver)))

    assert asker.legs[1] == {"answer": Allow(), "kept": {"draft": "half done", "n": 3}}
    done = [e for e in after if e.kind == "observed" and e.step == "s1"]
    assert done[-1].observation == Completed(
        {"finished": True, "from": {"draft": "half done", "n": 3}}
    )
    assert [e for e in after if isinstance(e, Ended)][-1].reason == "completed"


async def test_a_refusal_reaches_the_component_which_answers_for_itself() -> None:
    asker, saver = AsksOnce(), InMemorySaver()
    await _collect(run(PLAN, _ports(asker), options=_options(saver)))

    after = await _collect(resume(PLAN, Refuse("no"), _ports(asker), options=_options(saver)))

    done = [e for e in after if e.kind == "observed" and e.step == "s1"]
    assert done[-1].observation == Refused("no")


async def test_the_answer_survives_the_process_that_asked() -> None:
    """A different component object and a different saver object over the same file: nothing of
    the first leg is held in memory by the runtime, or by the component."""
    import tempfile
    from pathlib import Path

    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    with tempfile.TemporaryDirectory() as where:
        database = Path(where) / "runs.sqlite"
        async with AsyncSqliteSaver.from_conn_string(str(database)) as first:
            await _collect(run(PLAN, _ports(AsksOnce()), options=_options(first)))
        fresh = AsksOnce()
        async with AsyncSqliteSaver.from_conn_string(str(database)) as second:
            after = await _collect(resume(PLAN, Allow(), _ports(fresh), options=_options(second)))
        assert fresh.legs == [{"answer": Allow(), "kept": {"draft": "half done", "n": 3}}]
        assert [e for e in after if isinstance(e, Ended)][-1].reason == "completed"


async def test_the_step_is_counted_once_across_both_legs() -> None:
    """Two invocations, one step. The first leg's charge never reaches the checkpoint — the node
    interrupted before it returned — so the leg that completes is the one that counts, and the
    record says two steps for two. (Measured: a second leg that skipped the charge said one.)"""
    asker, saver = AsksOnce(), InMemorySaver()
    two = Composition(
        (
            Invoke("s1", "asker", (Binding("brief", value="go"),)),
            Invoke("s2", "work", (Binding("brief", value="again"),)),
        )
    )
    options = RunOptions(
        lease=Lease(Ceiling(2, 60, None), Floor(0)), run_id="asks", checkpointer=saver
    )
    await _collect(run(two, _ports(asker), options=options))
    after = await _collect(resume(two, Allow(), _ports(asker), options=options))

    assert [e.step for e in after if e.kind == "invoked"] == ["s1", "s2"]
    ended = [e for e in after if isinstance(e, Ended)][-1]
    assert (ended.reason, ended.steps_taken) == ("completed", 2)


async def test_a_step_that_runs_again_starts_a_fresh_leg() -> None:
    """An `Until` re-runs the same step id. What the previous leg was resumed with must not
    leak into the next run of that step — it asks again, on its own account."""
    from shadow_hdk.kernel import Condition, Until

    asker, saver = AsksOnce(), InMemorySaver()
    loop = Until(
        "u",
        Invoke("s1", "asker", (Binding("brief", value="go"),)),
        Condition("never", True),
        max_iterations=2,
    )
    plan = Composition((loop,))
    options = RunOptions(
        lease=Lease(Ceiling(10, 60, None), Floor(0)), run_id="asks", checkpointer=saver
    )
    await _collect(run(plan, _ports(asker), options=options))
    second = await _collect(resume(plan, Allow(), _ports(asker), options=options))

    questions = [e.question for e in second if isinstance(e, ApprovalRequested)]
    assert questions == ["may I finish?"], "the second run of s1 did not ask on its own account"
    assert [leg["answer"] for leg in asker.legs] == [None, Allow(), None]
