"""Serving the registry to a child *process*, over its own pipes.

The MCP norm is inverted here, and that is the whole content of this module.

In the SDK's stdio convenience the **client spawns the server**: `stdio_client` starts a process
and talks to it. That cannot be our shape. `RecordingServer` is not a program that can be started —
it holds a live `RunContext`, the parent's lease and the parent's event stream, none of which
survive being launched fresh in another process. So the parent spawns the **child** and serves MCP
over the child's own stdin and stdout: we write to its stdin, we read from its stdout, and the
child runs an ordinary `ClientSession` believing it was started by somebody.

The framing is the same newline-delimited JSON-RPC the stdio transport uses; the SDK just does not
expose it for streams other than this process's fd 0 and 1, so it is twenty lines here.

That also answers the transport question for anything further away: a child on another machine
needs a transport where the server is *already listening* (streamable HTTP), because the server
cannot be launched on demand — it can only be connected to. `09` §8's wire, when it comes, has to
start from that.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import anyio
import mcp_types
from anyio.abc import ByteReceiveStream, ByteSendStream
from mcp.shared.message import SessionMessage


async def serve_over_pipes(
    server: Any,
    incoming: ByteReceiveStream,
    outgoing: ByteSendStream,
    *,
    watch: Callable[[Callable[[str], Awaitable[None]]], Callable[[], None]] | None = None,
) -> None:
    """Serve `server` over a raw byte pipe pair, returning when `incoming` closes.

    `incoming` is what the child says (its stdout); `outgoing` is what we say to it (its stdin).
    `watch`, when given, is handed a way to send this connection a notification on the server's
    own stream — `notifications/tools/list_changed` when the catalogue changes (BUG-032) — and
    returns the function that forgets it when the connection closes.
    """
    to_server_write, to_server_read = anyio.create_memory_object_stream[SessionMessage](64)
    from_server_write, from_server_read = anyio.create_memory_object_stream[SessionMessage](64)

    async def notify(method: str) -> None:
        from mcp_types import JSONRPCNotification

        await from_server_write.send(
            SessionMessage(JSONRPCNotification(jsonrpc="2.0", method=method, params=None))
        )

    forget = watch(notify) if watch is not None else None

    async def read_the_child() -> None:
        buffered = b""
        async with to_server_write:
            async for chunk in incoming:
                buffered += chunk
                while b"\n" in buffered:
                    line, buffered = buffered.split(b"\n", 1)
                    if line.strip():
                        message = mcp_types.jsonrpc_message_adapter.validate_json(
                            line, by_name=False
                        )
                        await to_server_write.send(SessionMessage(message))

    async def write_to_the_child() -> None:
        async with from_server_read:
            async for session_message in from_server_read:
                text = session_message.message.model_dump_json(by_alias=True, exclude_unset=True)
                await outgoing.send(text.encode() + b"\n")

    async with anyio.create_task_group() as group:
        group.start_soon(write_to_the_child)
        group.start_soon(
            server.run, to_server_read, from_server_write, server.create_initialization_options()
        )
        try:
            await read_the_child()
        finally:
            if forget is not None:
                forget()
        # The child's stdout closed: it is gone, and nothing more will be asked of us.
        group.cancel_scope.cancel()


__all__ = ["serve_over_pipes"]
