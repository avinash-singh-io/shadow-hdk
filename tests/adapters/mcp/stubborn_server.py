"""An MCP server that does not leave when its stdin closes — the shape a battery has when its
process outlives the harness (BUG-033). Real MCP over stdio while the pipe is open; after the
pipe closes it sleeps on, ignoring SIGTERM and SIGHUP, so only ending its *group* ends it."""

from __future__ import annotations

import contextlib
import signal
import sys
import time

from mcp.server.mcpserver import MCPServer

server = MCPServer(name="stubborn")


@server.tool(description="Say hello.")
def hello(name: str) -> str:
    return f"hello {name}"


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    with contextlib.suppress(Exception):  # whatever the pipe's closing raises, we stay
        server.run(transport="stdio")
    print("stubborn: stdin closed, staying", file=sys.stderr, flush=True)
    while True:
        time.sleep(1)
