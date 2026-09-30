"""Wait for the thing, not for a number of seconds (TD-015).

A fixed `asyncio.sleep` standing in for a happens-before is a bet on the host being fast enough,
and this suite lost that bet five times in one afternoon — twice on a laptop under load and twice
on CI runners, each time green on a re-run of the same commit. The cost is not the red run. It is
that a red run stops meaning anything, which is the only thing a gate is for.

The sleeps that remain are the ones that are *about* time — an idle timeout that must elapse, a
grace period that must expire. Those are testing a duration, and waiting for one is correct.
"""

from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Awaitable, Callable
from typing import Any

Condition = Callable[[], Any | Awaitable[Any]]


async def until(
    condition: Condition,
    *,
    what: str,
    within: float = 10.0,
    checking_every: float = 0.005,
) -> None:
    """Return once `condition` is true; raise naming `what` if it never becomes true.

    `within` is a **failure** bound, not a synchronisation delay — it is generous on purpose, so a
    slow runner waits rather than fails, and a genuine deadlock still ends the test instead of
    hanging until the suite-wide timeout kills it with no explanation.
    """
    deadline = time.monotonic() + within
    while True:
        answer = condition()
        if inspect.isawaitable(answer):
            answer = await answer
        if answer:
            return
        if time.monotonic() >= deadline:
            raise AssertionError(f"waited {within}s and never saw: {what}")
        await asyncio.sleep(checking_every)


async def pending_on(store: Any, thread_id: str, *, how_many: int = 1) -> None:
    """Wait until the thread's record on disk carries its open question(s).

    **The save is a separate write from the question being asked**, so a reader that acts the
    moment the approval is raised — imaging the store, asserting on the record — is racing it.
    This is the wait that race needs.
    """

    async def carried() -> bool:
        record = await store.get(thread_id)
        return record is not None and len(record.pending) >= how_many

    await until(carried, what=f"{how_many} question(s) pending on thread {thread_id!r}")
