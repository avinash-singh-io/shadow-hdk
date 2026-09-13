"""The child is launched with **our** tools and no others (D42).

This is the claim that makes an agent provider as governed as a model provider. The provider owns
its loop — how many turns, which tool next, when it is done — and we own everything it can reach.
A file it writes, a command it runs and a claim it proposes all arrive as an `Invoke` on our graph,
judged on effects, charged to the parent's lease, on the event stream.

**The adapter never learns whose registry it is.** `ToolSource` is a kernel type: whoever opens the
session builds it and hands it over, and this adapter turns it into what ACP's `session/new` takes.
That is what lets the ACP adapter carry the recording server's address without importing the
recording adapter — rule 4 would fail the build for it, and the layering is the reason it does not
have to.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.acp import AcpAgent
from shadow_hdk.adapters.acp.agent import mcp_servers_from
from shadow_hdk.kernel import EffectProfile, ToolSource

OURS = ToolSource(kind="mcp", address="shadow-hdk://run/registry")
OVER_HTTP = ToolSource(kind="mcp-http", address="http://127.0.0.1:8931/mcp")


def test_a_tool_source_becomes_what_session_new_takes() -> None:
    made = mcp_servers_from((OURS,))

    assert len(made) == 1
    assert getattr(made[0], "name", None), "an MCP server entry with no name is unusable"


def test_an_http_tool_source_becomes_an_http_server() -> None:
    """A registry the child reaches over a socket rather than a pipe — which is the shape a child
    on another machine needs, and the one `serve_over_pipes` argued for."""
    made = mcp_servers_from((OVER_HTTP,))

    assert len(made) == 1
    assert getattr(made[0], "url", None) == "http://127.0.0.1:8931/mcp"


def test_a_tool_source_nobody_here_can_serve_is_refused_naming_it() -> None:
    """Silently dropping it would launch the child with **no** tools and look like a model that
    chose not to use any — the most expensive possible way to fail."""
    with pytest.raises(ValueError, match="carrier-pigeon"):
        mcp_servers_from((ToolSource(kind="carrier-pigeon", address="x"),))


def test_no_tools_is_no_servers_rather_than_an_error() -> None:
    """A session opened for a conversation that needs no tools is legitimate."""
    assert mcp_servers_from(()) == []


async def test_the_session_is_opened_with_them(tmp_path: Path) -> None:
    """The bug this closes: `new_session(cwd=…)` passed no `mcp_servers` at all, so the child was
    launched with whatever tools it brought and none of ours."""
    passed: list[Any] = []

    class Remembering(AcpAgent):
        async def start(self) -> None:
            passed.append(self._tools)

    agent = Remembering(
        "does-not-run", effects=EffectProfile(costs=True), workspace=tmp_path, tools=(OURS,)
    )
    await agent.start()

    assert passed == [(OURS,)]
