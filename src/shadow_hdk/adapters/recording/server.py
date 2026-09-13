"""The run's registry, offered to a child agent as an MCP server.

`09` §8 and `08` §4.6: *the recording MCP server is not a component to build — it is a server whose
tool handlers are judge then commit. **Recording is a consequence of routing.***

Taken literally. `call` does not judge, or emit, or meter. It runs a **one-step composition as a
child of the parent run**, and then all of that arrives because it is what a run already does:

* governance judges the step, exactly as it judges the parent's own;
* `Invoked` and `Observed` land on the parent's stream carrying the child's run id, so a host
  watching the parent sees what the child did;
* the child's lease is carved from the parent's, so a child that calls forever is stopped by the
  ceiling it was carved from.

And what the child is *offered* is `RunContext.visible()` — the same computation the model sees, so
a narrowing mode narrows the child with nothing in between.

Since D62 the routing itself is the runtime's (`runtime.offer.Routing`) — a thread needs it
without a socket — and this server is the MCP transport in front of it: `tools/list` and
`tools/call` translated, nothing judged here. It is attached to one run at a time; a thread
attaches each turn's run and detaches after.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from typing import Any

from mcp import types
from pydantic import JsonValue

from shadow_hdk.kernel.observations import Completed, Failed, Observation, Refused
from shadow_hdk.runtime import RunContext
from shadow_hdk.runtime.offer import REFUSED_NOT_RUNNING, Routing


class RecordingServer(Routing):
    """Offers a run's visible components to a child, and routes every call back through the run."""

    def __init__(
        self,
        context: RunContext | None = None,
        *,
        name: str = "shadow-hdk",
        withhold: frozenset[str] | set[str] = frozenset(),
    ) -> None:
        """`withhold`: components the parent keeps to itself.

        `visible()` answers *what may this run do*, which is not the same question as *what should
        this child be offered*. A host driving a provider through a component of its own — the step
        that holds the conversation open — would otherwise hand the child a tool that re-enters the
        conversation it is already inside. Withholding is the parent's call and needs no policy
        change to express.
        """
        super().__init__(name=name, withhold=withhold)
        if context is not None:
            self.attach(context)
        self.refused_connections = 0
        """Connections that presented the wrong token, or none (D52). A count, never a credential:
        what was presented is not kept. Hand `refuse` to `serve_over_socket` to keep it."""
        self._notifiers: set[Callable[[str], Awaitable[None]]] = set()
        """One per live connection: how to send that connection a notification (BUG-032)."""

    def refuse(self) -> None:
        """One more connection turned away at the door."""
        self.refused_connections += 1

    # ------------------------------------------------------------------ what it offers

    async def tools(self) -> list[types.Tool]:
        """`RunContext.visible()`, translated. Not a second list, and not a second policy."""
        context = self.context
        if context is None:
            return []
        return [
            types.Tool(
                name=registration.component.interface.name,
                description=registration.component.interface.description or None,
                input_schema=dict(registration.component.interface.input_schema)
                or {"type": "object"},
            )
            for registration in await context.visible()
            if registration.component.interface.name not in self.withheld
        ]

    # ------------------------------------------------------------------ what it does

    async def call_tool(
        self, name: str, arguments: Mapping[str, JsonValue] | None = None
    ) -> types.CallToolResult:
        """Route the child's call through the attached run, in the vocabulary the child speaks."""
        return _as_result(await self.call(name, arguments))

    # ------------------------------------------------------------------ the wire

    def wire(self, server: Any) -> None:
        """Wire `tools/list` and `tools/call` onto a low-level MCP server.

        The low level rather than the convenient one, because `MCPServer.add_tool` derives a schema
        from a Python signature and this registry's schemas belong to the components that published
        them. Carrying somebody else's schema verbatim is the whole job.
        """
        from mcp.types import CallToolRequestParams, PaginatedRequestParams

        async def list_tools(_ctx: Any, _params: PaginatedRequestParams | None) -> Any:
            return types.ListToolsResult(tools=await self.tools())

        async def call_tool(_ctx: Any, params: CallToolRequestParams) -> Any:
            return await self.call_tool(params.name, params.arguments or {})

        server.add_request_handler("tools/list", PaginatedRequestParams, list_tools)
        server.add_request_handler("tools/call", CallToolRequestParams, call_tool)

    def watch(self, notify: Callable[[str], Awaitable[None]]) -> Callable[[], None]:
        """A connection that can carry a notification registers how; the transport calls this
        when it opens and the returned function when it closes."""
        self._notifiers.add(notify)
        return lambda: self._notifiers.discard(notify)

    async def changed(self) -> None:
        """Tell every connection to list again — MCP's `notifications/tools/list_changed`
        (BUG-032). Measured: the mode flipped and a resident CLI kept the catalogue it fetched
        under the old one until the thread was resumed. A connection that is gone is dropped, not
        raised over."""
        for notify in list(self._notifiers):
            try:
                await notify("notifications/tools/list_changed")
            except Exception:  # noqa: BLE001 — a connection's death is that connection's problem
                self._notifiers.discard(notify)

    @asynccontextmanager
    async def served(self) -> AsyncIterator[Any]:
        """A low-level MCP server with this registry wired onto it, ready for any stream pair."""
        from mcp.server.lowlevel import Server

        server = Server(self.name)
        self.wire(server)
        yield server


def _as_result(observation: Observation | None) -> types.CallToolResult:
    """An observation, in the vocabulary a child agent speaks.

    A refusal and a failure both arrive as errors, because both mean *it did not happen* — but the
    text says which, so an agent can tell "you may not" from "it broke" and choose differently.
    """
    match observation:
        case Completed(output=output):
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(output))]
            )
        case Refused(reason=reason):
            return _error(f"refused: {reason}")
        case Failed(error=error):
            return _error(f"failed: {error}")
        case None:
            return _error("the call produced no observation")
        case other:
            return _error(f"the call ended {other.kind}")


def _error(text: str) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=True)


__all__ = ["REFUSED_NOT_RUNNING", "RecordingServer"]
