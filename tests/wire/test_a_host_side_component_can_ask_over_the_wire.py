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
from shadow_hdk.kernel.events import Asked as AskedEvent
from shadow_hdk.kernel.observations import Asked
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
            return Asked(question="over the wire?", handle="h")
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
        assert [e.question for e in parked if isinstance(e, AskedEvent)] == ["over the wire?"]
        assert not [e for e in parked if isinstance(e, Ended)]

        with anyio.fail_after(60):
            await host.resume(PLAN, {"kind": "allow"}, options)  # a judgement, as JSON
        after = list(host.events)

    assert asker.legs == [{"answer": None, "kept": None}, {"answer": Allow(), "kept": {"draft": 3}}]
    done = [e for e in after if e.kind == "observed" and e.step == "s1"]
    assert done[-1].observation == Completed({"from": {"draft": 3}})
    assert [e for e in after if isinstance(e, Ended)][-1].reason == "completed"


async def test_a_live_question_crosses_and_the_hosts_answer_comes_back() -> None:
    """`ask()` (D58): the component is on the host's side; the `Questions` handle is on the
    runtime's side, where the record is. The question crosses, waits, and the judgement returns."""
    import asyncio

    from shadow_hdk.runtime import Questions

    async def asks_live(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        answer = await context.ask("live?")
        return Completed({"answer": answer.kind})

    ports = Ports(
        model=None,
        components=(InMemoryComponents([(ASKER, asks_live)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    questions = Questions()
    options = RunOptions(
        lease=Lease(Ceiling(10, 60, None), Floor(0)), run_id="w2", questions=questions
    )

    async with loopback(ports) as (host, runtime):
        await host.initialize()

        async def answer_it() -> None:
            pending = await asyncio.wait_for(runtime_questions(runtime).next(), 20)
            runtime_questions(runtime).answer(pending.handle, {"kind": "refuse", "reason": "no"})

        # The handle lives runtime-side: the test reaches it there, as a host process would.
        task = asyncio.create_task(answer_it())
        with anyio.fail_after(60):
            await host.run(PLAN, options)
        await task
        after = list(host.events)

    done = [e for e in after if e.kind == "observed" and e.step == "s1"]
    assert done[-1].observation == Completed({"answer": "refuse"})
    assert [e.question for e in after if isinstance(e, AskedEvent)] == ["live?"]


def runtime_questions(runtime: Any) -> Any:
    """The runtime side's `Questions`, where the host process holds it."""
    return runtime.questions
