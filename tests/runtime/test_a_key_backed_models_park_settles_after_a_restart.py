"""A key-backed model's parked call is settled on a thread picked up by its id (D80, D88, D98).

Lane P asked which shape the kit supports for a key-backed model's parked turn: a resident `Thread`
per conversation, a thread resumed by id, or no park at all. The answer this file makes true is
**the second, and therefore also the first**: settling does not go through the provider.

The reason is structural. A park is answered by waking the run that parked, from the
**checkpointer** — the act resumes at the step it stopped on. The provider is not consulted, and a
key-backed model has no session to consult anyway: the record is its memory (D98). So a host may
open a thread for one turn, let it park, close it, and settle it from a different process an hour
later — which is exactly what a product that opens a thread per turn needs, and the case the CLI
proof (`test_a_parked_turn_survives_the_host.py`) did not cover, because its agent was a resident
one.

The two durable parts are the thread store, which keeps the question, and the checkpointer, which
keeps the run. Both are sqlite here, and the second host opens them fresh.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.kernel import (
    Allow,
    Ask,
    Ceiling,
    Completed,
    EffectProfile,
    Floor,
    Lease,
    ModelResponse,
    ScopeSet,
    ToolCall,
)
from shadow_hdk.kernel.ports import Context, Judgement
from shadow_hdk.runtime import Approvals, Approve, Deny, Ports
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)
from shadow_hdk.runtime.threads import Thread
from shadow_hdk.serve.stores import stores_for

pytestmark = pytest.mark.anyio

WRITE = make_registration("write", effects=EffectProfile(writes=ScopeSet.of("workspace")))


class Writes:
    def __init__(self) -> None:
        self.wrote: list[Any] = []

    async def __call__(self, inputs: Any) -> Completed:
        self.wrote.append(inputs)
        return Completed({"wrote": inputs})


class AskWrites:
    async def judge(self, effects: EffectProfile, _context: Context) -> Judgement:
        return Ask("may this write?") if "workspace" in effects.writes.names else Allow()


def _ports(writes: Writes) -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(WRITE, writes)]),),
        governance=AskWrites(),
        sink=ListSink(),
        clock=FixedClock(),
    )


def _lease() -> Lease:
    return Lease(Ceiling(40, 600, 100), Floor(0))


def _model(*responses: ModelResponse) -> Any:
    return ScriptedModel(list(responses))


async def _park_a_turn_and_go_away(where: Path) -> tuple[str, str, Any]:
    """The whole of a host's turn for a key-backed model: open a thread, take one turn, close it.
    The turn parks; nothing is kept in this process afterwards."""
    from shadow_hdk.adapters.agent import ModelAgent, single

    stores = stores_for(f"sqlite:///{where}/live.sqlite")
    model = _model(ModelResponse(tool_calls=(ToolCall("call-1", "write", {"value": 1}),)))
    thread = await Thread.open(
        agent=ModelAgent(model=model, pattern=single),
        ports=_ports(Writes()),
        store=stores.threads,
        root=where / "work",
        lease=_lease(),
        approvals=Approvals(),
        checkpointer=await stores.checkpointer(),
    )
    try:
        [event async for event in thread.turn("write it", on_question="park")]
        parked = thread.record.turns[-1]
        (question,) = thread.record.pending
    finally:
        await thread.close()
        await stores.aclose()
    return thread.id, question.handle, parked


async def test_the_turn_ends_parked_and_says_so_without_addressing_anyone(tmp_path: Path) -> None:
    """BUG-228 at the surface a host reads. `outcome` is `parked`; the text is the kit's own
    plain description, not the note written for the agent and not the model's parting words."""
    _thread_id, _handle, parked = await _park_a_turn_and_go_away(tmp_path)

    assert parked.outcome == "parked"
    assert "write" in parked.text
    assert "you" not in parked.text.lower().split()


async def test_the_question_outlives_the_thread_that_asked_it(tmp_path: Path) -> None:
    thread_id, handle, _parked = await _park_a_turn_and_go_away(tmp_path)

    stores = stores_for(f"sqlite:///{tmp_path}/live.sqlite")
    try:
        record = await stores.threads.get(thread_id)
        assert record is not None
        (question,) = record.pending
        assert question.handle == handle
        assert question.component == "write" and question.inputs == {"value": 1}
        assert question.run_id, "the run that parked, to be woken from the checkpointer"
    finally:
        await stores.aclose()


async def test_approved_on_a_thread_resumed_by_id_the_act_runs(tmp_path: Path) -> None:
    """The claim lane P's approval flow rests on: a second host, a new `Thread`, no provider
    session anywhere, and the act the person approved runs from its checkpoint."""
    from shadow_hdk.adapters.agent import ModelAgent, single

    thread_id, handle, _parked = await _park_a_turn_and_go_away(tmp_path)

    stores = stores_for(f"sqlite:///{tmp_path}/live.sqlite")
    writes = Writes()
    model = _model(ModelResponse(text="done"))
    resumed = await Thread.resume(
        thread_id,
        agent=ModelAgent(model=model, pattern=single),
        ports=_ports(writes),
        store=stores.threads,
        lease=_lease(),
        approvals=Approvals(),
        checkpointer=await stores.checkpointer(),
    )
    try:
        assert [q.handle for q in resumed.pending] == [handle]

        events = await resumed.settle(handle, Approve())

        assert any(event.kind == "observed" for event in events), events
        assert writes.wrote == [{"value": 1}], "the act ran, once, after the restart"
        assert resumed.pending == ()

        # And the model is told at its next turn what became of the call it made: its own
        # transcript cannot be rewound, so a call it never heard back from is one it repeats.
        [event async for event in resumed.turn("carry on")]
        told = model.requests[-1].messages[-1].content
        assert "write" in told and "approved" in told
    finally:
        await resumed.close()
        await stores.aclose()


async def test_denied_on_a_thread_resumed_by_id_nothing_runs_and_the_model_is_told_why(
    tmp_path: Path,
) -> None:
    from shadow_hdk.adapters.agent import ModelAgent, single

    thread_id, handle, _parked = await _park_a_turn_and_go_away(tmp_path)

    stores = stores_for(f"sqlite:///{tmp_path}/live.sqlite")
    writes = Writes()
    model = _model(ModelResponse(text="understood"))
    resumed = await Thread.resume(
        thread_id,
        agent=ModelAgent(model=model, pattern=single),
        ports=_ports(writes),
        store=stores.threads,
        lease=_lease(),
        approvals=Approvals(),
        checkpointer=await stores.checkpointer(),
    )
    try:
        await resumed.settle(handle, Deny("not that one"))

        assert writes.wrote == []
        assert resumed.pending == ()

        [event async for event in resumed.turn("carry on")]
        told = model.requests[-1].messages[-1].content
        assert "denied" in told and "not that one" in told
    finally:
        await resumed.close()
        await stores.aclose()
