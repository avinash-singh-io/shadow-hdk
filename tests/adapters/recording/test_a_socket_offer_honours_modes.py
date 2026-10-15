"""N-W0: the production socket wrapper, through a real relay and conversation."""

from pathlib import Path
from typing import Any, cast

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec
from shadow_hdk.adapters.recording import SocketOffer
from shadow_hdk.kernel import Ceiling, Completed, Floor, Lease, Turn
from shadow_hdk.kernel.providers import Behaviour
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink, make_registration
from shadow_hdk.runtime.threads import InMemoryThreads, Thread

pytestmark = pytest.mark.anyio


class SocketCli:
    def __init__(self) -> None:
        self.sources: Any = ()
        self.seen: list[Any] = []

    async def open(self, **kw: Any) -> Any:
        self.sources = kw["tools"]
        return self

    async def turn(self, prompt: str) -> Turn:
        source = self.sources[0]
        params = StdioServerParameters(command=source.address, env=dict(source.env))
        async with (
            stdio_client(params) as (incoming, outgoing),
            ClientSession(incoming, outgoing) as s,
        ):
            await s.initialize()
            self.seen.append(sorted(t.name for t in (await s.list_tools()).tools))
            self.seen.append(bool((await s.call_tool("read_it", {})).is_error))
            self.seen.append(bool((await s.call_tool("write_it", {})).is_error))
        return Turn(text="done")

    async def close(self) -> None:
        pass


@pytest.mark.parametrize("check", ["seen", "ran"])
async def test_socket_narrows_listing_and_calls_again_after_mode_switch(
    tmp_path: Path, check: str
) -> None:
    ran: list[str] = []

    async def read(_: Any) -> Completed:
        ran.append("read")
        return Completed("read")

    async def write(_: Any) -> Completed:
        ran.append("write")
        return Completed("write")

    cli = SocketCli()
    thread = await Thread.open(
        agent=cast(Any, cli),
        registry=SocketOffer(withhold={"turn"}),
        ports=Ports(
            model=None,
            components=(
                InMemoryComponents(
                    [(make_registration("read_it"), read), (make_registration("write_it"), write)]
                ),
            ),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
        modes=ModeRegistry(
            (
                ModeSpec.of("read", behaviour=Behaviour(tools_offered=("read_it",))),
                ModeSpec.of("write", behaviour=Behaviour(tools_offered=("write_it",))),
                ModeSpec.of("all"),
            )
        ),
        mode="read",
    )
    try:
        for mode in ("read", "write", "all"):
            if mode != "read":
                await thread.set_mode(mode)
            async for _ in thread.turn("go"):
                pass
    finally:
        await thread.close()
    actual = {"seen": cli.seen, "ran": ran}
    expected = {
        "seen": [
            ["read_it"],
            False,
            True,
            ["write_it"],
            True,
            False,
            ["read_it", "write_it"],
            False,
            False,
        ],
        "ran": ["read", "write", "read", "write"],
    }
    assert actual[check] == expected[check]
