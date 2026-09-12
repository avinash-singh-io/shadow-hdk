"""An MCP server over stdio whose process the runtime holds (BUG-033, D35, D53).

The SDK's `stdio_client` spawns the server and keeps the process to itself, so a server that does
not leave when its stdin closes — wigolo was seen alive with `ppid 1` once, after the harness had
been ended from outside — has nothing ending it. The runtime already has the rule for this: every
session leader it starts is `hold`-ed, and the interpreter's ending, by whichever door, ends them
all. This is the SDK's transport with that one difference: the process is ours, started as a
session leader, held while open, and ended with its **group** when closed or when we end.
"""

from __future__ import annotations

import asyncio
import contextlib
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import anyio

from shadow_hdk.runtime.processes import start_held, stop_or_kill
from mcp import StdioServerParameters
from mcp import types as mcp_types
from mcp.client.stdio import get_default_environment
from mcp.shared.message import SessionMessage

GRACE_S = 2.0
"""How long a server gets to leave on its own after its stdin closes, before the group is ended."""


@asynccontextmanager
async def held_stdio_client(server: StdioServerParameters) -> AsyncIterator[tuple[Any, Any]]:
    """The `(read, write)` streams a `ClientSession` takes, over a server process we hold."""
    command = shutil.which(server.command) or server.command
    # A session leader the runtime holds (D35, D53): ended with its group, and when we end.
    process = await start_held(
        command,
        *server.args,
        cwd=str(server.cwd) if server.cwd else None,
        env=get_default_environment() | dict(server.env or {}),
        stdin=asyncio.subprocess.PIPE,
        stderr=None,  # its diagnostics are ours to see, as the SDK's default has them
    )
    assert process.stdin is not None and process.stdout is not None

    to_session_send, to_session = anyio.create_memory_object_stream[SessionMessage | Exception](0)
    from_session, from_session_receive = anyio.create_memory_object_stream[SessionMessage](0)

    async def read_the_server() -> None:
        try:
            async with to_session_send:
                while True:
                    line = await process.stdout.readline()
                    if not line:
                        return
                    text = line.decode(server.encoding, errors=server.encoding_error_handler)
                    if not text.strip():
                        continue
                    try:
                        message = mcp_types.jsonrpc_message_adapter.validate_json(
                            text, by_name=False
                        )
                        await to_session_send.send(SessionMessage(message))
                    except (anyio.ClosedResourceError, anyio.BrokenResourceError):
                        return
                    except Exception as broken:  # noqa: BLE001 — a bad line is the session's to see
                        await to_session_send.send(broken)
        except (anyio.ClosedResourceError, anyio.BrokenResourceError):
            return

    async def write_the_server() -> None:
        try:
            async with from_session_receive:
                async for session_message in from_session_receive:
                    text = session_message.message.model_dump_json(
                        by_alias=True, exclude_unset=True
                    )
                    process.stdin.write(
                        (text + "\n").encode(server.encoding, errors=server.encoding_error_handler)
                    )
                    await process.stdin.drain()
        except (anyio.ClosedResourceError, anyio.BrokenResourceError, OSError):
            with contextlib.suppress(anyio.ClosedResourceError):
                await to_session_send.aclose()

    async with anyio.create_task_group() as group:
        group.start_soon(read_the_server)
        group.start_soon(write_the_server)
        try:
            yield to_session, from_session
        finally:
            # Its stdin closing is the polite request; the group is ended if it does not go.
            with contextlib.suppress(Exception):
                process.stdin.close()
            with anyio.CancelScope(shield=True):
                await stop_or_kill(process, grace_s=GRACE_S)
            group.cancel_scope.cancel()


__all__ = ["held_stdio_client"]
