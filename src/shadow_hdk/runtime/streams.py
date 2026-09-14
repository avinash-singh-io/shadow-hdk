"""A reconnectable stream is session state, independent of its transport.

Durable frames receive monotone ids and stay in a bounded replay window. Exactly one attachment
may consume replay followed by live frames; detaching starts an injected-clock grace period. Link
heartbeats are deliberately ephemeral: they prove the attachment is alive without entering replay
or any product record.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol


class SleepClock(Protocol):
    async def sleep(self, seconds: float) -> None: ...


class AsyncioClock:
    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class CursorExpired(ValueError):
    """The requested cursor precedes the oldest frame still retained."""

    def __init__(self, *, after: int, oldest: int, latest: int) -> None:
        super().__init__(
            f"cursor {after} expired; retained frames run from {oldest} through {latest}"
        )
        self.after = after
        self.oldest = oldest
        self.latest = latest


class AlreadyAttached(RuntimeError):
    """A stream session has one consumer; a second cannot steal or duplicate it."""


class StreamExpired(RuntimeError):
    """The detached session passed its grace period and cannot be attached again."""


@dataclass(frozen=True)
class StreamFrame[T]:
    id: int | None
    value: T | None
    heartbeat: bool = False


class StreamAttachment[T]:
    def __init__(self, session: StreamSession[T], queue: asyncio.Queue[StreamFrame[T]]) -> None:
        self._session = session
        self._queue = queue
        self._detached = False

    async def receive(self) -> StreamFrame[T]:
        return await self._queue.get()

    def detach(self) -> None:
        if self._detached:
            return
        self._detached = True
        self._session._detach(self)  # noqa: SLF001 — an attachment is one half of the primitive


class StreamSession[T]:
    """Bounded replay plus one live attachment, with no HTTP or product assumptions."""

    def __init__(
        self,
        *,
        capacity: int,
        grace_seconds: float | None = None,
        heartbeat_seconds: float | None = None,
        clock: SleepClock | None = None,
        on_expire: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        if capacity <= 0:
            raise ValueError("a stream session capacity must be positive")
        if grace_seconds is not None and grace_seconds < 0:
            raise ValueError("stream grace_seconds cannot be negative")
        if heartbeat_seconds is not None and heartbeat_seconds <= 0:
            raise ValueError("stream heartbeat_seconds must be positive")
        self.capacity = capacity
        self.grace_seconds = grace_seconds
        self.heartbeat_seconds = heartbeat_seconds
        self.clock = clock or AsyncioClock()
        self.on_expire = on_expire
        self._frames: deque[StreamFrame[T]] = deque(maxlen=capacity)
        self._next_id = 1
        self._attachment: StreamAttachment[T] | None = None
        self._queue: asyncio.Queue[StreamFrame[T]] | None = None
        self._grace: asyncio.Task[None] | None = None
        self._heartbeat: asyncio.Task[None] | None = None
        self._activity = 0
        self.expired = False

    @property
    def attached(self) -> bool:
        return self._attachment is not None

    def keep(self, value: T) -> StreamFrame[T]:
        if self.expired:
            raise StreamExpired("the stream session has expired")
        frame = StreamFrame(id=self._next_id, value=value)
        self._next_id += 1
        self._frames.append(frame)
        self._activity += 1
        if self._queue is not None:
            self._queue.put_nowait(frame)
        return frame

    def replay(self, *, after: int | None = None) -> tuple[StreamFrame[T], ...]:
        if not self._frames:
            return ()
        oldest = self._frames[0].id
        latest = self._frames[-1].id
        assert oldest is not None and latest is not None
        if after is not None and after < oldest - 1:
            raise CursorExpired(after=after, oldest=oldest, latest=latest)
        if after is None:
            return tuple(self._frames)
        return tuple(frame for frame in self._frames if frame.id is not None and frame.id > after)

    def attach(self, *, after: int | None = None) -> StreamAttachment[T]:
        if self.expired:
            raise StreamExpired("the stream session has expired")
        if self._attachment is not None:
            raise AlreadyAttached("the stream session already has an attachment")
        replay = self.replay(after=after)
        self._cancel(self._grace)
        self._grace = None
        queue: asyncio.Queue[StreamFrame[T]] = asyncio.Queue()
        for frame in replay:
            queue.put_nowait(frame)
        attachment = StreamAttachment(self, queue)
        self._attachment = attachment
        self._queue = queue
        if self.heartbeat_seconds is not None:
            self._heartbeat = asyncio.create_task(self._send_heartbeats(attachment))
        return attachment

    def _detach(self, attachment: StreamAttachment[T]) -> None:
        if self._attachment is not attachment:
            return
        self._attachment = None
        self._queue = None
        self._cancel(self._heartbeat)
        self._heartbeat = None
        if not self.expired and self.grace_seconds is not None:
            self._grace = asyncio.create_task(self._expire_after_grace())

    async def _send_heartbeats(self, attachment: StreamAttachment[T]) -> None:
        while self._attachment is attachment and not self.expired:
            before = self._activity
            await self.clock.sleep(self.heartbeat_seconds or 0)
            if self._attachment is not attachment or self.expired:
                return
            if before == self._activity and self._queue is not None:
                self._queue.put_nowait(StreamFrame(id=None, value=None, heartbeat=True))

    async def _expire_after_grace(self) -> None:
        await self.clock.sleep(self.grace_seconds or 0)
        if self._attachment is not None or self.expired:
            return
        self.expired = True
        if self.on_expire is not None:
            await self.on_expire()

    def expire(self) -> None:
        """End explicitly without calling the detach-expiry callback again."""
        if self.expired:
            return
        self.expired = True
        self._attachment = None
        self._queue = None
        self._cancel(self._heartbeat)
        self._cancel(self._grace)
        self._heartbeat = None
        self._grace = None

    @staticmethod
    def _cancel(task: asyncio.Task[None] | None) -> None:
        if task is not None:
            task.cancel()


__all__ = [
    "AlreadyAttached",
    "AsyncioClock",
    "CursorExpired",
    "SleepClock",
    "StreamAttachment",
    "StreamExpired",
    "StreamFrame",
    "StreamSession",
]
