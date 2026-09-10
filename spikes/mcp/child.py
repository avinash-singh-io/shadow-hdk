"""A child process that uses the parent's registry, believing it started an MCP server.

Run by `tests/adapters/recording/test_over_a_process.py`, never by hand. It speaks MCP as a
**client** over its own stdin and stdout, and writes what it saw to stderr as one JSON line —
stdout is the wire and may carry nothing else.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import anyio
from mcp import ClientSession
from mcp.server.stdio import stdio_server


async def main() -> None:
    # The stdio framing is symmetric — read fd 0, write fd 1 — so the server-side helper is also
    # what a client parked on a pipe needs. The SDK offers no client-side equivalent.
    async with (
        stdio_server() as (incoming, outgoing),
        ClientSession(incoming, outgoing) as session,
    ):
        await session.initialize()
        listed = await session.list_tools()
        called = await session.call_tool("look", {"topic": "lathe"})
        refused = await session.call_tool("wipe", {})
        said: dict[str, Any] = {
            "tools": sorted(tool.name for tool in listed.tools),
            "look": "".join(part.text for part in called.content if hasattr(part, "text")),
            "look_is_error": bool(called.is_error),
            "wipe_is_error": bool(refused.is_error),
            "wipe": "".join(part.text for part in refused.content if hasattr(part, "text")),
        }
        print(json.dumps(said), file=sys.stderr, flush=True)
        # `stdio_server` parks a reader on fd 0, which never closes while the parent is
        # serving, so returning normally would hang here. The work is done; leave.
        os._exit(0)


if __name__ == "__main__":
    anyio.run(main)
