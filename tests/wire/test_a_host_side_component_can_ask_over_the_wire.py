"""`keep` and `resumed` cross (D57): a component on the host's side of the wire asks, the run
parks where the record is, and on resume the host-side component finds the answer and what it
kept — without which an agent over the wire could not surface a tool call's question at all.
"""

from __future__ import annotations

from typing import Any

import anyio
from shadow_hdk.adapters.basic import AllowAll
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Completed,
    Composition,
    Ended,
    Floor,
    Invoke,
    Lease,
    Observation,
)
from shadow_hdk.kernel.events import ApprovalRequested
from shadow_hdk.kernel.observations import ApprovalRequest
from shadow_hdk.kernel.ports import Allow
from shadow_hdk.runtime import Ports, RunOptions, current_run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)
from shadow_hdk.wire.sides import loopback

ASKER = make_registration("asker")
PLAN = Composition((Invoke("s1", "asker", (Binding("brief", value="go"),)),))


class AsksOnce:
    def __init__(self) -> None:
        self.legs: list[dict[str, Any]] = []

    async def __call__(self, _inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        back = await context.resumed()
        self.legs.append(
            {"answer": back.answer if back else None, "kept": back.kept if back else None}
        )
        if back is None:
            await context.keep({"draft": 3})
            return ApprovalRequest(question="over the wire?", handle="h")
        return Completed({"from": back.kept})


async def test_a_host_side_component_asks_and_is_resumed_with_what_it_kept() -> None:
    asker = AsksOnce()
    ports = Ports(
        model=None,
        components=(InMemoryComponents([(ASKER, asker)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    options = RunOptions(lease=Lease(Ceiling(10, 60, None), Floor(0)), run_id="w")

    async with loopback(ports) as (host, _runtime):  # the runtime side owns the checkpointer
        await host.initialize()
        with anyio.fail_after(60):
            await host.run(PLAN, options)
        parked = list(host.events)
        assert [e.question for e in parked if isinstance(e, ApprovalRequested)] == [
            "over the wire?"
        ]
        assert not [e for e in parked if isinstance(e, Ended)]

        with anyio.fail_after(60):
            await host.resume(PLAN, {"kind": "allow"}, options)  # a judgement, as JSON
        after = list(host.events)

    assert asker.legs == [{"answer": None, "kept": None}, {"answer": Allow(), "kept": {"draft": 3}}]
    done = [e for e in after if e.kind == "observed" and e.step == "s1"]
    assert done[-1].observation == Completed({"from": {"draft": 3}})
    assert [e for e in after if isinstance(e, Ended)][-1].reason == "completed"


async def test_a_live_question_crosses_and_the_hosts_answer_comes_back() -> None:
    """`ask()` (D58): the component is on the host's side; the `Approvals` handle is on the
    runtime's side, where the record is. The question crosses, waits, and the judgement returns."""
    import asyncio

    from shadow_hdk.runtime import Approvals

    async def asks_live(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        answer = await context.request_approval(
            "live?", about=("run_shell", {"command": "rm -rf build"})
        )
        return Completed({"answer": answer.kind})

    ports = Ports(
        model=None,
        components=(InMemoryComponents([(ASKER, asks_live)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    questions = Approvals()
    options = RunOptions(
        lease=Lease(Ceiling(10, 60, None), Floor(0)), run_id="w2", approvals=questions
    )

    async with loopback(ports) as (host, runtime):
        await host.initialize()

        seen: list[Any] = []

        async def answer_it() -> None:
            pending = await asyncio.wait_for(runtime_questions(runtime).next(), 20)
            seen.append(pending)
            runtime_questions(runtime).answer(pending.handle, {"kind": "refuse", "reason": "no"})

        # The handle lives runtime-side: the test reaches it there, as a host process would.
        task = asyncio.create_task(answer_it())
        with anyio.fail_after(60):
            await host.run(PLAN, options)
        await task
        after = list(host.events)

    done = [e for e in after if e.kind == "observed" and e.step == "s1"]
    assert done[-1].observation == Completed({"answer": "refuse"})
    asked = [e for e in after if isinstance(e, ApprovalRequested)]
    assert [e.question for e in asked] == ["live?"]
    # What the question is about crosses too (BUG-026): on the pending question and on the record.
    assert (seen[0].component, seen[0].inputs) == ("run_shell", {"command": "rm -rf build"})
    assert (asked[0].component, asked[0].inputs) == ("run_shell", {"command": "rm -rf build"})


async def test_the_agents_own_question_crosses_and_the_text_comes_back() -> None:
    """`request_input` (D65): `ask_person` runs host-side; the `InputRequested` goes on the record
    where it was asked, and the runtime side's handle carries the person's text back."""
    import asyncio

    from shadow_hdk.kernel import Binding, Composition, Invoke
    from shadow_hdk.kernel.events import InputRequested
    from shadow_hdk.runtime.person import person_components

    ports = Ports(
        model=None,
        components=(person_components(),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    options = RunOptions(lease=Lease(Ceiling(10, 60, None), Floor(0)), run_id="w3")
    plan = Composition((Invoke("q1", "ask_person", (Binding("question", value="hue?"),)),))

    async with loopback(ports) as (host, runtime):
        await host.initialize()
        seen: list[Any] = []

        async def answer_it() -> None:
            pending = await asyncio.wait_for(runtime_questions(runtime).next(), 20)
            seen.append(pending)
            runtime_questions(runtime).answer(pending.handle, "purple")

        task = asyncio.create_task(answer_it())
        with anyio.fail_after(60):
            await host.run(plan, options)
        await task
        after = list(host.events)

    assert [e.question for e in after if isinstance(e, InputRequested)] == ["hue?"]
    assert seen[0].kind == "input"
    done = [e for e in after if e.kind == "observed" and e.step == "q1"]
    assert done[-1].observation == Completed({"answer": "purple"})


def runtime_questions(runtime: Any) -> Any:
    """The runtime side's `Approvals`, where the host process holds it."""
    return runtime.approvals
