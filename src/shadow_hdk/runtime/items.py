"""The event stream, folded into the items a host renders (D46, D61).

An item is what Codex, the Responses API and every agent UI call the unit a person sees: a tool
call with its result, a refusal, a question, its reasoning and its cost. The kernel plans in
`Item`s; a host reads `Item`s.

Twelve raw kinds are the record. Nobody renders the record; every client renders **steps**: this is
what it thought, this is what it reached for, this is what came back, this sub-agent went off and
did that, this was refused, this cost that. The fold is done once, here, as a pure function over
any event iterable — a live run or a stored record — so no host derives it and no two hosts derive
it differently.

It is generic. A browser agent's steps, a coding agent's steps and a device's steps fold the same
way, because the events do.

**Nesting is by run id.** A `Spawned` in a parent's stream names a child run; the child's events
arrive in the same stream (Phase 7) and fold under the parent step that was executing when the
child was spawned. Depth is unbounded and nothing about it is special.

**A step with no outcome yet is running, not an error.** A stream cut short — a run still going, a
record that ends mid-step — still folds; the last step says `running`.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from pydantic import JsonValue

from shadow_hdk.kernel.composition import StepId
from shadow_hdk.kernel.events import (
    ApprovalRequested,
    EffectRecorded,
    Event,
    InputRequested,
    Invoked,
    Observed,
    PlanAdmitted,
    PlanRefused,
    Reasoning,
    Refused,
    RunId,
    Spawned,
    UsageReported,
)
from shadow_hdk.kernel.observations import Observation
from shadow_hdk.kernel.ports import Usage

Outcome = Literal[
    "running",
    "completed",
    "refused",
    "approval_requested",
    "input_requested",
    "failed",
    "pending",
    "acted",
]

ITEM_INPUT_BYTES = 64 * 1024
"""Maximum canonical JSON size duplicated into an Item projection.

