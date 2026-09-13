"""Approval and input requests, answered by the host while a step waits (D58, D61).

D57 parks the run on a component's question and resumes it with the answer — the right shape when
the run can stop. It cannot always stop: a step holding a **provider's session** open is what
keeps that provider alive, and a tool call the provider is blocked on cannot wait for a process
that has ended. So a second shape, the same in every other respect: the request goes on the record
(`ApprovalRequested` or `InputRequested`), the component waits, and the host answers **live**
through a handle it keeps — the same kind of thing as `Cancellation` (D15): not a port, the host
reaching in.

The words are the industry's (D61): an **approval request** is answered `Approve`, `Deny` or
`ApproveAndAddRule` — Codex's `accept | decline | acceptWithExecpolicyAmendment`, Claude Code's
"yes, and don't ask again"; an **input request** is the agent's own question, answered with text.

A run given no `Approvals` handle has nobody to ask, and a component that asks anyway is told so
and answers for itself — refused, because consent nobody gave is not consent (D38).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Request:
    """One request a component is waiting on: for approval of an act, or for the person's input."""

    handle: str
    run_id: str
    step: str
    question: str
    component: str | None = None
    """What it is about — the component and inputs the step would run with (BUG-026)."""
    inputs: Any = None
    kind: str = "approval"
    """`approval` or `input`."""


@dataclass(frozen=True)
class Approve:
    """Let it run."""

    kind: str = "approve"


@dataclass(frozen=True)
class Deny:
    """Do not; the reason is told to the agent."""

    reason: str = "the person said no"
    kind: str = "deny"


@dataclass(frozen=True)
class ApproveAndAddRule:
    """Let it run, and let acts like it run without asking — a rule, proposed through the sink,
    that the host's rule registry keeps and governance reads at the next step (Phase 25 group 5).
    The rule is the host's to shape; what is carried here is what the person consented to."""

    rule: Any
    kind: str = "approve_and_add_rule"


@dataclass(frozen=True)
class Parked:
    """Not now: keep the question (D88). The call is not run and not refused for good — the run
    that asked stays asleep in the checkpointer, the provider is told the call is kept and asked
    to stop, and whoever keeps the record settles it on a later request (`Thread.settle`)."""

    kind: str = "park"


ApprovalAnswer = Approve | Deny | ApproveAndAddRule | Parked


class Approvals:
    """The host's handle: requests arrive on `next()`, answers go in through `answer()`. A rule
    that comes with an answer is kept by the run's registry (`RunOptions.rules`, D65) — the
    runtime adds it on either answer path, live or on resume, and proposes it through the sink."""

    """A handle the host keeps. Passed in `RunOptions`, inherited by children unless replaced."""

    def __init__(self) -> None:
        self._waiting: dict[str, asyncio.Future[Any]] = {}
        self._pending: dict[str, Request] = {}
        self._arrivals: asyncio.Queue[Request] = asyncio.Queue()
        self._withdrawals: asyncio.Queue[Request] = asyncio.Queue()
        self.parked: set[str] = set()
        """The handles answered `Parked` (D88): kept for later by whoever keeps the record."""

    def pending(self) -> tuple[Request, ...]:
        """Every question nobody has answered yet, oldest first."""
        return tuple(self._pending.values())

    async def next(self) -> Request:
        """Wait for the next question to arrive."""
        return await self._arrivals.get()

    async def next_withdrawn(self) -> Request:
        """Wait for the next question nobody will answer any more: the asker stopped waiting — a
        CLI that timed the call out, a run that was cancelled. A host showing the question takes
        its buttons away; an answer sent after this is `False`, not a mistake."""
        return await self._withdrawals.get()

    def answer(self, handle: str, judgement: Any) -> bool:
        """Answer one question. `False` if nothing was waiting under that handle."""
        waiting = self._waiting.pop(handle, None)
        self._pending.pop(handle, None)
        if waiting is None or waiting.done():
            return False
        if isinstance(judgement, Parked) or (
            isinstance(judgement, dict) and judgement.get("kind") == "park"
        ):
            self.parked.add(handle)
            judgement = Parked()
        waiting.set_result(judgement)
        return True

    async def ask(self, pending: Request) -> Any:
        """The runtime's side: register the question and wait for its answer."""
        loop = asyncio.get_running_loop()
        waiting: asyncio.Future[Any] = loop.create_future()
        self._waiting[pending.handle] = waiting
        self._pending[pending.handle] = pending
        await self._arrivals.put(pending)
        try:
            return await waiting
        finally:
            self._waiting.pop(pending.handle, None)
            answered = waiting.done() and not waiting.cancelled()
            if self._pending.pop(pending.handle, None) is not None and not answered:
                # Nobody answered and the asker is gone: say so to whoever is showing it.
                self._withdrawals.put_nowait(pending)


__all__ = [
    "ApprovalAnswer",
    "Approvals",
    "Approve",
    "ApproveAndAddRule",
    "Deny",
    "Parked",
    "Request",
]
