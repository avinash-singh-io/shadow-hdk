"""A parent that parks does not lose the children it was holding (D37, BUG-015).

**Reproduced before the fix:** a parent spawns a child, parks on an Ask, and resumes with
`children.held == ()`. Its component then spawns a *second* child, and the first is left parked
forever — no handle, no reachable checkpointer, and nobody to send to it or release it. The parent
was not told; it simply found an empty hand and started again.
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Await,
    Ceiling,
    Completed,
    Composition,
    Ended,
    Event,
    Floor,
    Invoke,
    Lease,
    Observation,
    Pending,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import Allow, Ask, Context, Judgement
from shadow_hdk.runtime import Ports, RunOptions, current_run, resume, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)

BRIEF = make_registration("read_the_brief")
MAILBOX = make_registration("mailbox")
PARENT = make_registration("parent")
CHILD = Composition((Invoke("brief", BRIEF.id), Await("inbox", MAILBOX.id)))


async def _brief(_inputs: JsonValue) -> Observation:
    return Completed("read")


async def _waits(_inputs: JsonValue) -> Observation:
    return Pending("inbox")


class AsksOnce:
    def __init__(self, at: str = "p2") -> None:
        self.at, self.asked = at, 0

    async def judge(self, _effects: EffectProfile, context: Context) -> Judgement:
        if context.step == self.at and self.asked == 0:
            self.asked += 1
            return Ask("may it?")
        return Allow()


class Parent:
    """Spawns one child if it is not already holding one — the ordinary shape, and the one that
    silently made a second child."""

    def __init__(self) -> None:
        self.held_each_step: list[tuple[str, ...]] = []
        self.spawns = 0

    async def __call__(self, _inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        if not context.children.held:
            self.spawns += 1
            await context.children.spawn(CHILD, Ceiling(5, 600, 50))
        self.held_each_step.append(context.children.held)
        return Completed(len(context.children.held))


def _ports(parent: Any) -> Ports:
    return Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(BRIEF, _brief), (MAILBOX, _waits), (PARENT, parent)]),),
        governance=AsksOnce(),
        sink=ListSink(),
        clock=FixedClock(),
    )


THREE = Composition(tuple(Invoke(f"p{i}", PARENT.id) for i in range(1, 4)))


def _options(saver: Any) -> RunOptions:
    return RunOptions(
        lease=Lease(Ceiling(30, 600, 1000), Floor(0)), run_id="parent", checkpointer=saver
    )


async def _two_legs(parent: Parent) -> tuple[list[Event], list[Event]]:
    saver = InMemorySaver()
    ports = _ports(parent)
    first = [e async for e in run(THREE, ports, options=_options(saver))]
    after = [e async for e in resume(THREE, "yes", ports, options=_options(saver))]
    return first, after


async def test_a_parent_still_holds_its_child_after_it_parks() -> None:
    parent = Parent()
    first, after = await _two_legs(parent)
    assert not [e for e in first if isinstance(e, Ended)], "the parent parked"
    assert parent.spawns == 1, f"the parent spawned {parent.spawns} children for one job"
    assert parent.held_each_step[-1], "the parent came back holding nothing"


async def test_the_handle_that_comes_back_is_the_one_that_went_in() -> None:
    """Not merely *a* child: the same one, so a message reaches what was already told the brief."""
    parent = Parent()
    await _two_legs(parent)
    handles = {held[0] for held in parent.held_each_step if held}
    assert len(handles) == 1, (
        f"the parent held different children on either side of the park: {handles}"
    )


async def test_a_restored_child_can_still_be_sent_to_and_answers_where_it_slept() -> None:
    """The whole point of holding one: `send` wakes it without re-paying its brief."""
    answered: list[list[Event]] = []

    class SendsAfterThePark(Parent):
        async def __call__(self, _inputs: JsonValue) -> Observation:
            context = current_run()
            assert context is not None
            if not context.children.held:
                self.spawns += 1
                await context.children.spawn(CHILD, Ceiling(5, 600, 50))
            self.held_each_step.append(context.children.held)
            if len(self.held_each_step) > 2:  # after the resume
                answered.append(
                    await context.children.send(context.children.held[0], {"say": "hi"})
                )
            return Completed(None)

    parent = SendsAfterThePark()
    await _two_legs(parent)
    assert answered, "the parent never got to send to the child it was holding"
    ran = [e.step for e in answered[0] if e.kind == "invoked"]
    assert "brief" not in ran, "the child re-read its brief instead of waking where it slept"
    assert "inbox" in ran


async def test_a_child_the_parent_cannot_reach_again_is_reported_not_forgotten() -> None:
    """A child spawned with a checkpointer of its own cannot be rebuilt from the parent's
    checkpoint — an object is not JSON. It is named in `lost` rather than quietly vanishing, so
    the parent can tell *this child is gone* from *I never had one*."""

    class OwnSaver(Parent):
        async def __call__(self, _inputs: JsonValue) -> Observation:
            context = current_run()
            assert context is not None
            if not context.children.held and not context.children.lost:
                self.spawns += 1
                await context.children.spawn(
                    CHILD, Ceiling(5, 600, 50), checkpointer=InMemorySaver()
                )
            self.held_each_step.append(context.children.held)
            return Completed(None)

    parent = OwnSaver()
    await _two_legs(parent)
    assert parent.spawns == 1, "the parent replaced a child it should have been told about"


async def test_a_released_child_does_not_come_back(tmp_path: object) -> None:
    """Restoration reads what the parent is holding *now*, not everything it ever held."""

    class Releases(Parent):
        async def __call__(self, _inputs: JsonValue) -> Observation:
            context = current_run()
            assert context is not None
            if not context.children.held and self.spawns == 0:
                self.spawns += 1
                handle, _ = await context.children.spawn(CHILD, Ceiling(5, 600, 50))
                await context.children.release(handle)
            self.held_each_step.append(context.children.held)
            return Completed(None)

    parent = Releases()
    await _two_legs(parent)
    assert all(held == () for held in parent.held_each_step), parent.held_each_step