The authoritative ``Invoked`` event retains the whole value. An item is a render projection and
can be emitted repeatedly on live/client surfaces, so a larger input becomes one explicit marker
instead of an ambiguous string cut or an unbounded second copy.
"""


@dataclass(frozen=True)
class Item:
    """One thing the agent did, with what it thought first and what it cost.

    `children` are the steps of every run spawned while this step was executing, in order, each
    with children of its own. `observation` is the whole observation — a projection is not the
    place to summarise; the offloading rule (Group 4) is where size is handled, before it gets here.
    """

    run_id: RunId
    step: StepId
    component: str | None = None
    inputs: JsonValue = None
    """Canonical inputs, or a typed JSON omission marker when the projection is too large."""
    reasoning: str = ""
    effect: EffectRecorded | None = None
    plan: PlanAdmitted | PlanRefused | None = None
    """The latest plan event of this step (D108): a plan proposed here and admitted or refused,
    with its digest and every mismatch — what a host renders as *planned* beside what ran."""
    """The latest public transaction fact for this step, when it crossed an effect boundary."""
    outcome: Outcome = "running"
    observation: Observation | None = None
    reason: str | None = None
    """A refusal's reason, or a question's text."""
    usage: Usage | None = None
    at: str | None = None
    children: tuple[Item, ...] = ()
    parent: tuple[RunId, StepId] | None = None
    """The step whose run spawned this one, for a client hanging steps where they belong as they
    close (`run_steps(nested=True)`); `None` at the top."""


@dataclass
class _Open:
    """A step still being folded. Mutable on purpose; frozen once it is handed out."""

    run_id: RunId
    step: StepId
    component: str | None = None
    inputs: JsonValue = None
    reasoning: list[str] = field(default_factory=list)
    effect: EffectRecorded | None = None
    plan: PlanAdmitted | PlanRefused | None = None
    outcome: Outcome = "running"
    observation: Observation | None = None
    reason: str | None = None
    usage: Usage | None = None
    at: str | None = None
    children: list[Item] = field(default_factory=list)
    parent: tuple[RunId, StepId] | None = None

    def frozen(self) -> Item:
        return Item(
            run_id=self.run_id,
            step=self.step,
            component=self.component,
            inputs=self.inputs,
            reasoning="".join(self.reasoning),
            effect=self.effect,
            plan=self.plan,
            outcome=self.outcome,
            observation=self.observation,
            reason=self.reason,
            usage=self.usage,
            at=self.at,
            children=tuple(self.children),
            parent=self.parent,
        )


def _outcome_of(observation: Observation) -> Outcome:
    kind = getattr(observation, "kind", "completed")
    named: dict[str, Outcome] = {
        "completed": "completed",
        "refused": "refused",
        "approval_request": "approval_requested",
        "input_request": "input_requested",
        "failed": "failed",
        "pending": "pending",
        "acted": "acted",
    }
    return named.get(kind, "completed")


class Fold:
    """The state of a fold in progress — what `steps` and `run_steps` share.

    `parent_of` maps a child run to (parent run, parent step) from its `Spawned`; `current` is the
    step each run is executing; `finished` collects top-level steps as they close.
    """

    def __init__(self) -> None:
        self.open: dict[tuple[RunId, StepId], _Open] = {}
        self.current: dict[RunId, StepId] = {}
        self.parent_of: dict[RunId, tuple[RunId, StepId]] = {}
        self.finished: list[Item] = []
        self.order: list[tuple[RunId, StepId]] = []
        self.closed_now: list[Item] = []
        """Every step the last `feed` closed, nested or not — what a live host renders."""
        self._waiting: dict[tuple[RunId, StepId], Item] = {}
        """Steps that closed on a question — an approval or an input — and may be answered."""

    def _step(self, run_id: RunId, step: StepId) -> _Open:
        key = (run_id, step)
        if key not in self.open:
            self.open[key] = self._reopened(key) or _Open(run_id=run_id, step=step)
            self.order.append(key)
        self.current[run_id] = step
        return self.open[key]

    def _reopened(self, key: tuple[RunId, StepId]) -> _Open | None:
        """A step that closed on a question and now hears more is the same step, answered
        (D38: it resumes where it parked; nothing invokes it twice). The waiting item was handed
        out so a live host could render it; it comes back out of the finished list — one step is
        one item — and the reopened fold keeps what the invocation said (BUG-040)."""
        waited = self._waiting.pop(key, None)
        if waited is None:
            return None
        self.finished = [done for done in self.finished if (done.run_id, done.step) != key]
        for opened in self.open.values():
            opened.children = [c for c in opened.children if (c.run_id, c.step) != key]
        return _Open(
            run_id=waited.run_id,
            step=waited.step,
            component=waited.component,
            inputs=waited.inputs,
            reasoning=[waited.reasoning] if waited.reasoning else [],
            effect=waited.effect,
            usage=waited.usage,
            at=waited.at,
            children=list(waited.children),
        )

    def feed(self, event: Event) -> list[Item]:
        """Fold one event; return any top-level steps that just closed. `closed_now` holds every
        step that closed, a nested one included."""
        closed: list[Item] = []
        self.closed_now = []
        match event:
            case Reasoning():
                self._step(event.run_id, event.step).reasoning.append(event.text)
            case Invoked():
                opened = self._step(event.run_id, event.step)
                opened.component = event.component
                opened.inputs = _project_inputs(event.inputs)
                opened.at = event.at
            case EffectRecorded():
                self._step(event.run_id, event.step).effect = event
            case PlanAdmitted() | PlanRefused():
                # **A plan event opens no step.** It names the step it was proposed in — which
                # may be a child's call id when a resident CLI proposed it through the offer —
                # so it attaches to that step if it is open here, else to the run's current one;
                # an item is a step, and a plan is a fact about one.
                key = (event.run_id, event.step)
                if key in self.open:
                    self.open[key].plan = event
                elif (current := self.current.get(event.run_id)) is not None:
                    self.open[(event.run_id, current)].plan = event
            case Observed():
                opened = self._step(event.run_id, event.step)
                opened.observation = event.observation
                opened.outcome = _outcome_of(event.observation)
                closed += self._close(event.run_id, event.step)
            case Refused():
                opened = self._step(event.run_id, event.step)
                opened.outcome = "refused"
                opened.reason = event.reason
                closed += self._close(event.run_id, event.step)
            case ApprovalRequested():
                opened = self._step(event.run_id, event.step)
                opened.outcome = "approval_requested"
                opened.reason = event.question
                closed += self._close(event.run_id, event.step)
            case InputRequested():
                opened = self._step(event.run_id, event.step)
                opened.outcome = "input_requested"
                opened.reason = event.question
                closed += self._close(event.run_id, event.step)
            case UsageReported():
                if (key := (event.run_id, event.step)) in self.open:
                    self.open[key].usage = event.usage
                else:
                    self._late_usage(event)
            case Spawned():
                if (parent_step := self.current.get(event.run_id)) is not None:
                    self.parent_of[event.child_run_id] = (event.run_id, parent_step)
        return closed

    def _late_usage(self, event: UsageReported) -> None:
        """`UsageReported` arrives after `Observed` closed the step. Attach it to the frozen step
        wherever it ended up — top level or under a parent — by rebuilding that one entry."""
        for i, done in enumerate(self.finished):
            if (done.run_id, done.step) == (event.run_id, event.step):
                self.finished[i] = replace(done, usage=event.usage)
                return
        for opened in self.open.values():
            for j, child in enumerate(opened.children):
                if (child.run_id, child.step) == (event.run_id, event.step):
                    opened.children[j] = replace(child, usage=event.usage)
                    return

    def _close(self, run_id: RunId, step: StepId) -> list[Item]:
        opened = self.open.pop((run_id, step))
        opened.parent = self.parent_of.get(run_id)
        done = opened.frozen()
        self.order.remove((run_id, step))
        self.closed_now.append(done)
        if done.outcome in ("approval_requested", "input_requested"):
            self._waiting[(run_id, step)] = done
        if (parent := self.parent_of.get(run_id)) is not None:
            parent_run, parent_step = parent
            if (parent_run, parent_step) in self.open:
                self.open[(parent_run, parent_step)].children.append(done)
                return []
        self.finished.append(done)
        return [done]

    def drain(self) -> list[Item]:
        """Everything, closed or still running, in the order it started. For a stream that ended."""
        still_open = [self.open[key].frozen() for key in self.order]
        return [*self.finished, *[s for s in still_open if s.run_id not in self.parent_of]]


def items(events: Iterable[Event]) -> list[Item]:
    """Every top-level step in a recorded stream, children nested, running ones last."""
    fold = Fold()
    for event in events:
        fold.feed(event)
    return fold.drain()


async def run_items(events: AsyncIterator[Event], *, nested: bool = False) -> AsyncIterator[Item]:
    """The same fold over a live stream, yielding each top-level step as it closes.

    Takes the event iterator `run(...)` returns, so a host that wants both the record and the
    steps tees the one stream rather than running twice.

    `nested=True` yields **every** step as it closes, a sub-agent's before the step that spawned
    it, each with `parent` set — because an orchestrator's own step closes last, and a host that
    waited for it rendered nothing for the whole run.
    """
    fold = Fold()
    async for event in events:
        top = fold.feed(event)
        for done in fold.closed_now if nested else top:
            yield done


def _project_inputs(value: JsonValue) -> JsonValue:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    if len(encoded) <= ITEM_INPUT_BYTES:
        return value
    return {
        "$shadow": {
            "kind": "omitted",
            "reason": "too_large",
            "bytes": len(encoded),
        }
    }


def as_json(item: Item) -> dict[str, Any]:
    """The projection, as a client on the wire receives it."""
    from shadow_hdk.kernel.contracts import adapter_for

    dumped: dict[str, Any] = adapter_for(Item).dump_python(item, mode="json")
    return dumped


__all__ = ["ITEM_INPUT_BYTES", "Fold", "Item", "Outcome", "as_json", "items", "run_items"]
