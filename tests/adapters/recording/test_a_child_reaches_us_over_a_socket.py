"""A child that launches its own MCP server, reaching ours instead (D42).

`test_over_a_process.py` proves the case where **we** spawn the child: we serve MCP over its pipes
and it never knows. A coding CLI does not allow that. It spawns its MCP servers itself, from a
configuration it is handed, and it will launch whatever program that configuration names — which
cannot be `RecordingServer`, because that holds a live `RunContext` and is not a program.

So the program it launches is a relay, and this proves the whole chain the way a CLI will use it:
a **real `ClientSession`**, spawning a **real relay process**, reaching a registry that lives in
this process inside a running step. Nothing is faked at either end; the only thing standing in for
Claude Code is the client session, which is the part that is not ours anyway.

The claim that matters is the last one: what the child called lands on the **parent's** record.
That is what makes a subscription-driven agent as governed as one we drive ourselves.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from shadow_hdk.adapters.recording import (
    PORT_VARIABLE,
    TOKEN_VARIABLE,
    RecordingServer,
    serve_over_socket,
)
from shadow_hdk.kernel import Event, Invoked, Observed
from shadow_hdk.runtime import RunContext

from .conftest import with_a_run

RELAY = [str(Path(sys.executable).parent / "shadow-hdk-registry")]
"""The installed console script — which is what a CLI's MCP configuration would actually name."""


async def with_a_child_over_a_socket() -> tuple[dict[str, Any], list[Event]]:
    async def drive(context: RunContext) -> dict[str, Any]:
        holder = RecordingServer(context)
        async with holder.served() as server, serve_over_socket(server) as (port, token):
            parameters = StdioServerParameters(
                command=RELAY[0],
                args=RELAY[1:],
                env={PORT_VARIABLE: str(port), TOKEN_VARIABLE: token},
            )
            async with (
                stdio_client(parameters) as (incoming, outgoing),
                ClientSession(incoming, outgoing) as session,
            ):
                await session.initialize()
                listed = await session.list_tools()
                looked = await session.call_tool("look", {"topic": "lathe"})
                return {
                    "tools": sorted(tool.name for tool in listed.tools),
                    "look": looked.content[0].text,  # type: ignore[union-attr]
                    "look_is_error": bool(looked.is_error),
                }

    return await with_a_run(drive, steps=40)


@pytest.mark.anyio
async def test_a_child_that_launched_a_relay_is_using_our_registry() -> None:
    said, _ = await with_a_child_over_a_socket()

    assert said["tools"] == ["breaks", "driver", "look", "wipe"]
    assert said["look_is_error"] is False
    assert said["look"] == '{"found": {"topic": "lathe"}}'


@pytest.mark.anyio
async def test_what_it_called_is_on_the_parents_record() -> None:
    """The whole point. A subscription pays for the reasoning; the acting is ours and it is
    written down — judged on effects, charged to the lease, on the event stream."""
    _, events = await with_a_child_over_a_socket()

    invoked = [e for e in events if isinstance(e, Invoked) and e.component == "look"]
    observed = [e for e in events if isinstance(e, Observed) and e.step != "s1"]

    assert len(invoked) == 1, "another process called a tool and the parent has no record of it"
    assert observed, "the child's answer never reached the parent's stream"
    assert invoked[0].run_id != events[0].run_id, "it should carry a child run id"


@pytest.mark.anyio
async def test_the_relay_refuses_plainly_when_there_is_nothing_to_reach() -> None:
    """A relay that hung, or exited zero having done nothing, would look to a CLI exactly like an
    MCP server with no tools — which reads as a model that chose not to use any."""
    import subprocess

    finished = subprocess.run(
        RELAY,
        env={PORT_VARIABLE: "1", TOKEN_VARIABLE: "a-token-with-nothing-behind-it"},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert finished.returncode != 0
    assert "not there" in finished.stderr or "nothing to relay" in finished.stderr
