"""The event stream, folded into what a person reads as agent steps (D46).

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

from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from shadow_hdk.kernel.events import (
    Asked,
    Event,
    Invoked,
    Observed,
    Reasoned,
    Refused,
    RunId,
    Spawned,
    Spent,
    StepId,
)
from shadow_hdk.kernel.observations import Observation
from shadow_hdk.kernel.ports import Usage

Outcome = Literal["running", "completed", "refused", "asked", "failed", "pending", "acted"]


@dataclass(frozen=True)
class Step:
    """One thing the agent did, with what it thought first and what it cost.

    `children` are the steps of every run spawned while this step was executing, in order, each
    with children of its own. `observation` is the whole observation — a projection is not the
    place to summarise; the offloading rule (Group 4) is where size is handled, before it gets here.
    """

    run_id: RunId
    step: StepId
    component: str | None = None
    reasoning: str = ""
    outcome: Outcome = "running"
    observation: Observation | None = None
    reason: str | None = None
    """A refusal's reason, or a question's text."""
    usage: Usage | None = None
    at: str | None = None
    children: tuple[Step, ...] = ()


@dataclass
class _Open:
    """A step still being folded. Mutable on purpose; frozen once it is handed out."""

    run_id: RunId
    step: StepId
    component: str | None = None
    reasoning: list[str] = field(default_factory=list)
    outcome: Outcome = "running"
    observation: Observation | None = None
    reason: str | None = None
    usage: Usage | None = None
    at: str | None = None
    children: list[Step] = field(default_factory=list)

    def frozen(self) -> Step:
        return Step(
            run_id=self.run_id,
            step=self.step,
            component=self.component,
            reasoning="".join(self.reasoning),
            outcome=self.outcome,
            observation=self.observation,
            reason=self.reason,
            usage=self.usage,
            at=self.at,
            children=tuple(self.children),
        )


def _outcome_of(observation: Observation) -> Outcome:
    kind = getattr(observation, "kind", "completed")
    return (
        kind
        if kind in ("completed", "refused", "asked", "failed", "pending", "acted")
        else "completed"
    )  # type: ignore[return-value]


class Fold:
    """The state of a fold in progress — what `steps` and `run_steps` share.

    `parent_of` maps a child run to (parent run, parent step) from its `Spawned`; `current` is the
    step each run is executing; `finished` collects top-level steps as they close.
    """

    def __init__(self) -> None:
        self.open: dict[tuple[RunId, StepId], _Open] = {}
        self.current: dict[RunId, StepId] = {}
        self.parent_of: dict[RunId, tuple[RunId, StepId]] = {}
        self.finished: list[Step] = []
        self.order: list[tuple[RunId, StepId]] = []

    def _step(self, run_id: RunId, step: StepId) -> _Open:
        key = (run_id, step)
        if key not in self.open:
            self.open[key] = _Open(run_id=run_id, step=step)
            self.order.append(key)
        self.current[run_id] = step
        return self.open[key]

    def feed(self, event: Event) -> list[Step]:
        """Fold one event; return any top-level steps that just closed."""
        closed: list[Step] = []
        match event:
            case Reasoned():
                self._step(event.run_id, event.step).reasoning.append(event.text)
            case Invoked():
                opened = self._step(event.run_id, event.step)
                opened.component = event.component
                opened.at = event.at
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
            case Asked():
                opened = self._step(event.run_id, event.step)
                opened.outcome = "asked"
                opened.reason = event.question
                closed += self._close(event.run_id, event.step)
            case Spent():
                if (key := (event.run_id, event.step)) in self.open:
                    self.open[key].usage = event.usage
                else:
                    self._late_usage(event)
            case Spawned():
                if (parent_step := self.current.get(event.run_id)) is not None:
                    self.parent_of[event.child_run_id] = (event.run_id, parent_step)
        return closed

    def _late_usage(self, event: Spent) -> None:
        """`Spent` arrives after `Observed` closed the step. Attach it to the frozen step wherever
        it ended up — top level or under a parent — by rebuilding that one entry."""
        for i, done in enumerate(self.finished):
            if (done.run_id, done.step) == (event.run_id, event.step):
                self.finished[i] = replace(done, usage=event.usage)
                return
        for opened in self.open.values():
            for j, child in enumerate(opened.children):
                if (child.run_id, child.step) == (event.run_id, event.step):
                    opened.children[j] = replace(child, usage=event.usage)
                    return

    def _close(self, run_id: RunId, step: StepId) -> list[Step]:
        done = self.open.pop((run_id, step)).frozen()
        self.order.remove((run_id, step))
        if (parent := self.parent_of.get(run_id)) is not None:
            parent_run, parent_step = parent
            if (parent_run, parent_step) in self.open:
                self.open[(parent_run, parent_step)].children.append(done)
                return []
        self.finished.append(done)
        return [done]

    def drain(self) -> list[Step]:
        """Everything, closed or still running, in the order it started. For a stream that ended."""
        still_open = [self.open[key].frozen() for key in self.order]
        return [*self.finished, *[s for s in still_open if s.run_id not in self.parent_of]]


def steps(events: Iterable[Event]) -> list[Step]:
    """Every top-level step in a recorded stream, children nested, running ones last."""
    fold = Fold()
    for event in events:
        fold.feed(event)
    return fold.drain()


async def run_steps(events: AsyncIterator[Event]) -> AsyncIterator[Step]:
    """The same fold over a live stream, yielding each top-level step as it closes.

    Takes the event iterator `run(...)` returns, so a host that wants both the record and the
    steps tees the one stream rather than running twice.
    """
    fold = Fold()
    async for event in events:
        for done in fold.feed(event):
            yield done


def as_json(step: Step) -> dict[str, Any]:
    """The projection, as a client on the wire receives it."""
    from shadow_hdk.kernel.contracts import adapter_for

    dumped: dict[str, Any] = adapter_for(Step).dump_python(step, mode="json")
    return dumped


__all__ = ["Fold", "Outcome", "Step", "as_json", "run_steps", "steps"]
