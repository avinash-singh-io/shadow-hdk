"""`ctx.ask()`: a question the host answers while the step is still running (D58).

The other shape from D57's: no park, because the step cannot stop — it holds something alive. The
question is on the record where it was raised; the host sees it on its `Questions` handle and
answers by handle; with no handle the answer is a refusal that says nobody was there.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Completed,
    Composition,
    Floor,
    Invoke,
    Lease,
    Observation,
)
from shadow_hdk.kernel.events import Asked as AskedEvent
from shadow_hdk.kernel.ports import Allow, Refuse
from shadow_hdk.runtime import Ports, Questions, RunOptions, current_run, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)

pytestmark = pytest.mark.anyio

ASKER = make_registration("asker")
PLAN = Composition((Invoke("s1", "asker", (Binding("brief", value="go"),)),))


class _AllowAll:
    async def judge(self, effects: Any, context: Any) -> Allow:
        return Allow()


def _ports(asker: Any) -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(ASKER, asker)]),),
        governance=_AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


async def asks_then_reports(_inputs: JsonValue) -> Observation:
    context = current_run()
    assert context is not None
    answer = await context.ask("may I?")
    return Completed({"answer": answer.kind, "reason": getattr(answer, "reason", None)})


async def _collect(events: Any) -> list[Any]:
    return [e async for e in events]


async def test_the_question_is_on_the_record_and_the_host_answers_by_handle() -> None:
    questions = Questions()
    options = RunOptions(lease=Lease(Ceiling(5, 60, None), Floor(0)), questions=questions)

    async def the_host() -> None:
        pending = await asyncio.wait_for(questions.next(), 10)
        assert pending.question == "may I?" and pending.step == "s1"
        assert questions.pending() == (pending,)
        assert questions.answer(pending.handle, Allow())
        assert questions.answer(pending.handle, Allow()) is False, "answered once"

    host = asyncio.create_task(the_host())
    events = await _collect(run(PLAN, _ports(asks_then_reports), options=options))
    await host

    asked = [e for e in events if isinstance(e, AskedEvent)]
    assert [(a.step, a.question) for a in asked] == [("s1", "may I?")]
    done = [e for e in events if e.kind == "observed"][-1]
    assert done.observation == Completed({"answer": "allow", "reason": None})
    assert questions.pending() == ()


async def test_with_nobody_to_ask_the_answer_is_a_refusal_that_says_so() -> None:
    options = RunOptions(lease=Lease(Ceiling(5, 60, None), Floor(0)))
    events = await _collect(run(PLAN, _ports(asks_then_reports), options=options))

    done = [e for e in events if e.kind == "observed"][-1]
    output = getattr(done.observation, "output", {})
    assert isinstance(output, dict)
    assert output["answer"] == "refuse"
    assert "nobody" in str(output["reason"])
    assert [e for e in events if isinstance(e, AskedEvent)], "still on the record"


async def test_a_child_run_inherits_the_parents_handle() -> None:
    questions = Questions()
    options = RunOptions(lease=Lease(Ceiling(10, 60, None), Floor(0)), questions=questions)

    async def spawns_an_asker(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        _, events = await context.children.spawn(PLAN, Ceiling(3, 60, None))
        return Completed([e.kind for e in events if e.kind == "observed"])

    SPAWNER = make_registration("spawner")

    async def the_host() -> None:
        pending = await asyncio.wait_for(questions.next(), 10)
        questions.answer(pending.handle, Refuse("no"))

    ports = Ports(
        model=None,
        components=(InMemoryComponents([(ASKER, asks_then_reports), (SPAWNER, spawns_an_asker)]),),
        governance=_AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    host = asyncio.create_task(the_host())
    events = await _collect(run(Composition((Invoke("p", "spawner", ()),)), ports, options=options))
    await host
    child_done = [e for e in events if e.kind == "observed" and e.step == "s1"]
    assert child_done[-1].observation == Completed({"answer": "refuse", "reason": "no"})


async def test_a_question_the_asker_stopped_waiting_for_is_withdrawn() -> None:
    """A CLI times a call out; the question it raised must not sit on the host's screen with
    buttons that answer nothing."""
    import asyncio

    from shadow_hdk.runtime import Questions
    from shadow_hdk.runtime.questions import Pending

    questions = Questions()
    pending = Pending(handle="h", run_id="r", step="s", question="?")
    asking = asyncio.create_task(questions.ask(pending))
    await asyncio.sleep(0)
    assert questions.pending() == (pending,)

    asking.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asking

    withdrawn = await asyncio.wait_for(questions.next_withdrawn(), 1)
    assert withdrawn.handle == "h"
    assert questions.pending() == ()
    assert questions.answer("h", None) is False
