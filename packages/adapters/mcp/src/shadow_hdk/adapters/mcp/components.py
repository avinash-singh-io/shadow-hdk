"""An MCP server's tools become components.

This is how most components will arrive (`09` §4), and the interesting part is not the plumbing —
it is that **an effect profile is derived from what the server declares, and hardened where it
declares nothing.** MCP's annotations cover about half of our six fields; the rest stay at their
worst until a deployment says otherwise. A tool that says nothing at all is registered as
`ASSUME_WORST`, so a mode that forbids reaching outside refuses it, and the agent never sees it.

That is the whole reason the registry can be open: we govern effects, and an effect nobody vouched
for is assumed to be the worst one.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from contextlib import AsyncExitStack
from typing import Any

from pydantic import JsonValue

from shadow_hdk.kernel.components import (
    Component,
    Interface,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.observations import Completed, Failed, Observation
from shadow_hdk.kernel.ports import ComponentPort
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool


class McpComponents(ComponentPort):
    """One MCP server, held open.

    **The session's lifetime is the adapter's, not a run's.** A server is a process and a handshake;
    paying for both on every step would be absurd, and tying it to a run would end it when the run
    ended. Use it as an async context manager, or call `start` and `stop` yourself.
    """

    def __init__(
        self,
        parameters: StdioServerParameters,
        *,
        source: str = "mcp",
        at: str = "",
        prefix: str = "",
    ) -> None:
        self._parameters = parameters
        self._source = source
        self._at = at
        self._prefix = prefix
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._tools: dict[RegistrationId, str] = {}

    # ------------------------------------------------------------------ lifetime

    async def start(self) -> None:
        stack = AsyncExitStack()
        read, write = await stack.enter_async_context(stdio_client(self._parameters))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._stack, self._session = stack, session

    async def stop(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
        self._stack, self._session = None, None

    async def __aenter__(self) -> McpComponents:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()

    # ------------------------------------------------------------------ the port

    async def registrations(self) -> Sequence[Registration]:
        if self._session is None:
            return []
        listed = await self._session.list_tools()
        found = []
        for tool in listed.tools:
            registration = self._registration(tool)
            self._tools[registration.id] = tool.name
            found.append(registration)
        return found

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        if self._session is None:
            return Failed(f"{self._source!r} is not started")
        name = self._tools.get(registration)
        if name is None:
            # A catalogue read populates the map, and the runtime always refreshes before it
            # resolves — but an adapter used on its own should not need to know that.
            await self.registrations()
            name = self._tools.get(registration)
        if name is None:
            return Failed(f"no component registered as {registration!r}")
        arguments = dict(inputs) if isinstance(inputs, dict) else {}
        try:
            result: Any = await self._session.call_tool(name, arguments)
        except Exception as exc:  # noqa: BLE001 — a server is untrusted like any component (D7)
            return Failed(f"{type(exc).__name__}: {exc}")
        if getattr(result, "is_error", False):
            return Failed(f"{name}: {_text_of(result)}")
        structured = getattr(result, "structured_content", None)
        if structured is not None:
            return Completed(structured)
        return Completed(_as_json(_text_of(result)))

    # ------------------------------------------------------------------ derivation

    def _registration(self, tool: Tool) -> Registration:
        annotations = tool.annotations
        return Registration(
            id=f"{self._prefix}{tool.name}",
            component=Component(
                interface=Interface(
                    name=f"{self._prefix}{tool.name}",
                    description=tool.description or "",
                    input_schema=dict(tool.input_schema or {}),
                    output_schema=dict(tool.output_schema or {}),
                ),
                # **Derived, not trusted.** Absent annotations mean every hint is `None`, and the
                # kernel reads that as the worst case — never as "probably harmless".
                effects=EffectProfile.from_mcp_annotations(
                    read_only_hint=getattr(annotations, "read_only_hint", None),
                    destructive_hint=getattr(annotations, "destructive_hint", None),
                    idempotent_hint=getattr(annotations, "idempotent_hint", None),
                    open_world_hint=getattr(annotations, "open_world_hint", None),
                ),
                provenance=Provenance(registered_by=self._source, adapter="mcp", at=self._at),
                labels=frozenset({"tool"}),
            ),
        )


def _text_of(result: Any) -> str:
    return "".join(
        block.text for block in getattr(result, "content", ()) or () if hasattr(block, "text")
    )


def _as_json(text: str) -> JsonValue:
    """A server that answered with JSON meant JSON; one that answered with prose meant prose."""
    try:
        parsed: JsonValue = json.loads(text)
    except (ValueError, TypeError):
        return text
    return parsed


__all__ = ["McpComponents", "StdioServerParameters"]
