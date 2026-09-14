"""The reusable stream session is a deterministic state machine, not HTTP handler state."""

from __future__ import annotations

import asyncio

import pytest
from shadow_hdk.runtime.streams import (
    AlreadyAttached,
    CursorExpired,
    StreamSession,
)

pytestmark = pytest.mark.anyio


class ManualClock:
    def __init__(self) -> None:
        self.sleepers: list[tuple[float, asyncio.Event]] = []

    async def sleep(self, seconds: float) -> None:
        event = asyncio.Event()
        self.sleepers.append((seconds, event))
        await event.wait()

    async def advance(self) -> None:
        await asyncio.sleep(0)
        for _seconds, event in self.sleepers:
            event.set()
        await asyncio.sleep(0)


async def test_ids_are_monotone_replay_is_bounded_and_a_stale_cursor_is_typed() -> None:
    session = StreamSession[str](capacity=2)
    assert [session.keep(value).id for value in ("one", "two", "three")] == [1, 2, 3]
    assert [(frame.id, frame.value) for frame in session.replay(after=1)] == [
        (2, "two"),
        (3, "three"),
    ]
    with pytest.raises(CursorExpired) as stale:
        session.replay(after=0)
    assert stale.value.after == 0 and stale.value.oldest == 2 and stale.value.latest == 3


async def test_only_one_attachment_receives_replay_then_live_once() -> None:
    session = StreamSession[str](capacity=3)
    session.keep("before")
    attached = session.attach(after=0)
    with pytest.raises(AlreadyAttached):
        session.attach(after=0)

    assert (await attached.receive()).value == "before"
    session.keep("during")
    assert (await attached.receive()).value == "during"
    attached.detach()
    again = session.attach(after=2)
    session.keep("after")
    assert (await again.receive()).value == "after"
    again.detach()


async def test_detach_expires_after_injected_grace_and_reattach_cancels_it() -> None:
    clock = ManualClock()
    expired: list[str] = []

    async def expire() -> None:
        expired.append("expired")

    session = StreamSession[str](capacity=3, grace_seconds=10, clock=clock, on_expire=expire)
    first = session.attach()
    first.detach()
    await asyncio.sleep(0)
    assert [seconds for seconds, _event in clock.sleepers] == [10]
    second = session.attach()
    await clock.advance()
    assert expired == [], "reattachment cancelled the old grace"
    second.detach()
    await asyncio.sleep(0)
    await clock.advance()
    assert expired == ["expired"]
    assert session.expired


async def test_an_idle_attachment_gets_an_ephemeral_heartbeat_not_a_replay_frame() -> None:
    clock = ManualClock()
    session = StreamSession[str](capacity=3, heartbeat_seconds=5, clock=clock)
    attached = session.attach()
    await asyncio.sleep(0)
    assert [seconds for seconds, _event in clock.sleepers] == [5]

    await clock.advance()
    pulse = await attached.receive()
    assert pulse.heartbeat and pulse.id is None and pulse.value is None
    assert session.replay() == (), "heartbeats are link liveness, not durable session frames"
    attached.detach()
