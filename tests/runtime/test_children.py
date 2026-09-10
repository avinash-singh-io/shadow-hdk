"""Spawn, send, release — a child kept between messages (D16).

A held child is a **parked run**, not a resident object: `spawn` runs it until it parks, `send` is a
`resume` with the message as the answer, and `release` cancels it and settles its lease. `09` §6
says the runtime owns nothing durable and is disposable by design, and a resident child with an
inbox is durable runtime state under another name.

*Without re-paying its brief* is therefore not a feature written here — it is what the checkpoint
already buys, and the test for it is that the child's earlier steps do not run a second time.
"""

from __future__ import annotations

from pydantic import JsonValue

from shadow_hdk.kernel import (
    Await,
    Ceiling,
    Completed,
    Composition,
    Ended,
    Event,
    Floor,
    Held,
    Invoke,
    Lease,
    Observation,
    Observed,
    Pending,
)
from shadow_hdk.runtime import RunContext, RunOptions, current_run, run
from shadow_hdk.runtime.testing import make_registration
from tests.runtime.conftest import ports_over

BRIEF = make_registration("read_the_brief")
MAILBOX = make_registration("mailbox")
PARENT = make_registration("parent", labels=frozenset({"agent"}))


async def _waits(_inputs: JsonValue) -> Observation:
    return Pending("inbox")


CHILD = Composition((Invoke("brief", BRIEF.id), Await("inbox", MAILBOX.id)))


def a_lease(steps: int = 40) -> Lease:
    return Lease(Ceiling(steps, 3600, 10_000), Floor(0))


def _ran(events: list[Event]) -> list[str]:
    return [e.step for e in events if e.kind == "invoked"]


async def _in_a_parent(what: object, *, steps: int = 40) -> tuple[object, list[Event]]:
    """Run `what(context)` inside a step, and give back its answer and the parent's events."""
    box: list[object] = []

    async def call(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        box.append(await what(context))  # type: ignore[operator]
        return Completed(None)

    ports, _ = ports_over([(BRIEF, "brief read"), (MAILBOX, _waits), (PARENT, call)])
    events = [
        e
        async for e in run(
            Composition((Invoke("p1", PARENT.id),)),
            ports,
            options=RunOptions(lease=a_lease(steps)),
        )
    ]
    assert box, "the parent step never ran"
    return box[0], events


async def test_a_child_that_parks_is_held() -> None:
    async def spawn(context: RunContext) -> object:
        handle, events = await context.children.spawn(CHILD, Ceiling(10, 600, 1000))
        # Both steps ran: the `Await` component *is* called, answers `Pending`, and the run
        # parks after it — waiting is a step that happened, not a step that was skipped.
        assert _ran(events) == ["brief", "inbox"], "the child did not get as far as its wait"
        assert not [e for e in events if isinstance(e, Ended)], "a held child has not ended"
        assert handle in context.children.held
        return handle

    handle, parent_events = await _in_a_parent(spawn)
    held = [e for e in parent_events if isinstance(e, Held)]
    assert len(held) == 1, "the parent's record does not say a child is being held"
    assert held[0].handle == handle
    assert held[0].child_run_id == handle
    # What the hold cost, which is the informative half of the event: the brief and the wait.
    assert held[0].steps_spent == 2


async def test_a_send_is_answered_without_re_running_the_childs_earlier_steps() -> None:
    """The whole of *without re-paying its brief*: `brief` ran once, at spawn, and not again."""

    async def spawn_then_send(context: RunContext) -> list[Event]:
        handle, _ = await context.children.spawn(CHILD, Ceiling(10, 600, 1000))
        return await context.children.send(handle, {"say": "hello"})

    answered, _ = await _in_a_parent(spawn_then_send)
    assert isinstance(answered, list)
    assert "brief" not in _ran(answered), (
        "the child re-read its brief instead of waking where it slept"
    )
    inbox = [e for e in answered if isinstance(e, Observed) and e.step == "inbox"]
    assert inbox[-1].observation == Completed({"say": "hello"})


async def test_a_release_ends_the_child_and_forgets_it() -> None:
    async def spawn_then_release(context: RunContext) -> list[Event]:
        handle, _ = await context.children.spawn(CHILD, Ceiling(10, 600, 1000))
        events = await context.children.release(handle)
        assert handle not in context.children.held, "a released child is still being held"
        return events

    events, _ = await _in_a_parent(spawn_then_release)
    assert isinstance(events, list)
    ended = [e for e in events if isinstance(e, Ended)]
    assert ended and ended[-1].reason == "cancelled"


async def test_releasing_one_child_leaves_its_sibling_alone() -> None:
    """Branch granularity. Each child holds its own `Cancellation` (D15) rather than the parent's,
    so letting one go says nothing about the others."""

    async def two_children(context: RunContext) -> list[Event]:
        first, _ = await context.children.spawn(CHILD, Ceiling(10, 600, 1000))
        second, _ = await context.children.spawn(CHILD, Ceiling(10, 600, 1000))
        await context.children.release(first)
        assert second in context.children.held
        return await context.children.send(second, {"say": "still here"})

    answered, _ = await _in_a_parent(two_children)
    assert isinstance(answered, list)
    inbox = [e for e in answered if isinstance(e, Observed) and e.step == "inbox"]
    assert inbox[-1].observation == Completed({"say": "still here"})
    assert [e for e in answered if isinstance(e, Ended)][-1].reason == "completed"


async def test_holding_a_child_costs_the_parent_nothing_while_it_waits() -> None:
    """Measured rather than assumed. A parked child settles what it spent on the way in, so what a
    parent gives up by holding one is the steps the child actually took — not its whole ceiling.
    """

    async def spawn_and_look(context: RunContext) -> tuple[int, int]:
        before = context.remaining().ceiling.max_steps
        await context.children.spawn(CHILD, Ceiling(10, 600, 1000))
        return before, context.remaining().ceiling.max_steps

    seen, _ = await _in_a_parent(spawn_and_look)
    assert isinstance(seen, tuple)
    before, after = seen
    spent = before - after
    assert spent == 2, f"holding a child cost {spent} steps, not the two it took"
    assert spent < 10, "the parent gave up the child ceiling rather than what the child spent"
