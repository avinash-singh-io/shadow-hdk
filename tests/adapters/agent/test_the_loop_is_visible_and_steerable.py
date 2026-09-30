"""The agent's own plan, and steering a key-backed turn (ENH-045, ENH-046, D171–D173).

Lane P's asks 8 and 9.

**The plan.** Half of it already existed and not the half a host needs: `Composed`,
`PlanAdmitted`/`PlanRefused` and `items()` say what the *runtime* is about to do. What was
absent is the agent's own narration — the field's to-do list, revised as it learns. A
registered component with
**no effects at all** (D171), so every mode admits it: an agent that had to ask permission to say
what it intends would stop saying it.

**The steer.** `ModelAgent.steer` answered `False`, honestly — and the loop between steps is the
kit's own, which is the one place it *could* be true (D173). The property that matters is not that
`steer` returns `True`, which is the easy half, but that the words **reach the model**.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.adapters.agent.planning import ITEMS, UPDATE_PLAN, PlanComponents
from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.kernel import Ceiling, Floor, Lease, ModelResponse
from shadow_hdk.kernel.observations import Completed, Refused
from shadow_hdk.kernel.ports import Message, ToolCall
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink
from shadow_hdk.runtime.threads import InMemoryThreads, Thread

pytestmark = pytest.mark.anyio


# ------------------------------------------------------------------ the plan


async def test_the_plan_is_a_tool_with_no_effects_at_all(tmp_path: Path) -> None:
    """D171. Nothing declared means every mode admits it, `read-only` included — which is what a
    narration needs to be worth having."""
    found = await PlanComponents().registrations()

    assert [r.id for r in found] == [UPDATE_PLAN]
    effects = found[0].component.effects
    assert not effects.reads.everything and not effects.reads.names, effects
    assert not effects.writes.everything and not effects.writes.names, effects
    assert effects.reaches is False and effects.costs is False, effects


async def test_a_plan_is_kept_and_counted_as_it_is_revised(tmp_path: Path) -> None:
    plan = PlanComponents()

    first = await plan.invoke(
        UPDATE_PLAN, {"items": [{"step": "read the code", "status": "doing"}]}
    )
    second = await plan.invoke(
        UPDATE_PLAN,
        {
            "items": [
                {"step": "read the code", "status": "done"},
                {"step": "write the test", "status": "doing"},
            ]
        },
    )

    assert isinstance(first, Completed) and isinstance(second, Completed)
    assert cast(Any, second.output)["items"] == 2
    assert cast(Any, second.output)["revision"] == 2, "a host can tell one revision from the next"
    assert [i["step"] for i in plan.plan] == ["read the code", "write the test"]
    assert plan.plan[0]["status"] == "done", "the latest is what is kept"


async def test_a_status_may_be_any_word_a_product_uses(tmp_path: Path) -> None:
    """D172. An enumeration would change the kit's contract every time a product wants a status it
    did not think of, and a plan's vocabulary is exactly what a product owns."""
    plan = PlanComponents()

    told = await plan.invoke(UPDATE_PLAN, {"items": [{"step": "x", "status": "blocked-on-review"}]})

    assert isinstance(told, Completed)
    assert plan.plan[0]["status"] == "blocked-on-review"


async def test_a_step_with_no_status_is_pending(tmp_path: Path) -> None:
    plan = PlanComponents()

    await plan.invoke(UPDATE_PLAN, {"items": [{"step": "x"}]})

    assert plan.plan[0]["status"] == "pending"


async def test_a_step_with_no_words_is_refused(tmp_path: Path) -> None:
    plan = PlanComponents()

    told = await plan.invoke(UPDATE_PLAN, {"items": [{"status": "doing"}]})

    assert isinstance(told, Refused) and "step 1" in told.reason, told
    assert plan.plan == (), "and nothing was kept"


async def test_a_plan_nobody_could_follow_is_refused(tmp_path: Path) -> None:
    plan = PlanComponents()

    told = await plan.invoke(UPDATE_PLAN, {"items": [{"step": f"s{n}"} for n in range(ITEMS + 1)]})

    assert isinstance(told, Refused) and str(ITEMS) in told.reason, told


async def test_the_plan_reaches_the_record_through_the_call_itself(tmp_path: Path) -> None:
    """Nothing extra was built for this: `Invoked.inputs` already carries every revision in order,
    which is why the plan is a component rather than a runtime concept."""
    from shadow_hdk.kernel import Invoked

    plan = PlanComponents()
    seen: list[Any] = []
    narrator = _SaysAPlan()
    thread = await Thread.open(
        agent=cast(Any, narrator),
        ports=Ports(
            model=None,
            components=(plan,),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(20, 600, None), Floor(0)),
    )
    narrator.reach = thread.registry.call
    try:
        async for event in thread.turn("get on with it"):
            seen.append(event)
    finally:
        await thread.close()

    invoked = [e for e in seen if isinstance(e, Invoked) and e.component == UPDATE_PLAN]
    assert invoked, [type(e).__name__ for e in seen]
    assert cast(Any, invoked[0].inputs)["items"][0]["step"] == "read the code"


