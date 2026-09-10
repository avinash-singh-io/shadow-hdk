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


def _ports(parent: Any, asks_at: str = "p2") -> Ports:
    return Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(BRIEF, _brief), (MAILBOX, _waits), (PARENT, parent)]),),
        governance=AsksOnce(asks_at),
        sink=ListSink(),
        clock=FixedClock(),
    )


THREE = Composition(tuple(Invoke(f"p{i}", PARENT.id) for i in range(1, 4)))


def _options(saver: Any) -> RunOptions:
    return RunOptions(
        lease=Lease(Ceiling(30, 600, 1000), Floor(0)), run_id="parent", checkpointer=saver
    )


async def _two_legs(parent: Parent, asks_at: str = "p2") -> tuple[list[Event], list[Event]]:
    saver = InMemorySaver()
    ports = _ports(parent, asks_at)
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
    checkpoint — an object is not JSON. It is named in `lost`, with the reason, rather than
    quietly vanishing: the parent can then tell *this child is gone* from *I never had one*."""

    class OwnSaver(Parent):
        def __init__(self) -> None:
            super().__init__()
            self.lost_seen: list[tuple[str, ...]] = []
            self.reasons: list[str] = []

        async def __call__(self, _inputs: JsonValue) -> Observation:
            context = current_run()
            assert context is not None
            if not context.children.held and not context.children.lost:
                self.spawns += 1
                await context.children.spawn(
                    CHILD, Ceiling(5, 600, 50), checkpointer=InMemorySaver()
                )
            self.held_each_step.append(context.children.held)
            self.lost_seen.append(context.children.lost)
            self.reasons.extend(context.children.why_lost(h) for h in context.children.lost)
            return Completed(None)

    parent = OwnSaver()
    await _two_legs(parent)
    assert parent.spawns == 1, "the parent replaced a child it should have been told about"
    assert parent.lost_seen[0] == (), "nothing was lost before the park"
    assert parent.lost_seen[-1], "the parent was never told the child was unreachable"
    assert parent.held_each_step[-1] == (), "an unreachable child was reported as held"
    assert parent.lost_seen[-1][0] == parent.held_each_step[0][0], "a different child was reported"
    assert any("checkpointer of its own" in reason for reason in parent.reasons), parent.reasons


async def test_a_child_released_after_an_earlier_step_recorded_it_stays_released() -> None:
    """The headstone. Each step writes what the run holds *then*, and the reducer merges — so
    without a `None` for a released handle, the earlier step's record still says *held* and the
    child comes back from the dead on resume.

    What is asserted is what the parent held **on entry** to the resumed step. Asserting the end
    state proved nothing: a resurrected child was simply released a second time, and the hand was
    empty again by the time anyone looked.
    """

    class SpawnsThenReleases(Parent):
        def __init__(self) -> None:
            super().__init__()
            self.held_on_entry: list[tuple[str, ...]] = []

        async def __call__(self, _inputs: JsonValue) -> Observation:
            context = current_run()
            assert context is not None
            self.held_on_entry.append(context.children.held)
            if self.spawns == 0:
                self.spawns += 1
                await context.children.spawn(CHILD, Ceiling(5, 600, 50))
            elif context.children.held:
                await context.children.release(context.children.held[0])
            self.held_each_step.append(context.children.held)
            return Completed(None)

    parent = SpawnsThenReleases()
    # The pause lands **after** the release, which is the only arrangement where the headstone
    # matters: an earlier step's record still says *held*, and the reducer keeps it.
    await _two_legs(parent, asks_at="p3")
    assert parent.held_on_entry[1] == (parent.held_each_step[0][0],), "p2 should have found it"
    assert parent.held_on_entry[-1] == (), "a released child came back from the dead after the park"


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


async def test_a_child_that_ended_on_a_send_does_not_come_back_either() -> None:
    """A child can leave the hand two ways: released, or finished while being sent to. Both need
    the headstone, or an earlier step's record resurrects a run that has already ended — and the
    parent comes back believing it holds something that finished."""
    answers: list[Observation] = [Pending("inbox"), Completed("done")]

    async def _pends_then_finishes(_inputs: JsonValue) -> Observation:
        return answers.pop(0) if len(answers) > 1 else answers[0]

    class SpawnsThenSendsUntilItEnds(Parent):
        def __init__(self) -> None:
            super().__init__()
            self.held_on_entry: list[tuple[str, ...]] = []

        async def __call__(self, _inputs: JsonValue) -> Observation:
            context = current_run()
            assert context is not None
            self.held_on_entry.append(context.children.held)
            if self.spawns == 0:
                self.spawns += 1
                await context.children.spawn(CHILD, Ceiling(5, 600, 50))
            elif context.children.held:
                await context.children.send(context.children.held[0], {"say": "finish"})
            self.held_each_step.append(context.children.held)
            return Completed(None)

    parent = SpawnsThenSendsUntilItEnds()
    saver = InMemorySaver()
    ports = Ports(
        model=ScriptedModel(),
        components=(
            InMemoryComponents(
                [(BRIEF, _brief), (MAILBOX, _pends_then_finishes), (PARENT, parent)]
            ),
        ),
        governance=AsksOnce("p3"),
        sink=ListSink(),
        clock=FixedClock(),
    )
    [e async for e in run(THREE, ports, options=_options(saver))]
    [e async for e in resume(THREE, "yes", ports, options=_options(saver))]
    assert parent.held_on_entry[1], "p2 should have found the child it spawned"
    assert parent.held_each_step[1] == (), "the child ended on the send, so it is no longer held"
    assert parent.held_on_entry[-1] == (), "a child that had ended came back after the park"
