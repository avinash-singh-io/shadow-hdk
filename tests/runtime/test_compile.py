"""Compositions become graphs — the mapping `09` §10 states, asserted one step kind at a time.

`Sequence` becomes edges, `FanOut` becomes `Send`, `Until` becomes a conditional edge with a
counter, and `Ask` becomes `interrupt()`. Nothing here knows what a composition *means*; it knows
what shape it takes.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

from pydantic import JsonValue

from shadow_hdk.kernel import (
    Allow,
    Ask,
    Binding,
    Completed,
    Composition,
    Condition,
    FanOut,
    Invoke,
    Sequence,
    Until,
)
from shadow_hdk.runtime.compile import plan_cache_stats, plan_for
from shadow_hdk.runtime.testing import Judge, make_registration
from tests.runtime.conftest import drive


async def test_one_invoke_runs_one_node() -> None:
    reg = make_registration("search")
    events = await drive(Composition((Invoke("s1", reg.id),)), [(reg, {"hits": 3})])
    assert [(e.kind, e.step) for e in events] == [("invoked", "s1"), ("observed", "s1")]
    assert events[-1].observation == Completed({"hits": 3})


async def test_a_sequence_preserves_order() -> None:
    reg = make_registration("step")
    steps = tuple(Invoke(f"s{i}", reg.id, (Binding("i", value=i),)) for i in range(4))
    events = await drive(Composition((Sequence("seq", steps),)), [(reg, "ok")])
    assert [e.step for e in events if e.kind == "invoked"] == ["s0", "s1", "s2", "s3"]


async def test_a_fan_out_really_runs_in_parallel() -> None:
    """A barrier no sequential implementation can pass: each child waits for the other to arrive.

    Written with a timeout because a sequential compiler would hang here rather than fail, and a
    hang is a worse test than a failure.
    """
    barrier = asyncio.Barrier(3)
    reg = make_registration("slow")

    async def wait_for_siblings(inputs: JsonValue) -> Completed:
        await barrier.wait()
        return Completed(inputs)

    fan = FanOut("fan", tuple(Invoke(f"c{i}", reg.id) for i in range(3)))
    events = await asyncio.wait_for(
        drive(Composition((fan,)), [(reg, wait_for_siblings)]), timeout=5
    )
    assert sorted(e.step for e in events if e.kind == "invoked") == ["c0", "c1", "c2"]
    assert sorted(e.step for e in events if e.kind == "observed") == ["c0", "c1", "c2"]


async def test_until_stops_when_the_condition_is_satisfied() -> None:
    reg = make_registration("try")
    attempts: Iterator[JsonValue] = iter([{"ok": False}, {"ok": False}, {"ok": True}, {"ok": True}])

    async def attempt(_inputs: JsonValue) -> Completed:
        return Completed(next(attempts))

    loop = Until("u", Invoke("body", reg.id), Condition("ok", True), max_iterations=9)
    events = await drive(Composition((loop,)), [(reg, attempt)])
    assert len([e for e in events if e.kind == "invoked"]) == 3


async def test_until_stops_at_its_ceiling_of_iterations() -> None:
    reg = make_registration("try")
    loop = Until("u", Invoke("body", reg.id), Condition("ok", True), max_iterations=4)
    events = await drive(Composition((loop,)), [(reg, {"ok": False})])
    assert len([e for e in events if e.kind == "invoked"]) == 4


async def test_a_nested_composite_runs_in_order() -> None:
    reg = make_registration("step")
    inner = Sequence("inner", (Invoke("a", reg.id), Invoke("b", reg.id)))
    outer = Sequence("outer", (Invoke("first", reg.id), inner, Invoke("last", reg.id)))
    events = await drive(Composition((outer,)), [(reg, "ok")])
    assert [e.step for e in events if e.kind == "invoked"] == ["first", "a", "b", "last"]


async def test_a_later_step_reads_an_earlier_step_s_output() -> None:
    reg = make_registration("step")

    async def echo(inputs: JsonValue) -> Completed:
        return Completed(inputs)

    first = Invoke("s1", reg.id, (Binding("seed", value=7),))
    second = Invoke("s2", reg.id, (Binding("from_s1", ref="s1"),))
    events = await drive(Composition((Sequence("seq", (first, second)),)), [(reg, echo)])
    invoked = {e.step: e.inputs for e in events if e.kind == "invoked"}
    assert invoked["s2"] == {"from_s1": {"seed": 7}}


async def test_a_dangling_reference_does_not_stop_the_composition() -> None:
    reg = make_registration("step")
    bad = Invoke("s1", reg.id, (Binding("x", ref="nowhere"),))
    good = Invoke("s2", reg.id)
    events = await drive(Composition((Sequence("seq", (bad, good)),)), [(reg, "ok")])
    observed = {e.step: e.observation for e in events if e.kind == "observed"}
    assert observed["s1"].kind == "failed"
    assert observed["s2"] == Completed("ok")


async def test_the_same_shape_is_planned_once() -> None:
    reg = make_registration("step")
    shape = Composition((Sequence("seq", (Invoke("s1", reg.id), Invoke("s2", reg.id))),))
    plan_for(shape)
    before = plan_cache_stats()
    for _ in range(5):
        plan_for(shape)
    after = plan_cache_stats()
    assert after["hits"] - before["hits"] == 5
    assert after["misses"] == before["misses"]


async def test_an_ask_parks_the_run_and_a_resume_lets_it_through() -> None:
    reg = make_registration("send")
    events, resume = await drive(
        Composition((Invoke("s1", reg.id),)),
        [(reg, "sent")],
        judge=Judge(lambda e, c: Ask("may it reach the network?")),
        interruptible=True,
    )
    assert [e.kind for e in events] == ["approval_requested"]
    after = await resume(Allow())
    assert [e.kind for e in after] == ["invoked", "observed"]
    assert after[-1].observation == Completed("sent")
