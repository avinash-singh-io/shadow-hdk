"""The host itself: hand everything in, run the brief, answer what is asked, keep the record."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from pathlib import Path

from examples.host.brains import AT, Brain
from examples.host.ledger import Ledger
from examples.host.policy import Policy
from examples.host.view import lines_for, thought
from shadow_hdk.adapters.basic import SystemClock
from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.kernel import ApprovalRequested, Ceiling, Ended, Event, Floor, Lease, Reasoning
from shadow_hdk.kernel.ports import Judgement
from shadow_hdk.runtime import Ports, RunOptions, resume, run
from shadow_hdk.runtime.environment import Mode
from shadow_hdk.runtime.items import run_items


@dataclass
class Outcome:
    """What the host holds when the run stops — finished, or parked on a question."""

    run_id: str
    events: list[Event] = field(default_factory=list)
    ledger: Ledger = field(default_factory=Ledger)
    question: str | None = None
    """Set when the run is parked: the policy asked, and nobody answered. Resume with
    `host(..., run_id=outcome.run_id, answer=Allow())` — from this process or the next one."""
    ended: str | None = None


Answer = Callable[[str], Judgement | None]


async def host(
    brief: str,
    *,
    root: Path,
    brain: Brain,
    store: Path,
    mode: Mode = "workspace-write",
    on_line: Callable[[str], None] = print,
    answer: Answer | None = None,
    run_id: str | None = None,
    resume_with: Judgement | None = None,
) -> Outcome:
    """Run `brief` through `brain`, everything the host owns handed in.

    `answer` is called with each question the policy raises; return a judgement to continue in
    this call, or `None` to leave the run parked in `store`. `resume_with` continues a run parked
    earlier — `run_id` names it and `store` is the same file.
    """
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    root.mkdir(parents=True, exist_ok=True)
    store.parent.mkdir(parents=True, exist_ok=True)
    environment = await LocalEnvironment.open(root, mode=mode, at=AT)
    policy, ledger = Policy(allow_network=brain.reaches), Ledger()
    ports = Ports(
        model=brain.model,
        components=(environment, *brain.components),
        governance=policy,
        sink=ledger,
        clock=SystemClock(),
        observer=None,
    )
    outcome = Outcome(run_id=run_id or f"host-{uuid.uuid4().hex[:8]}", ledger=ledger)
    lease = Lease(Ceiling(max_steps=60, max_wall_seconds=600, max_cost_cents=200), Floor(0))

    async with AsyncSqliteSaver.from_conn_string(str(store)) as saver:
        options = RunOptions(lease=lease, run_id=outcome.run_id, checkpointer=saver)
        events = (
            resume(brain.plan, resume_with, ports, options=options)
            if resume_with is not None
            else run(brain.plan, ports, options=options)
        )
        while True:
            question = await _render(events, outcome, on_line)
            if question is None:
                break
            judgement = answer(question) if answer is not None else None
            if judgement is None:
                outcome.question = question
                break
            events = resume(brain.plan, judgement, ports, options=options)
    await environment.close()
    return outcome


async def _render(
    events: AsyncIterator[Event], outcome: Outcome, on_line: Callable[[str], None]
) -> str | None:
    """Render steps as they close; keep every event; say what was asked, if anything."""
    question: str | None = None

    async def tapped() -> AsyncIterator[Event]:
        nonlocal question
        async for event in events:
            outcome.events.append(event)
            if isinstance(event, Reasoning):
                # What it thought, as it thinks it — not when the step it belongs to closes.
                on_line(thought(event.text, depth=0 if event.run_id == outcome.run_id else 1))
            if isinstance(event, ApprovalRequested):
                question = event.question
            if isinstance(event, Ended) and event.run_id == outcome.run_id:
                outcome.ended = event.reason
            yield event

    async for step in run_items(tapped(), nested=True):
        for line in lines_for(step, depth=1 if step.parent else 0, tree=False):
            on_line(line)
    return question


__all__ = ["Answer", "Outcome", "host"]
