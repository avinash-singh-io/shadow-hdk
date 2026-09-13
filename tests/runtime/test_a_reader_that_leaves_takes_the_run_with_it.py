"""A reader that leaves takes the run with it (BUG-041).

`run()` drives the composition in a task of its own and yields what the emitter hears. When the
reader is cancelled — the wire session closed, a page reloaded, a host going down — the
generator's `finally` waited for the drive to end. A drive blocked on a question nobody will
answer never ends, so the reader hung forever on its own cancellation. Found by the first test
that killed a host mid-question (D80): every `thread/close` on a thread with a card open would
have hung the same way.

The drive is cancelled with its reader. The question it was waiting on is withdrawn (D59), so a
host showing it takes its buttons away.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    Floor,
    Invoke,
    Lease,
    Observation,
)
from shadow_hdk.kernel.ports import Allow
from shadow_hdk.runtime import Approvals, Ports, RunOptions, current_run, run
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink, make_registration

pytestmark = pytest.mark.anyio

ASKER = make_registration("asker")


class _AllowAll:
    async def judge(self, effects: Any, context: Any) -> Allow:
        return Allow()


async def asks_live(_inputs: JsonValue) -> Observation:
    context = current_run()
    assert context is not None
    await context.request_approval("may I?")
    return Completed("never")  # pragma: no cover — nobody answers


def _ports() -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(ASKER, asks_live)]),),
        governance=_AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


async def test_a_cancelled_reader_ends_within_a_moment_and_the_question_is_withdrawn() -> None:
    approvals = Approvals()
    options = RunOptions(lease=Lease(Ceiling(5, 60, None), Floor(0)), approvals=approvals)

    async def reading() -> None:
        async for _event in run(Composition((Invoke("ask", "asker"),)), _ports(), options=options):
            pass

    reader = asyncio.create_task(reading())
    asked = await asyncio.wait_for(approvals.next(), 10)
    reader.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(reader, 2)  # the drive went with it; nothing waits for nobody
    withdrawn = await asyncio.wait_for(approvals.next_withdrawn(), 2)
    assert withdrawn.handle == asked.handle
    assert approvals.pending() == ()
