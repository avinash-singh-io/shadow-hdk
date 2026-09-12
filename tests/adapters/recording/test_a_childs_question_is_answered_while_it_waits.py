"""A CLI's tool call the policy asks about reaches the person while the CLI waits (BUG-021, D58).

A subscription provider calls a tool over the socket and blocks on the answer. The RecordingServer
runs the call as a nested run; when the policy says `Ask`, that run parks — and the call had no
observation, so the CLI was told *the call produced no observation* and nobody was asked. The run
cannot park the way D57 parks an in-process agent: the step holding the conversation is what keeps
the CLI alive.

So the question is asked **live**: `Asked` goes on the record, the call waits on the host's
`Approvals` handle, and when the host answers the nested run is resumed with the judgement and the
CLI gets the result — allowed, the tool ran; refused, it is told refused. A run with no `Approvals`
handle answers for itself: refused, and the record says nobody was there to ask.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from shadow_hdk.adapters.recording import RecordingServer

from shadow_hdk.kernel import EffectProfile, ScopeSet
from shadow_hdk.kernel.events import ApprovalRequested
from shadow_hdk.kernel.ports import Allow, Ask, Context, Judgement, Refuse
from shadow_hdk.runtime import Approvals, RunContext

from .conftest import WORKSPACE, with_a_run

pytestmark = pytest.mark.anyio


class AsksAboutWrites:
    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        if effects.writes and not effects.writes <= ScopeSet.of("nothing"):
            return Ask(f"{context.step} wants to write; allow?")
        return Allow()


async def _wipe_through(context: RunContext) -> Any:
    holder = RecordingServer(context)
    return await holder.call("wipe", {})


async def test_the_question_reaches_the_host_and_an_allow_lets_the_call_through() -> None:
    questions = Approvals()

    async def the_host_says_yes() -> None:
        pending = await asyncio.wait_for(questions.next(), 10)
        assert "wants to write" in pending.question
        questions.answer(pending.handle, Allow())

    async def drive(context: RunContext) -> Any:
        host = asyncio.create_task(the_host_says_yes())
        try:
            return await _wipe_through(context)
        finally:
            await host

    result, events = await with_a_run(drive, governance=AsksAboutWrites(), approvals=questions)

    assert not result.is_error, result.content[0].text
    assert '"wiped": true' in result.content[0].text
    assert any(isinstance(e, ApprovalRequested) for e in events), (
        "the question was not on the record"
    )


async def test_a_refusal_tells_the_child_it_was_refused() -> None:
    questions = Approvals()

    async def the_host_says_no() -> None:
        pending = await asyncio.wait_for(questions.next(), 10)
        questions.answer(pending.handle, Refuse("not today"))

    async def drive(context: RunContext) -> Any:
        host = asyncio.create_task(the_host_says_no())
        try:
            return await _wipe_through(context)
        finally:
            await host

    result, _ = await with_a_run(drive, governance=AsksAboutWrites(), approvals=questions)

    assert result.is_error
    assert "refused" in result.content[0].text and "not today" in result.content[0].text
    assert "no observation" not in result.content[0].text


async def test_a_person_who_takes_their_time_does_not_cost_the_call_its_lease() -> None:
    """Measured in the studio, on the first question a person ever answered there: the nested
    run was resumed with the ceiling it had asked for at the start, which after a second of
    thinking was more wall-clock than the parent had left — *a child lease cannot exceed its
    parent's ceiling* — and the provider was told the call had failed. The child is held and
    sent the answer now, with a ceiling clamped to what is left."""
    questions = Approvals()

    async def the_host_thinks_first() -> None:
        pending = await asyncio.wait_for(questions.next(), 10)
        await asyncio.sleep(1.2)
        questions.answer(pending.handle, Allow())

    async def drive(context: RunContext) -> Any:
        host = asyncio.create_task(the_host_thinks_first())
        try:
            return await _wipe_through(context)
        finally:
            await host

    result, _ = await with_a_run(
        drive, governance=AsksAboutWrites(), approvals=questions, wall_seconds=3
    )

    assert not result.is_error, result.content[0].text
    assert '"wiped": true' in result.content[0].text


async def test_with_nobody_to_ask_the_call_is_refused_and_says_so() -> None:
    result, events = await with_a_run(_wipe_through, governance=AsksAboutWrites())

    assert result.is_error
    assert "nobody" in result.content[0].text.lower(), result.content[0].text
    assert "no observation" not in result.content[0].text


WORKSPACE_SCOPE = WORKSPACE  # re-exported for the module's readers
