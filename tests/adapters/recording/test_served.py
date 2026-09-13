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
from mcp import ClientSession, types
from mcp.shared.memory import create_client_server_memory_streams
from shadow_hdk.adapters.recording import RecordingServer

from shadow_hdk.kernel import Event, Invoked, Observed
from shadow_hdk.kernel.ports import GovernancePort
from shadow_hdk.runtime import RunContext

from .conftest import with_a_run
from .test_recording import READING, mode


async def over_the_wire[T](
    use: Callable[[ClientSession], Awaitable[T]],
    *,
    governance: GovernancePort | None = None,
    steps: int = 20,
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

    return await with_a_run(drive, governance=governance, steps=steps)


def text_of(result: types.CallToolResult) -> str:
    return "".join(part.text for part in result.content if isinstance(part, types.TextContent))


@pytest.mark.anyio
async def test_the_registry_reaches_a_real_client_with_its_schemas_intact() -> None:
    listed, _ = await over_the_wire(lambda session: session.list_tools())
    assert {tool.name for tool in listed.tools} == {"look", "wipe", "breaks", "driver"}
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
    invoked = [e for e in events if isinstance(e, Invoked) and e.component == "look"]
    observed = [e for e in events if isinstance(e, Observed) and e.step != "s1"]
    assert len(invoked) == 1, "the child's call did not reach the parent's stream"
    assert observed, "the child's answer did not reach the parent's stream"
    assert invoked[0].step.startswith("shadow-hdk__look")
    assert invoked[0].run_id != events[0].run_id, (
        "it should carry the child's run id, not the parent's"
    )


@pytest.mark.anyio
async def test_a_narrowing_mode_narrows_a_real_client_with_nothing_in_between() -> None:
    """The mode is the only thing between the registry and the wire. `wipe` writes irreversibly, so
    a reading mode removes it from the client's list because it removed it from the run."""
    listed, _ = await over_the_wire(lambda session: session.list_tools(), governance=mode(READING))
    names = {tool.name for tool in listed.tools}
    assert "look" in names
    assert "wipe" not in names


@pytest.mark.anyio
async def test_a_client_that_calls_forever_is_stopped_by_the_parents_lease() -> None:
    """Nothing in the server counts the child's calls. The ceiling it was carved from does."""

    async def call_until_stopped(session: ClientSession) -> int:
        errors = 0
        for _ in range(40):
            result = await session.call_tool("look", {"topic": "lathe"})
            if result.is_error:
                errors += 1
                if errors > 2:
                    break
        return errors

    errors, _ = await over_the_wire(call_until_stopped, steps=6)
    assert errors > 0, "the client was never stopped"


@pytest.mark.anyio
async def test_a_session_that_listed_is_told_when_the_list_changes() -> None:
    """BUG-032: a resident CLI lists once and keeps the catalogue; after `set_mode` it must be
    told to list again — MCP's `notifications/tools/list_changed`, sent to every session that
    has listed this registry."""
    heard: list[str] = []

    async def drive(context: RunContext) -> int:
        holder = RecordingServer(context)
        async with (
            create_client_server_memory_streams() as (
                (client_read, client_write),
                (server_read, server_write),
            ),
            holder.served() as server,
            anyio.create_task_group() as group,
        ):
            group.start_soon(
                server.run, server_read, server_write, server.create_initialization_options()
            )

            async def notify(method: str) -> None:
                from mcp.shared.message import SessionMessage
                from mcp_types import JSONRPCNotification

                await server_write.send(
                    SessionMessage(JSONRPCNotification(jsonrpc="2.0", method=method, params=None))
                )

            forget = holder.watch(notify)

            async def on_message(message: Any) -> None:
                method = getattr(getattr(message, "root", message), "method", None)
                if method:
                    heard.append(str(method))

            async with ClientSession(client_read, client_write, message_handler=on_message) as s:
                await s.initialize()
                await s.list_tools()
                await holder.changed()
                for _ in range(100):
                    if "notifications/tools/list_changed" in heard:
                        break
                    await anyio.sleep(0.01)
                forget()
                await holder.changed()  # nobody watching any more: nothing sent, nothing raised
            group.cancel_scope.cancel()
        return heard.count("notifications/tools/list_changed")

    told, _ = await with_a_run(drive)
    assert told == 1, heard
