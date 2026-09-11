"""The event stream, folded into what a person reads as agent steps (D46).

Twelve raw kinds are the record. Nobody renders the record; every client renders **steps** — this is
what it thought, this is what it reached for, this is what came back, this sub-agent went off and
did that, this was refused, this cost that. A projection is that fold, done once, in the runtime,
as a pure function over any event iterable — a live run or a stored record — so no host derives it
and no two hosts derive it differently.

It is generic. A browser agent's steps, a coding agent's steps and a device's steps fold the same
way, because the events do.

**Nesting is by run id.** A `Spawned` in a parent's stream names a child run; the child's events
arrive in the same stream (Phase 7) and fold under the parent step that was executing when the
child was spawned. Depth is unbounded and nothing about it is special.
"""

from __future__ import annotations

from typing import Any

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Ended,
    Event,
    Floor,
    Invoked,
    Lease,
    Observed,
    Reasoned,
    Spawned,
    Spent,
    Started,
)
from shadow_hdk.kernel.events import Asked, Refused
from shadow_hdk.kernel.ports import Usage
from shadow_hdk.runtime.steps import Step, steps

LEASE = Lease(Ceiling(10, 60, 100), Floor(0))


def a_stream() -> list[Event]:
    """A parent that thinks, calls a tool, spawns a child that calls a tool, then is refused."""
    p, c = "parent", "child"
    return [
        Started(run_id=p, seq=1, at="t1", lease=LEASE),
        Reasoned(run_id=p, seq=2, at="t2", step="lead", text="check the handbook"),
        Invoked(run_id=p, seq=3, at="t3", step="lead", component="agent", inputs={}),
        Spawned(run_id=p, seq=4, at="t4", child_run_id=c, lease=LEASE),
        Started(run_id=c, seq=1, at="t5", lease=LEASE),
        Reasoned(run_id=c, seq=2, at="t6", step="look", text="the handbook lists it"),
        Invoked(run_id=c, seq=3, at="t7", step="look", component="look_up", inputs={"topic": "x"}),
        Observed(run_id=c, seq=4, at="t8", step="look", observation=Completed({"mass": 12})),
        Spent(run_id=c, seq=5, at="t9", step="look", usage=Usage(10, 5, 2)),
        Ended(run_id=c, seq=6, at="t10", reason="completed", steps_taken=1),
        Observed(run_id=p, seq=5, at="t11", step="lead", observation=Completed({"answer": 12})),
        Spent(run_id=p, seq=6, at="t12", step="lead", usage=Usage(100, 40, 5)),
        Invoked(run_id=p, seq=7, at="t13", step="wipe", component="rm", inputs={}),
        Refused(run_id=p, seq=8, at="t14", step="wipe", reason="mode 'looking' permits no writes"),
        Invoked(run_id=p, seq=9, at="t15", step="publish", component="post", inputs={}),
        Asked(run_id=p, seq=10, at="t16", step="publish", question="publish it?", handle="h1"),
    ]


def test_each_step_is_one_thing_the_agent_did() -> None:
    folded = steps(a_stream())

    assert [s.step for s in folded] == ["lead", "wipe", "publish"]


def test_a_step_carries_what_it_thought_and_what_it_reached_for() -> None:
    lead = steps(a_stream())[0]

    assert lead.reasoning == "check the handbook"
    assert lead.component == "agent"
    assert lead.outcome == "completed"
    assert lead.usage == Usage(100, 40, 5)


def test_a_refusal_is_a_step_with_its_reason() -> None:
    wipe = steps(a_stream())[1]

    assert wipe.outcome == "refused"
    assert wipe.reason == "mode 'looking' permits no writes"


def test_a_question_is_a_step_still_waiting() -> None:
    publish = steps(a_stream())[2]

    assert publish.outcome == "asked"
    assert publish.reason == "publish it?"


def test_a_child_folds_under_the_step_that_spawned_it() -> None:
    """The screenshot every host wants: the sub-agent's steps nested under the parent's."""
    lead = steps(a_stream())[0]

    assert len(lead.children) == 1
    child = lead.children[0]
    assert child.run_id == "child"
    assert child.step == "look"
    assert child.reasoning == "the handbook lists it"
    assert child.outcome == "completed"
    assert child.usage == Usage(10, 5, 2)


def test_the_fold_is_pure_and_total() -> None:
    """Twice over the same events gives the same steps, and a stream cut short still folds — a
    step with no outcome yet is *running*, not an error."""
    partial = a_stream()[:3]

    assert steps(a_stream()) == steps(a_stream())
    assert steps(partial)[0].outcome == "running"


def test_a_step_folds_reasoning_that_arrived_in_pieces() -> None:
    p = "r"
    pieces: list[Event] = [
        Started(run_id=p, seq=1, at="t", lease=LEASE),
        Reasoned(run_id=p, seq=2, at="t", step="s", text="the "),
        Reasoned(run_id=p, seq=3, at="t", step="s", text="lathe"),
        Invoked(run_id=p, seq=4, at="t", step="s", component="c", inputs={}),
    ]

    assert steps(pieces)[0].reasoning == "the lathe"


def test_a_step_is_data_a_client_can_serialise() -> None:
    """It goes over SSE next; a step that could not be dumped would be a projection nobody can
    render."""
    from shadow_hdk.kernel.contracts import round_trip

    lead = steps(a_stream())[0]

    assert isinstance(lead, Step)
    assert round_trip(lead, Step) == lead


async def _replayed(events: list[Event]) -> Any:
    for event in events:
        yield event


async def test_a_host_can_watch_every_step_close_as_it_closes() -> None:
    """`run_steps` yields a top-level step when it closes — and an orchestrator's step closes at
    the very end, after every sub-agent's step it nested. A host rendering "agent steps" live saw
    nothing for the whole run. `nested=True` yields **every** step as it closes, the child's before
    the parent's, each naming its parent so a client can hang it where it belongs."""
    from shadow_hdk.runtime.steps import run_steps

    seen = [step async for step in run_steps(_replayed(a_stream()), nested=True)]

    assert [(s.run_id, s.step) for s in seen] == [
        ("child", "look"),
        ("parent", "lead"),
        ("parent", "wipe"),
        ("parent", "publish"),
    ]
    assert seen[0].parent == ("parent", "lead")
    assert [s.parent for s in seen[1:]] == [None, None, None]
    # The parent, when it closes, still carries the child — the tree is intact for a late reader.
    assert seen[1].children[0].step == "look"

    default = [step async for step in run_steps(_replayed(a_stream()))]
    assert [(s.run_id, s.step) for s in default] == [
        ("parent", "lead"),
        ("parent", "wipe"),
        ("parent", "publish"),
    ], "the default changed"
