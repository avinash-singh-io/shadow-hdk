"""Nothing reaches the run's registry without the token the run minted (D52; D44's debt).

The socket is loopback and ephemeral, and that was never enough: any process on the machine that
guessed the port could act inside somebody else's run. A token, minted per serve with `secrets`,
travels to the relay in its environment and is sent as the **first line** before any MCP traffic.
The server reads exactly one line, compares in constant time, and either serves or closes.

Three things the token must never do: appear in a log, appear on an event, appear in an
`Available`. It is a secret, and this runtime holds no secrets it does not have to (D41) — this one
lives for one serve and dies with it.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path
from typing import Any

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from shadow_hdk.adapters.recording import PORT_VARIABLE, RecordingServer, serve_over_socket
from shadow_hdk.adapters.recording.socket import TOKEN_VARIABLE

from shadow_hdk.runtime import RunContext

from .conftest import with_a_run

RELAY = [str(Path(sys.executable).parent / "shadow-hdk-registry")]


async def with_a_child(*, token_env: str | None) -> dict[str, Any]:
    """Spawn the relay the way a CLI would, with the token the caller chooses, and say what came
    back."""

    async def drive(context: RunContext) -> dict[str, Any]:
        holder = RecordingServer(context)
        async with (
            holder.served() as server,
            serve_over_socket(server, refused=holder.refuse) as (port, token),
        ):
            env = {PORT_VARIABLE: str(port)}
            if token_env == "right":
                env[TOKEN_VARIABLE] = token
            elif token_env == "wrong":
                env[TOKEN_VARIABLE] = "not-the-token"
            parameters = StdioServerParameters(command=RELAY[0], args=RELAY[1:], env=env)
            try:
                with anyio.fail_after(20):
                    async with (
                        stdio_client(parameters) as (incoming, outgoing),
                        ClientSession(incoming, outgoing) as session,
                    ):
                        await session.initialize()
                        listed = await session.list_tools()
                        return {
                            "tools": sorted(t.name for t in listed.tools),
                            "refused": server_refused(holder),
                        }
            except (TimeoutError, Exception):  # noqa: BLE001 — a refused relay looks like a dead server
                return {"tools": None, "refused": server_refused(holder)}

    found, _ = await with_a_run(drive, steps=40)
    return found


def server_refused(holder: Any) -> int:
    return int(getattr(holder, "refused_connections", 0))


@pytest.mark.anyio
async def test_the_right_token_is_served() -> None:
    seen = await with_a_child(token_env="right")

    assert seen["tools"] == ["breaks", "driver", "look", "wipe"]


@pytest.mark.anyio
async def test_the_wrong_token_is_refused_and_counted() -> None:
    seen = await with_a_child(token_env="wrong")

    assert seen["tools"] is None, "a wrong token reached the registry"
    assert seen["refused"] == 1, "the refusal was not counted"


@pytest.mark.anyio
async def test_no_token_at_all_is_refused() -> None:
    seen = await with_a_child(token_env=None)

    assert seen["tools"] is None, "a connection with no token reached the registry"


INITIALIZE = b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'


async def raw_connection_sending(first: bytes) -> tuple[bool, int]:
    """Connect without the relay, send `first` and then an MCP initialize, and say whether MCP
    answered and how many refusals the holder counted."""

    async def drive(context: RunContext) -> tuple[bool, int]:
        holder = RecordingServer(context)
        async with (
            holder.served() as server,
            serve_over_socket(server, refused=holder.refuse) as (port, _token),
        ):
            with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
                raw.sendall(first + INITIALIZE)
                raw.settimeout(3)
                try:
                    answered = raw.recv(4096)
                except (TimeoutError, OSError):
                    answered = b""
            # The server closes on refusal; give its task a turn to count before we look.
            await anyio.sleep(0.05)
            return b"jsonrpc" in answered, server_refused(holder)

    found, _ = await with_a_run(drive, steps=10)
    return found


@pytest.mark.anyio
async def test_a_raw_connection_that_speaks_mcp_first_is_refused() -> None:
    """The line the server reads first is the token, and a JSON-RPC frame is not a token. Without
    this a client that skipped the handshake and started talking MCP would be served — which is
    the whole hole, one byte to the left."""
    served, refused = await raw_connection_sending(b"")

    assert served is False, "MCP traffic without a token was answered"
    assert refused == 1


@pytest.mark.anyio
async def test_an_empty_line_is_not_a_token() -> None:
    """A bare newline is the case a prefix compare accepts — every string starts with the empty
    one. The compare must be equality, and this is the test that can tell."""
    served, refused = await raw_connection_sending(b"\n")

    assert served is False, "an empty token line was accepted"
    assert refused == 1


def test_the_token_is_a_secret_shaped_secret() -> None:
    """Minted with `secrets`, long enough to be unguessable, different every time."""
    from shadow_hdk.adapters.recording.socket import mint

    one, two = mint(), mint()

    assert one != two
    assert len(one) >= 32
