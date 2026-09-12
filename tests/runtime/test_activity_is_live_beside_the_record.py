"""The record is complete; the activity is live (principle 6, D63).

Everything that *happened* is on the record, once, replayable. Everything that is *happening* — a
token of thinking, a token of text, a line a running command printed, "composing" — is on an
ephemeral stream beside it: delivered to the observer, never on `run()`'s events, never in a
checkpoint, bounded and dropped-oldest so a slow host cannot stall a run (D11). A child run's
activity reaches the root's observer the way its events do.

LangGraph's `custom` stream mode has exactly this shape (ephemeral, written from inside a node,
not checkpointed); ours rides the emitter's observer channel because that already owns the seam
between a run and its host and already forwards child runs.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from shadow_hdk.kernel import (
    Activity,
    Binding,
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Event,
    Floor,
    Invoke,
    Lease,
    Observation,
)
from shadow_hdk.kernel.observations import ApprovalRequest
from shadow_hdk.kernel.ports import Allow, Context, Judgement, ObserverPort
from shadow_hdk.runtime import Ports, RunOptions, current_run, resume, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)

pytestmark = pytest.mark.anyio

WORK = make_registration("work")


class Watching(ObserverPort):
    def __init__(self, slow: float = 0.0) -> None:
        self.events: list[Event] = []
        self.activity: list[Activity] = []
        self.slow = slow

    async def on(self, event: Event) -> None:
        self.events.append(event)

    async def on_activity(self, activity: Activity) -> None:
        if self.slow:
            await asyncio.sleep(self.slow)
        self.activity.append(activity)


class AllowAll:
    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        return Allow()


def ports(observer: ObserverPort, component: Any) -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(WORK, component)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
        observer=observer,
    )


PLAN = Composition((Invoke("s1", "work", (Binding("brief", value="go"),)),))


def options(**kw: Any) -> RunOptions:
    return RunOptions(lease=Lease(Ceiling(10, 60, None), Floor(0)), run_id="a", **kw)


async def test_activity_reaches_the_observer_and_never_the_record() -> None:
    async def talks(_inputs: Any) -> Observation:
        context = current_run()
        assert context is not None
        await context.activity("thinking", "hmm")
        await context.activity("text", "hel")
        await context.activity("text", "lo")
        return Completed("hello")

    watching = Watching()
    events = [e async for e in run(PLAN, ports(watching, talks), options=options())]

    assert [(a.kind, a.text) for a in watching.activity] == [
        ("thinking", "hmm"),
        ("text", "hel"),
        ("text", "lo"),
    ]
    assert all(a.run_id == "a" and a.step == "s1" for a in watching.activity)
    assert not [e for e in events if isinstance(e, Activity)], "activity is not an event"
    assert not [e for e in watching.events if isinstance(e, Activity)]


async def test_activity_is_bounded_and_drops_the_oldest_rather_than_stalling_the_run() -> None:
    from shadow_hdk.runtime.emit import OBSERVER_BACKLOG_MAX

    many = OBSERVER_BACKLOG_MAX * 3

    async def floods(_inputs: Any) -> Observation:
        context = current_run()
        assert context is not None
        for i in range(many):
            await context.activity("text", str(i))
        return Completed("done")

    watching = Watching(slow=0.001)
    async with asyncio.timeout(10):
        events = [e async for e in run(PLAN, ports(watching, floods), options=options())]

    assert events[-1].kind == "ended" and events[-1].reason == "completed"
    seen = [int(a.text) for a in watching.activity]
    assert len(seen) < many, "a slow observer must lose activity, not hold the run"
    assert seen == sorted(seen) and seen[-1] == many - 1, "what survives is the newest, in order"


async def test_activity_is_not_in_the_checkpoint_and_not_replayed_on_resume() -> None:
    legs: list[int] = []

    class Asks:
        async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
            return Allow()

    async def parks(_inputs: Any) -> Observation:
        context = current_run()
        assert context is not None
        legs.append(len(legs))
        back = await context.resumed()
        await context.activity("text", f"leg {len(legs)}")
        if back is None:
            return ApprovalRequest(question="may I?", handle="h")
        return Completed("done")

    saver = InMemorySaver()
    watching = Watching()
    first = [
        e async for e in run(PLAN, ports(watching, parks), options=options(checkpointer=saver))
    ]
    assert not [e for e in first if e.kind == "ended"]
    assert [a.text for a in watching.activity] == ["leg 1"]

    after = Watching()
    [
        e
        async for e in resume(
            PLAN, Allow(), ports(after, parks), options=options(checkpointer=saver)
        )
    ]
    assert [a.text for a in after.activity] == ["leg 2"], "the first leg's activity is gone"


async def test_a_child_runs_activity_reaches_the_roots_observer() -> None:
    from shadow_hdk.runtime.testing import make_registration as reg

    child_plan = Composition((Invoke("c1", "work", (Binding("brief", value="child"),)),))

    async def parent(_inputs: Any) -> Observation:
        context = current_run()
        assert context is not None
        await context.children.spawn(child_plan, Ceiling(3, 60, None))
        return Completed("parent done")

    async def child(_inputs: Any) -> Observation:
        context = current_run()
        assert context is not None
        await context.activity("output", "from the child")
        return Completed("child done")

    watching = Watching()
    both = Ports(
        model=None,
        components=(InMemoryComponents([(reg("parent"), parent), (WORK, child)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
        observer=watching,
    )
    plan = Composition((Invoke("p", "parent", (Binding("brief", value="go"),)),))
    [e async for e in run(plan, both, options=options())]

    assert [(a.kind, a.text, a.step) for a in watching.activity] == [
        ("output", "from the child", "c1")
    ]
    assert watching.activity[0].run_id != "a", "the activity is stamped with the child's run"


async def test_an_observer_without_on_activity_is_left_alone() -> None:
    """Growing the port breaks no adapter (D14): an observer that only knows `on` still works."""

    class OnlyEvents:
        def __init__(self) -> None:
            self.events: list[Event] = []

        async def on(self, event: Event) -> None:
            self.events.append(event)

    async def talks(_inputs: Any) -> Observation:
        context = current_run()
        assert context is not None
        await context.activity("text", "unheard")
        return Completed("ok")

    only = OnlyEvents()
    events = [e async for e in run(PLAN, ports(only, talks), options=options())]
    assert events[-1].kind == "ended" and events[-1].reason == "completed"
    assert only.events
