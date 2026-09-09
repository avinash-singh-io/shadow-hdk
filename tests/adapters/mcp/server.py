"""A real MCP server, spoken to over stdio by the tests.

Not a fake: the adapter is exercised against the SDK's own server, over a pipe, in a subprocess.
What is being tested is the seam, and a seam tested against a stand-in for the other side is a seam
tested against your own idea of it.

Three tools on purpose:

* `look_up` — annotated read-only and closed-world, so its profile should come out narrow;
* `wipe` — annotated destructive, so it should come out irreversible;
* `append` — annotated **not** read-only and **not** destructive, which is the only shape that tells
  the destructive hint apart from the default: without it, ignoring the hint entirely would look
  exactly the same, and a mutation proved it did;
* `mystery` — **annotated with nothing**, so it must come out as the worst case rather than a guess.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

server = MCPServer(name="reference-server")


@server.tool(
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False),
    description="Look a topic up in the reference server.",
)
def look_up(topic: str) -> dict[str, object]:
    answers = {
        "lathe": {"asset": "LATHE-3", "mass_kg": 12, "line": 3},
        "lathe mass": {"mass_kg": 12, "measured": "2026-08-01"},
    }
    return answers.get(topic, {"unknown": topic})


@server.tool(
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True),
    description="Erase a record. There is no undo.",
)
def wipe(what: str) -> str:
    return f"wiped {what}"


@server.tool(
    annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False),
    description="Add a line. It changes things, but nothing is lost.",
)
def append(line: str) -> str:
    return f"appended {line}"


@server.tool(description="Nobody said what this does.")
def mystery(value: str) -> str:
    return f"mysteriously {value}"


@server.tool(description="Always fails, on purpose.")
def explode() -> str:
    raise RuntimeError("the reference server is unwell")


if __name__ == "__main__":
    server.run("stdio")
