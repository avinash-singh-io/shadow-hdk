"""The run's registry offered over the authenticated socket, for a thread's lifetime (D62).

A `Thread` opens its provider once and turns many times. The provider's MCP configuration names
the relay once, at open, so the registry must be served for as long as the thread lives — and
routed to whichever turn's run is attached. This is that: `RecordingServer` in front of the
runtime's routing, `serve_over_socket` around it, one `ToolSource` naming the relay with the port
and the token in its environment (D42, D44, D52).
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path

from pydantic import JsonValue

from shadow_hdk.adapters.recording.server import RecordingServer
from shadow_hdk.adapters.recording.socket import (
    PORT_VARIABLE,
    TOKEN_VARIABLE,
    serve_over_socket,
)
from shadow_hdk.kernel import Observation
from shadow_hdk.kernel.ports import ToolSource
from shadow_hdk.runtime import RunContext

RELAY = "shadow-hdk-registry"
"""The console script a CLI launches when it thinks it is starting an MCP server."""


def _where_the_relay_is() -> str:
    """The kit's own console script, by its whole path.

    **Beside the running interpreter first** (BUG-226): a console script is installed next to the
    interpreter of the environment it was installed into, so this is the kit's own copy by
    construction. A `PATH` lookup answers for whatever environment the *host process* was started
    with, which inside a packaged application is a different one — and inside an application
    bundle the answer contains a space.

    `PATH` stays as the fallback for a kit imported from a source tree, and the bare name as the
    last resort, so a child that can find it on its own still can.
    """
    beside = Path(sys.executable).parent / RELAY
    if beside.exists():
        return str(beside)
    return shutil.which(RELAY) or RELAY


def relay_source(port: int, token: str) -> ToolSource:
    """Where the provider's tools are — ours, behind the relay, with the token (D52).

    The relay must be on the path the *child* will search, not merely on ours: it is launched by
    the CLI, in the environment we hand the CLI. So it is named by its whole path, and that path
    is never split by whoever spells it for a CLI (BUG-226).
    """
    return ToolSource(
        kind="mcp",
        address=_where_the_relay_is(),
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
