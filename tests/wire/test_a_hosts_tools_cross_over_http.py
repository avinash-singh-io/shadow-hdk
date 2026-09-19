"""ENH-030 over HTTP, where two connections are natural: the host's replies to the runtime's
`components.invoke` go up by POST (the MCP streamable-HTTP split), and a second connection that
resumes the thread with `host_components: true` brings its own tools in place of the first's."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import anyio
import pytest

from shadow_hdk.kernel import Completed, EffectProfile
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink, make_registration
from shadow_hdk.wire import connect_to, served_over_http

from .test_a_hosts_tools_cross_on_the_thread_door import ToolCallingThreads, host_ports
from .test_a_thread_crosses_the_wire import AllowAll

pytestmark = pytest.mark.anyio

SHOUT = make_registration("shout", effects=EffectProfile())


async def shout(inputs: Any) -> Any:
    return Completed({"shout": str(inputs.get("name", "")).upper()})


def second_hosts_ports() -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(SHOUT, shout)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


async def test_the_hosts_tool_is_called_back_over_http_and_a_new_host_replaces_it(
    tmp_path: Path,
) -> None:
    threads = ToolCallingThreads(tmp_path, [("greet", {"name": "http"})])
    with anyio.fail_after(60):
        async with served_over_http(threads=threads) as address:
            async with connect_to(address, host_ports()) as first:
                await first.initialize()
                started = await first.peer.call(
                    "thread/start",
                    {"root": str(tmp_path), "mode": "workspace-write", "host_components": True},
                )
                thread_id = started["thread_id"]
                tools = await first.peer.call("tools/list", {"thread_id": thread_id})
                assert {t["id"] for t in tools["tools"]} >= {"greet", "notify", "look"}
                done = await first.peer.call(
                    "turn/start", {"thread_id": thread_id, "text": "greet over http"}
                )
                assert done["turn"]["outcome"] == "completed"
                await first.peer.call("thread/close", {"thread_id": thread_id})
            # The first connection is gone. A second host resumes the thread with *its* tools.
            async with connect_to(address, second_hosts_ports()) as second:
                await second.initialize()
                await second.peer.call(
                    "thread/resume", {"thread_id": thread_id, "host_components": True}
                )
                tools = await second.peer.call("tools/list", {"thread_id": thread_id})
                ids = {t["id"] for t in tools["tools"]}
                assert "shout" in ids, "the new host's tool is there"
                assert "greet" not in ids, "the old host's tool went with the old host"
                await second.peer.call("thread/close", {"thread_id": thread_id})
