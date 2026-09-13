"""A child agent that ignores `SIGTERM` is made to go (BUG-011, D35).

`tests/runtime/test_a_process_that_will_not_stop_is_killed.py` proves the mechanism against bare
processes. This proves the **bridge** uses it: a real ACP child over a real pipe, spawned by the
adapter, spoken to over the protocol, and then asked to stop while it is deaf to being asked.

`spikes/acp/agent.py --deaf` is a conformant agent that has installed `SIG_IGN` for `SIGTERM`. It is
not a shape ACP describes; it exists because a cooperative agent cannot demonstrate a deadline.
"""

from __future__ import annotations

import asyncio
import os
import time

from shadow_hdk.adapters.acp import AcpAgent
from tests.adapters.acp.test_agent import READER, SPIKE

GRACE = 1.0
OUTER_BOUND = 30.0
"""If the deadline is not enforced this test **fails** rather than hanging the suite."""


def deaf_child(**kw: object) -> AcpAgent:
    return AcpAgent(
        SPIKE[0],
        [*SPIKE[1:], "--deaf"],
        name="child",
        effects=READER,
        at="2026-09-10T00:00:00+00:00",
        grace_s=GRACE,
        **kw,  # type: ignore[arg-type]
    )


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


async def test_a_deaf_child_does_not_wedge_the_bridge() -> None:
    agent = deaf_child()
    await asyncio.wait_for(agent.start(), OUTER_BOUND)
    assert agent._process is not None  # noqa: SLF001 — the claim is about the machine, not the object
    pid = agent._process.pid  # noqa: SLF001
    assert agent.process_is_running

    started = time.monotonic()
    await asyncio.wait_for(agent.stop(), OUTER_BOUND)

    assert time.monotonic() - started < 15.0, "stop() waited on a child that will never answer"
    assert agent.had_to_be_killed is True
    await asyncio.sleep(0.2)
    assert not _alive(pid), "the child agent was left running"


async def test_a_child_that_answers_is_not_killed() -> None:
    """The grace period is not decoration: an agent asked politely gets to close what it had open,
    and a bridge that killed every child would lose whatever it was mid-way through writing."""
    async with AcpAgent(
        SPIKE[0],
        list(SPIKE[1:]),
        name="child",
        effects=READER,
        at="2026-09-10T00:00:00+00:00",
        grace_s=10.0,
    ) as agent:
        assert agent.process_is_running

    assert agent.had_to_be_killed is False, "a cooperative child was killed"


async def test_stopping_a_child_that_never_started_is_quiet() -> None:
    """`stop()` runs from `__aexit__` and from the timeout path, so it must tolerate a bridge whose
    `start()` raised — a host cleaning up after a failure should not meet a second one."""
    agent = deaf_child()

    await asyncio.wait_for(agent.stop(), OUTER_BOUND)

    assert agent.process_is_running is False
