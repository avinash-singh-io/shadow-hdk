"""A question carries what it is about: the component and the inputs (BUG-026).

Measured 2026-09-12 in the studio: *mode 'open' asks before this: it writes more than usual* —
and nothing else. The person could not see whether they were allowing `read_file sales.csv` or
`run_shell pip install pandas`, because the `Asked` event and the pending question carried the
policy's sentence and the step's id, and the step had not been invoked (it is judged first).

Consent to something unseen is not consent (D38). So `Asked` names the component and carries
the inputs, on both paths — the run that parks, and the question asked live while a CLI waits.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from shadow_hdk.kernel import Binding, Ceiling, Composition, EffectProfile, Floor, Invoke, Lease
from shadow_hdk.kernel.events import ApprovalRequested
from shadow_hdk.kernel.observations import Completed, Observation
from shadow_hdk.kernel.ports import Allow, Ask, Context, Judgement
from shadow_hdk.runtime import Approvals, Ports, RunOptions, current_run, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)

pytestmark = pytest.mark.anyio

WORK = make_registration("work")
ASKER = make_registration("asker")


class AsksAboutEverything:
    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        if context.step == "s1":
            return Ask("may it?")
        return Allow()


async def _work(_inputs: Any) -> Observation:
    return Completed("done")


def _ports(governance: Any, extra: Any = None) -> Ports:
    pairs = [(WORK, _work)] + ([extra] if extra else [])
    return Ports(
        model=None,
        components=(InMemoryComponents(pairs),),
        governance=governance,
        sink=ListSink(),
        clock=FixedClock(),
    )


async def test_the_asked_event_names_the_component_and_carries_the_inputs() -> None:
    plan = Composition((Invoke("s1", "work", (Binding("path", value="sales.csv"),)),))
    options = RunOptions(lease=Lease(Ceiling(5, 60, None), Floor(0)), run_id="q")

    events = [e async for e in run(plan, _ports(AsksAboutEverything()), options=options)]

    asked = [e for e in events if isinstance(e, ApprovalRequested)]
    assert len(asked) == 1
    assert asked[0].component == "work"
    assert asked[0].inputs == {"path": "sales.csv"}


async def test_a_question_asked_live_says_what_it_is_about() -> None:
    questions = Approvals()
    seen: list[Any] = []

    async def asker(_inputs: Any) -> Observation:
        context = current_run()
        assert context is not None
        answer = await context.request_approval(
            "may it run this?", about=("run_shell", {"command": "pip install pandas"})
        )
        return Completed(str(answer))

    async def host() -> None:
        pending = await asyncio.wait_for(questions.next(), 5)
        seen.append(pending)
        questions.answer(pending.handle, Allow())

    plan = Composition((Invoke("s2", "asker", ()),))
    options = RunOptions(
        lease=Lease(Ceiling(5, 60, None), Floor(0)), run_id="q2", approvals=questions
    )
    task = asyncio.create_task(host())
    events = [e async for e in run(plan, _ports(Allowing(), (ASKER, asker)), options=options)]
    await task

    assert seen[0].component == "run_shell"
    assert seen[0].inputs == {"command": "pip install pandas"}
    asked = [e for e in events if isinstance(e, ApprovalRequested)][0]
    assert asked.component == "run_shell" and asked.inputs == {"command": "pip install pandas"}


class Allowing:
    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        return Allow()
