"""A child run is judged in its parent's context (BUG-030): the attributes a host put on the run —
the thread, the turn, and above all the **mode** — reach the policy for every step of a child the
run spawns, exactly as they reach the parent's own steps.

Found through the studio: `set_mode("read-only")` changed the thread's mode, `tools/list` said
`run_shell` was refused, and the agent's `run_shell` — a child run, spawned through the offered
registry — appended a file anyway. The child's `RunOptions` carried no context, so the mode
governance fell back to its default, which was the mode the environment was opened in.
"""

from __future__ import annotations

from typing import Any

from pydantic import JsonValue

from shadow_hdk.kernel import Ceiling, Completed, Composition, Floor, Invoke, Lease, Observation
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import Allow, Context, Judgement, Refuse
from shadow_hdk.runtime import Ports, RunOptions, current_run, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)

PARENT = make_registration("parent")
LEAF = make_registration("leaf")
CHILD = Composition((Invoke("l1", LEAF.id),))


class SeesTheMode:
    """Refuses any step judged without a `mode` attribute, and records what it was told."""

    def __init__(self) -> None:
        self.told: list[dict[str, JsonValue]] = []

    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        self.told.append(dict(context.attributes))
        if "mode" not in context.attributes:
            return Refuse("judged with no mode: the parent's context did not reach this step")
        return Allow()


async def spawner(_inputs: JsonValue) -> Observation:
    context = current_run()
    assert context is not None
    _handle, events = await context.children.spawn(CHILD, Ceiling(5, 600, 50))
    return Completed({"child": [e.kind for e in events]})


async def leaf(_inputs: JsonValue) -> Observation:
    return Completed("leaf")


async def test_a_child_step_is_judged_with_the_parents_attributes() -> None:
    policy = SeesTheMode()
    ports = Ports(
        model=None,
        components=(InMemoryComponents([(PARENT, spawner), (LEAF, leaf)]),),
        governance=policy,
        sink=ListSink(),
        clock=FixedClock(),
    )
    options = RunOptions(
        lease=Lease(Ceiling(10, 600, 100), Floor(0)),
        context={"thread": "t1", "turn": "turn-1", "mode": "read-only"},
    )
    events = [e async for e in run(Composition((Invoke("p1", PARENT.id),)), ports, options=options)]
    ended = [e for e in events if e.kind == "ended"]
    assert ended and ended[-1].reason == "completed", [e.kind for e in events]
    leaf_judgements = [t for t in policy.told if t.get("component") == LEAF.id]
    assert leaf_judgements, "the child's step was judged"
    assert leaf_judgements[0].get("mode") == "read-only", leaf_judgements[0]
    assert leaf_judgements[0].get("thread") == "t1" and leaf_judgements[0].get("turn") == "turn-1"
    observed: Any = next(e for e in events if e.kind == "observed" and e.step == "p1").observation
    assert "refused" not in observed.output["child"], observed.output


async def test_a_child_may_still_be_handed_a_context_of_its_own() -> None:
    """The default is inheritance; an explicit `context=` in the overrides wins, as every other
    option's does."""
    policy = SeesTheMode()

    async def spawner_with_own(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        _h, events = await context.children.spawn(
            CHILD, Ceiling(5, 600, 50), context={"mode": "full", "own": True}
        )
        return Completed([e.kind for e in events])

    ports = Ports(
        model=None,
        components=(InMemoryComponents([(PARENT, spawner_with_own), (LEAF, leaf)]),),
        governance=policy,
        sink=ListSink(),
        clock=FixedClock(),
    )
    options = RunOptions(
        lease=Lease(Ceiling(10, 600, 100), Floor(0)), context={"mode": "read-only"}
    )
    [e async for e in run(Composition((Invoke("p1", PARENT.id),)), ports, options=options)]
    leaf_judgements = [t for t in policy.told if t.get("component") == LEAF.id]
    assert leaf_judgements[0].get("mode") == "full" and leaf_judgements[0].get("own") is True