class _SaysAPlan:
    """A provider double whose only move is to narrate a plan through the registry."""

    reach: Any = None

    async def open(self, **kw: Any) -> Any:
        return self

    async def turn(self, prompt: str) -> Any:
        from shadow_hdk.kernel import Turn

        if self.reach is not None:
            await self.reach(UPDATE_PLAN, {"items": [{"step": "read the code", "status": "doing"}]})
        return Turn(text="planned")

    async def steer(self, text: str) -> bool:
        return False

    async def interrupt(self) -> bool:
        return False

    async def close(self) -> None:
        return None


# ------------------------------------------------------------------ the steer


class Patient:
    """A model that calls a tool on its first step and answers on its second, so there is a gap
    between steps for a steer to land in — and keeps every request, so what it was told is
    readable."""

    def __init__(self) -> None:
        self.asked: list[Any] = []
        self.arrived = asyncio.Event()
        self.may_continue = asyncio.Event()

    async def complete(self, request: Any) -> ModelResponse:
        self.asked.append(request)
        if len(self.asked) == 1:
            self.arrived.set()
            await self.may_continue.wait()
            return ModelResponse(tool_calls=(ToolCall("c1", UPDATE_PLAN, {"items": []}),))
        return ModelResponse(text="done")

    async def stream(self, request: Any) -> Any:  # pragma: no cover
        from shadow_hdk.kernel.ports import ModelChunk

        response = await self.complete(request)
        yield ModelChunk(text=response.text, tool_calls=response.tool_calls, done=True)

    def words_of(self, which: int) -> list[str]:
        return [m.content for m in self.asked[which].messages if isinstance(m, Message)]


async def test_a_steer_reaches_a_key_backed_model_on_its_next_step(tmp_path: Path) -> None:
    """The property that matters, and the one `steer`'s return value does not establish: the words
    are in what the model was **actually asked** on its next step."""
    from shadow_hdk.adapters.agent import ModelAgent, single

    model = Patient()
    thread = await Thread.open(
        agent=ModelAgent(model=cast(Any, model), pattern=single),
        ports=Ports(
            model=cast(Any, model),
            components=(PlanComponents(),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(20, 600, None), Floor(0)),
    )

    async def take_a_turn() -> None:
        async for _ in thread.turn("start"):
            pass

    running = asyncio.create_task(take_a_turn())
    try:
        await asyncio.wait_for(model.arrived.wait(), timeout=10)

        taken = await thread.steer("actually, stop after the first file")

        assert taken is True, "the loop between steps is the kit's own, so this can be true"
        model.may_continue.set()
        await asyncio.wait_for(running, timeout=10)
    finally:
        if not running.done():
            running.cancel()
        await thread.close()

    assert len(model.asked) >= 2, "there was no second step to steer into"
    assert any("stop after the first file" in w for w in model.words_of(1)), model.words_of(1)
    assert not any("stop after the first file" in w for w in model.words_of(0)), (
        "a request already in flight cannot be changed, and must not appear to have been"
    )


async def test_a_steer_with_no_turn_running_is_false(tmp_path: Path) -> None:
    """The honest half, unchanged: `False` where there is nothing to steer — the same answer a
    one-shot CLI gives, and it keeps `steer`'s `bool` meaning something.

    Asked of the **session**, not the thread. `Conversation.steer` short-circuits on "is a turn
    running" before it ever reaches the provider, so a thread-level test here passes whatever the
    session does — found by a mutation that made the session answer `True` and broke nothing.
    """
    from shadow_hdk.adapters.agent import ModelAgent, single

    agent = ModelAgent(model=cast(Any, Patient()), pattern=single)
    session = await agent.open(workspace=str(tmp_path))

    assert await session.steer("nothing is running") is False


async def test_the_thread_also_says_false_before_a_turn(tmp_path: Path) -> None:
    """And the level above, which has its own reason to answer `False` (no turn in flight)."""
    from shadow_hdk.adapters.agent import ModelAgent, single

    model = Patient()
    thread = await Thread.open(
        agent=ModelAgent(model=cast(Any, model), pattern=single),
        ports=Ports(
            model=cast(Any, model),
            components=(InMemoryComponents([]),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(20, 600, None), Floor(0)),
    )
    try:
        assert await thread.steer("too early") is False
    finally:
        await thread.close()
