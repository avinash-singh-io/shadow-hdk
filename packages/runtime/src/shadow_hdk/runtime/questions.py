"""Asking the host while a step is still running (D58).

D57 parks the run on a component's question and resumes it with the answer — the right shape when
the run can stop. It cannot always stop: a step holding a **provider's session** open is what
keeps that provider alive, and a tool call the provider is blocked on cannot wait for a process
that has ended. So a second shape, the same in every other respect: the question goes on the record
as `Asked`, the component waits, and the host answers **live** through a handle it keeps — the same
kind of thing as `Cancellation` (D15): not a port, the host reaching in.

A run given no `Questions` has nobody to ask, and a component that asks anyway is told so and
answers for itself — refused, because consent nobody gave is not consent (D38).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Pending:
    """One question a component is waiting on."""

    handle: str
    run_id: str
    step: str
    question: str
    component: str | None = None
    """What it is about — the component and inputs the step would run with (BUG-026)."""
    inputs: Any = None


class Questions:
    """A handle the host keeps. Passed in `RunOptions`, inherited by children unless replaced."""

    def __init__(self) -> None:
        self._waiting: dict[str, asyncio.Future[Any]] = {}
        self._pending: dict[str, Pending] = {}
        self._arrivals: asyncio.Queue[Pending] = asyncio.Queue()
        self._withdrawals: asyncio.Queue[Pending] = asyncio.Queue()

    def pending(self) -> tuple[Pending, ...]:
        """Every question nobody has answered yet, oldest first."""
        return tuple(self._pending.values())

    async def next(self) -> Pending:
        """Wait for the next question to arrive."""
        return await self._arrivals.get()

    async def next_withdrawn(self) -> Pending:
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
        waiting.set_result(judgement)
        return True

    async def ask(self, pending: Pending) -> Any:
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


__all__ = ["Pending", "Questions"]
