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
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any

from mcp import types
from pydantic import JsonValue

from shadow_hdk.kernel.composition import Binding, Composition, Invoke
from shadow_hdk.kernel.events import Asked as AskedEvent
from shadow_hdk.kernel.events import Observed
from shadow_hdk.kernel.events import Refused as RefusedEvent
from shadow_hdk.kernel.leases import Ceiling
from shadow_hdk.kernel.observations import Completed, Failed, Observation, Refused
from shadow_hdk.runtime import RunContext, resume, run


class RecordingServer:
    """Offers a run's visible components to a child, and routes every call back through the run."""

    def __init__(
        self,
        context: RunContext,
        *,
        name: str = "shadow-hdk",
        withhold: frozenset[str] | set[str] = frozenset(),
    ) -> None:
        self._context = context
        self.name = name
        self.calls = 0
        self.refused_connections = 0
        """Connections that presented the wrong token, or none (D52). A count, never a credential:
        what was presented is not kept. Hand `refuse` to `serve_over_socket` to keep it."""
        self._withheld = frozenset(withhold)
        """Components the parent keeps to itself.

        `visible()` answers *what may this run do*, which is not the same question as *what should
        this child be offered*. A host driving a provider through a component of its own — the step
        that holds the conversation open — would otherwise hand the child a tool that re-enters the
        conversation it is already inside. Withholding is the parent's call and needs no policy
        change to express.
        """

    def refuse(self) -> None:
        """One more connection turned away at the door."""
        self.refused_connections += 1

    # ------------------------------------------------------------------ what it offers

    async def tools(self) -> list[types.Tool]:
        """`RunContext.visible()`, translated. Not a second list, and not a second policy."""
        return [
            types.Tool(
                name=registration.component.interface.name,
                description=registration.component.interface.description or None,
                input_schema=dict(registration.component.interface.input_schema)
                or {"type": "object"},
            )
            for registration in await self._context.visible()
            if registration.component.interface.name not in self._withheld
        ]

    # ------------------------------------------------------------------ what it does

    async def call(
        self, name: str, arguments: Mapping[str, JsonValue] | None = None
    ) -> types.CallToolResult:
        """Route the child's call through the parent's run, and hand back what came out."""
        if name in self._withheld:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"no component named {name!r}")],
                isError=True,
            )
        self.calls += 1
        # `__` and not `:` — LangGraph reserves the colon for checkpoint namespaces, so a step id
        # carrying one fails at graph construction. The compiler learned this in Phase 0; a new
        # adapter minting its own step ids has to know it too.
        step = f"{self.name}__{name}__{self.calls}"
        composition = Composition(
            (
                Invoke(
                    id=step,
                    component=name,
                    inputs=tuple(
                        Binding(name=key, value=value) for key, value in (arguments or {}).items()
                    ),
                ),
            )
        )
        remaining = (await self._context.remaining_now()).ceiling
        if remaining.max_steps <= 0:
            return _error("the run has no steps left")

        # Its own id and a checkpointer of its own, so that if the policy asks, the nested run can
        # be resumed with the answer — `resume` needs both, and `spawn_options_now` mints neither.
        from langgraph.checkpoint.memory import InMemorySaver

        options = await self._context.spawn_options_now(
            Ceiling(
                max_steps=min(2, remaining.max_steps),
                max_wall_seconds=remaining.max_wall_seconds,
                max_cost_cents=remaining.max_cost_cents,
            ),
            run_id=self._context.ports.clock.new_id(),
            checkpointer=InMemorySaver(),
        )
        observation, question = await self._drive(
            run(composition, self._context.ports, options=options), step
        )
        while observation is None and question is not None:
            # **The policy asked, and the child is waiting on this very call** (BUG-021, D58). The
            # nested run parked; this step cannot — it is what keeps the provider alive — so the
            # question is put to the host live and the nested run resumed with the answer. A run
            # with nobody to ask is told so, and the answer is a refusal.
            answer = await self._context.ask(question)
            observation, question = await self._drive(
                resume(composition, answer, self._context.ports, options=options), step
            )
        return _as_result(observation)

    async def _drive(self, events: Any, step: str) -> tuple[Observation | None, str | None]:
        """Run the nested run out; say what the step observed, or what it asked."""
        observation: Observation | None = None
        question: str | None = None
        async for event in events:
            if isinstance(event, Observed) and event.step == step:
                observation = event.observation
            elif isinstance(event, RefusedEvent) and event.step == step:
                # **A refusal emits one event, not two** — the decision taken when the governed step
                # was written: the refusal *is* the record of what happened to that step, and a
                # second `Observed` saying the same thing is how two narrations come to disagree.
                # So a reader that watches only for `Observed` misses every refusal, which is what
                # the first version of this did.
                observation = Refused(event.reason)
            elif isinstance(event, AskedEvent) and event.step == step:
                question = event.question
        return observation, question

    # ------------------------------------------------------------------ the wire

    def attach(self, server: Any) -> None:
        """Wire `tools/list` and `tools/call` onto a low-level MCP server.

        The low level rather than the convenient one, because `MCPServer.add_tool` derives a schema
        from a Python signature and this registry's schemas belong to the components that published
        them. Carrying somebody else's schema verbatim is the whole job.
        """
        from mcp.types import CallToolRequestParams, PaginatedRequestParams

        async def list_tools(_ctx: Any, _params: PaginatedRequestParams | None) -> Any:
            return types.ListToolsResult(tools=await self.tools())

        async def call_tool(_ctx: Any, params: CallToolRequestParams) -> Any:
            return await self.call(params.name, params.arguments or {})

        server.add_request_handler("tools/list", PaginatedRequestParams, list_tools)
        server.add_request_handler("tools/call", CallToolRequestParams, call_tool)

    @asynccontextmanager
    async def served(self) -> AsyncIterator[Any]:
        """A low-level MCP server with this registry wired onto it, ready for any stream pair."""
        from mcp.server.lowlevel import Server

        server = Server(self.name)
        self.attach(server)
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
    return _error(f"the call ended as {observation.kind}")


def _error(text: str) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)], is_error=True)


__all__ = ["RecordingServer"]
