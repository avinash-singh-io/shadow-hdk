"""The server, driven the way a child agent drives it: over a real MCP client session.

The ten tests next door call `tools()` and `call()` directly, which proves the *routing* and proves
nothing about the *wire*. `attach` hands two request handlers to somebody else's server, naming
their parameter models, and a mistake there is invisible to a direct call and total over a socket.
So this drives a real `ClientSession` against the real low-level `Server` through a stream pair.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import anyio
import pytest
from shadow_hdk.adapters.recording import RecordingServer
from mcp import ClientSession, types
from mcp.shared.memory import create_client_server_memory_streams

from shadow_hdk.kernel import Event
from shadow_hdk.runtime import RunContext

from .conftest import with_a_run


async def over_the_wire[T](
    use: Callable[[ClientSession], Awaitable[T]],
) -> tuple[T, list[Event]]:
    """Serve one run's registry to `use` as a client, and give back the run's events too."""

    async def drive(context: RunContext) -> T:
        answer: list[T] = []
        holder = RecordingServer(context)
        async with (
            create_client_server_memory_streams() as (
                (client_read, client_write),
                (server_read, server_write),
            ),
            holder.served() as server,
            anyio.create_task_group() as group,
        ):

            async def serve() -> None:
                await server.run(
                    server_read,
                    server_write,
                    server.create_initialization_options(),
                    raise_exceptions=True,
                )

            group.start_soon(serve)
            async with ClientSession(client_read, client_write) as session:
                await session.initialize()
                answer.append(await use(session))
            # Cancelling unwinds the server task; a `return` from inside the group would be
            # swallowed by the cancel scope, which is why the answer travels in a list.
            group.cancel_scope.cancel()
        return answer[0]

    return await with_a_run(drive)


def text_of(result: types.CallToolResult) -> str:
    return "".join(part.text for part in result.content if isinstance(part, types.TextContent))


@pytest.mark.anyio
async def test_the_registry_reaches_a_real_client_with_its_schemas_intact() -> None:
    listed, _ = await over_the_wire(lambda session: session.list_tools())
    look = next(tool for tool in listed.tools if tool.name == "look")
    assert look.description == "Look a topic up."
    assert look.input_schema["properties"]["topic"]["description"] == "what to look up"
    assert look.input_schema["required"] == ["topic"]


@pytest.mark.anyio
async def test_a_call_over_the_wire_runs_the_component_and_comes_back() -> None:
    async def call(session: ClientSession) -> Any:
        return await session.call_tool("look", {"topic": "lathe"})

    result, _ = await over_the_wire(call)
    assert result.is_error is not True
    assert text_of(result) == '{"found": {"topic": "lathe"}}'


@pytest.mark.anyio
async def test_a_component_that_breaks_reaches_the_client_as_an_error() -> None:
    async def call(session: ClientSession) -> Any:
        return await session.call_tool("breaks", {})

    result, _ = await over_the_wire(call)
    assert result.is_error is True
    assert "failed" in text_of(result)


@pytest.mark.anyio
async def test_what_the_client_did_is_on_the_parents_record() -> None:
    async def call(session: ClientSession) -> Any:
        return await session.call_tool("look", {"topic": "lathe"})

    _, events = await over_the_wire(call)
    invoked = [e for e in events if e.kind == "invoked" and "shadow-hdk__look" in e.step]
    assert len(invoked) == 1, "the child's call did not reach the parent's stream"
