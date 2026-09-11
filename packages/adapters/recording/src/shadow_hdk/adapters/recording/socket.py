"""The registry, offered on a loopback socket — and the relay that lets a child reach it.

`pipes.py` explains why the usual MCP arrangement is inverted here: `RecordingServer` holds a live
`RunContext`, the parent's lease and the parent's event stream, so it is not a program that can be
*started*. It can only be connected to. Where the parent spawns the child itself, it serves MCP over
that child's own pipes and the problem goes away.

**A coding CLI does not let us do that.** It spawns its MCP servers itself, from a configuration it
is handed — `--mcp-config` for one, `session/new`'s `mcpServers` for another — and it will launch
whatever program that configuration names. The program it launches cannot be our server.

So the program it launches is a **relay**: forty lines that connect to a loopback port we are
already listening on and copy bytes both ways. The child believes it started an MCP server; the
server it reached is the run's own registry, in this process, with the lease and the record intact.
That is what closes D42's socket around a provider that owns its own loop.

**The port is loopback and ephemeral, and that was never enough** (D52). Any process on the
machine that guessed the port could act inside somebody else's run. So a token is minted per serve
with `secrets`, travels to the relay in its environment, and is sent as the **first line** before
any MCP traffic. The server reads exactly one line, compares in constant time, and serves or
closes — a JSON-RPC frame arriving where the token should be is a refusal, not a handshake. The
token lives for one serve and dies with it; it appears on no event and in no log.
"""

from __future__ import annotations

import os
import secrets
import socket
import sys
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

import anyio
from anyio.abc import SocketAttribute
from shadow_hdk.adapters.recording.pipes import serve_over_pipes

PORT_VARIABLE = "SHADOW_HDK_REGISTRY_PORT"
"""Where the relay is told which port to reach. An environment variable rather than an argument,
because a CLI's MCP configuration may control the argv and not much else."""

TOKEN_VARIABLE = "SHADOW_HDK_REGISTRY_TOKEN"
"""Where the relay is told the token (D52). The environment, like the port — and never argv, which
`ps` shows to every user on the machine."""


def mint() -> str:
    """One token, for one serve."""
    return secrets.token_urlsafe(32)


@asynccontextmanager
async def serve_over_socket(
    server: Any, *, host: str = "127.0.0.1", refused: Callable[[], None] | None = None
) -> AsyncIterator[tuple[int, str]]:
    """Listen on an ephemeral loopback port and serve `server` to whoever presents the token.

    Yields `(port, token)`. Loopback only, and not negotiable here: a registry bound to a routable
    interface is a way for anyone on the network to act inside somebody else's run. The token is
    the second half of the same argument (D52). `refused` is called once per connection turned
    away — the holder counts; this module keeps nothing about what was presented.
    """
    listener = await anyio.create_tcp_listener(local_host=host, local_port=0)
    port = int(listener.extra(SocketAttribute.local_address)[1])
    token = mint()
    expected = token.encode()

    async def serve_one(stream: Any) -> None:
        async with stream:
            # **One line, then MCP — or nothing.** The relay sends the token and a newline before
            # its first frame. Read up to the newline and no further, so the first MCP frame is
            # left intact for the transport; a frame arriving here instead of a token is refused,
            # because it means somebody skipped the handshake.
            presented = b""
            while b"\n" not in presented and len(presented) < 512:
                chunk = await stream.receive(1)
                if not chunk:
                    break
                presented += chunk
            line = presented.split(b"\n", 1)[0]
            if not secrets.compare_digest(line, expected):
                if refused is not None:
                    refused()
                return
            await serve_over_pipes(server, stream, stream)

    # **The listener is closed by leaving its own block, never by hand.** `serve()` parks in
    # `accept()`; closing the listener out from under it raises `ClosedResourceError` *through the
    # task group*, which turns an ordinary teardown into a failure the caller has to explain.
    # Cancelling first is not enough — the close still races the parked accept. Letting the task
    # group unwind and only then leaving `async with listener` orders it correctly.
    async with listener, anyio.create_task_group() as group:
        group.start_soon(listener.serve, serve_one)
        try:
            yield port, token
        finally:
            group.cancel_scope.cancel()


def relay() -> int:
    """Copy bytes between this process's pipes and the registry's port, until either end closes.

    This is the program a CLI launches when it thinks it is starting an MCP server. It is
    deliberately tiny and deliberately synchronous: it must start fast, hold nothing, and fail
    plainly. Threads rather than asyncio because two blocking copies is the whole of it.
    """
    raw = os.environ.get(PORT_VARIABLE)
    if not raw or not raw.isdigit():
        print(f"{PORT_VARIABLE} is not set to a port; nothing to relay to", file=sys.stderr)
        return 2
    token = os.environ.get(TOKEN_VARIABLE, "")
    if not token:
        print(f"{TOKEN_VARIABLE} is not set; the registry will refuse this relay", file=sys.stderr)
        return 4
    try:
        upstream = socket.create_connection(("127.0.0.1", int(raw)), timeout=30)
    except OSError as unreachable:
        print(f"the registry on port {raw} is not there: {unreachable}", file=sys.stderr)
        return 3
    # The token, then a newline, then nothing until MCP starts — the server reads one line.
    upstream.sendall(token.encode() + b"\n")

    def pump(read_from: Any, write_to: Any) -> None:
        try:
            while chunk := read_from(4096):
                write_to(chunk)
        except (OSError, ValueError):
            pass

    upward = threading.Thread(
        target=pump, args=(sys.stdin.buffer.read1, upstream.sendall), daemon=True
    )
    upward.start()

    def to_stdout(data: bytes) -> None:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

    pump(upstream.recv, to_stdout)
    return 0


if __name__ == "__main__":  # pragma: no cover — it is the child, and the child is tested
    raise SystemExit(relay())


__all__ = ["PORT_VARIABLE", "TOKEN_VARIABLE", "mint", "relay", "serve_over_socket"]
