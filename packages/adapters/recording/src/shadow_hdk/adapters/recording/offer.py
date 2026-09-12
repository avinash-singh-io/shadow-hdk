"""The run's registry offered over the authenticated socket, for a thread's lifetime (D62).

A `Thread` opens its provider once and turns many times. The provider's MCP configuration names
the relay once, at open, so the registry must be served for as long as the thread lives — and
routed to whichever turn's run is attached. This is that: `RecordingServer` in front of the
runtime's routing, `serve_over_socket` around it, one `ToolSource` naming the relay with the port
and the token in its environment (D42, D44, D52).
"""

from __future__ import annotations

import shutil
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager

from shadow_hdk.adapters.recording.server import RecordingServer
from shadow_hdk.adapters.recording.socket import (
    PORT_VARIABLE,
    TOKEN_VARIABLE,
    serve_over_socket,
)
from pydantic import JsonValue

from shadow_hdk.kernel import Observation
from shadow_hdk.kernel.ports import ToolSource
from shadow_hdk.runtime import RunContext

RELAY = "shadow-hdk-registry"
"""The console script a CLI launches when it thinks it is starting an MCP server."""


def relay_source(port: int, token: str) -> ToolSource:
    """Where the provider's tools are — ours, behind the relay, with the token (D52).

    The relay must be on the path the *child* will search, not merely on ours: it is launched by
    the CLI, in the environment we hand the CLI.
    """
    found = shutil.which(RELAY)
    return ToolSource(
        kind="mcp",
        address=found or RELAY,
        env=((PORT_VARIABLE, str(port)), (TOKEN_VARIABLE, token)),
    )


class SocketOffer:
    """A thread's registry, served over the socket under the host's name."""

    def __init__(self, *, name: str = "tools", withhold: frozenset[str] | set[str] = frozenset()):
        self._holder = RecordingServer(None, name=name, withhold=withhold)

    @property
    def name(self) -> str:
        return self._holder.name

    @property
    def holder(self) -> RecordingServer:
        return self._holder

    def attach(self, context: RunContext) -> None:
        self._holder.attach(context)

    def detach(self) -> None:
        self._holder.detach()

    async def call(
        self, name: str, arguments: Mapping[str, JsonValue] | None = None
    ) -> Observation:
        return await self._holder.call(name, arguments)

    async def changed(self) -> None:
        await self._holder.changed()

    @asynccontextmanager
    async def served(self) -> AsyncIterator[tuple[ToolSource, ...]]:
        holder = self._holder
        async with (
            holder.served() as server,
            serve_over_socket(server, refused=holder.refuse, watch=holder.watch) as (
                port,
                token,
            ),
        ):
            yield (relay_source(port, token),)


__all__ = ["RELAY", "SocketOffer", "relay_source"]
