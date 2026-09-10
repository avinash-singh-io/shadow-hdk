"""A two-way channel carrying JSON **text**, and a loopback pair of them.

Text rather than objects, even in the loopback. A loopback passing live Python objects between two
halves of one process would prove the plumbing and nothing about the boundary — and the boundary is
the entire subject of this package. Everything that crosses here has been through `json.dumps`, so a
type that cannot survive the trip fails in the test suite rather than at a customer's socket.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Protocol

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream


class Channel(Protocol):
    """One end of a two-way link. Frames are JSON text, one message each."""

    async def send(self, frame: str) -> None: ...

    async def receive(self) -> str: ...

    async def aclose(self) -> None: ...


@dataclass
class MemoryChannel:
    """One end of a loopback. `watching` sees every frame this end sends."""

    outbound: MemoryObjectSendStream[str]
    inbound: MemoryObjectReceiveStream[str]
    watching: Callable[[str], None] | None = None

    async def send(self, frame: str) -> None:
        if self.watching is not None:
            self.watching(frame)
        await self.outbound.send(frame)

    async def receive(self) -> str:
        return await self.inbound.receive()

    async def aclose(self) -> None:
        await self.outbound.aclose()
        await self.inbound.aclose()


@asynccontextmanager
async def channel_pair(
    watching: Callable[[str], None] | None = None,
) -> AsyncIterator[tuple[MemoryChannel, MemoryChannel]]:
    """Two ends of one link. Unbounded, because a bounded loopback deadlocks the moment one side
    issues a callback while the other is waiting on a reply — which is this protocol's normal shape,
    not an edge case."""
    left_send, left_receive = anyio.create_memory_object_stream[str](float("inf"))
    right_send, right_receive = anyio.create_memory_object_stream[str](float("inf"))
    host = MemoryChannel(outbound=left_send, inbound=right_receive, watching=watching)
    runtime = MemoryChannel(outbound=right_send, inbound=left_receive, watching=watching)
    try:
        yield host, runtime
    finally:
        await host.aclose()
        await runtime.aclose()


__all__ = ["Channel", "MemoryChannel", "channel_pair"]
