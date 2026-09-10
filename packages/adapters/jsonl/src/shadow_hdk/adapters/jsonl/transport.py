"""This adapter, offered as a transport, and the socket closed around what it launches.

Declared in distribution metadata rather than imported, so the selection surface can hand back a
provider from here without depending on it (D39, and rule 5 of the stands-alone invariant).

**Where D42 lands for a CLI of this shape.** A coding CLI launches its own MCP servers from a
configuration it is handed. So the configuration it is handed names the run's registry, its own file
and shell tools are refused, and every other source of MCP servers is shut off. Then the only tools
it has are ours: what it writes and what it runs arrive as steps on our graph, judged on effects and
charged to the parent's lease. It reasons; we govern.

A provider whose dialect names no way to inject tools **cannot be governed this way**, and a caller
handing it tools is told so rather than being given a session that quietly ignores them.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.jsonl.session import JsonlSession
from shadow_hdk.kernel import AgentPort, AgentSession, Dialect, Provider, ToolSource


class UngovernableProvider(ValueError):
    """Tools were offered to a provider that has no way to be given them."""


def mcp_config_for(tools: tuple[ToolSource, ...]) -> str:
    """The `--mcp-config` payload naming the run's registry.

    Each source becomes a stdio server the CLI launches. What it launches is the relay, which
    connects back to the registry living in this process — the child believes it started a server,
    and the server it reached is the run's own.
    """
    servers: dict[str, Any] = {}
    for index, source in enumerate(tools):
        if source.kind != "mcp":
            raise UngovernableProvider(
                f"this transport serves tool sources of kind 'mcp'; {source.kind!r} is not one, "
                "and a provider launched without its tools looks exactly like one that chose "
                "not to use any"
            )
        command, *arguments = source.address.split()
        servers[f"shadow-hdk-{index}" if index else "shadow-hdk"] = {
            "command": command,
            "args": arguments,
            "env": dict(source.env),
        }
    return json.dumps({"mcpServers": servers})


def server_names(tools: tuple[ToolSource, ...]) -> set[str]:
    """What the injected servers are called — the names the CLI will prefix its tool ids with."""
    return {f"shadow-hdk-{i}" if i else "shadow-hdk" for i in range(len(tools))}


def argv_for(provider: Provider, tools: tuple[ToolSource, ...]) -> list[str]:
    """The launch arguments, with the registry wired in and the CLI's own tools refused."""
    dialect = provider.dialect or Dialect()
    argv = list(provider.launch_args)
    if not tools:
        return argv
    if not dialect.mcp_config_arg:
        raise UngovernableProvider(
            f"{provider.called} has no way to be handed tools, so nothing this run offers it could "
            "be governed; refusing rather than starting it ungoverned (D42)"
        )
    argv += [dialect.mcp_config_arg, mcp_config_for(tools)]
    argv += list(dialect.mcp_strict_args)
    if dialect.allow_arg:
        prefix = dialect.allow_tool_prefix
        argv += [dialect.allow_arg, *sorted(prefix + n for n in server_names(tools))]
    if dialect.disallow_arg and dialect.disallow:
        argv += [dialect.disallow_arg, *dialect.disallow]
    return argv


class JsonlProvider(AgentPort):
    """One CLI of this shape, opened as a governed agent provider."""

    def __init__(
        self, provider: Provider, *, binary: Path, env: Mapping[str, str], **extra: Any
    ) -> None:
        self._provider = provider
        self._binary = binary
        self._env = dict(env)
        self._extra = extra

    async def open(
        self, *, tools: tuple[ToolSource, ...] = (), workspace: str | None = None
    ) -> AgentSession:
        launched = self._provider.__class__(
            **{**self._provider.__dict__, "launch_args": tuple(argv_for(self._provider, tools))}
        )
        return JsonlSession(
            launched,
            binary=self._binary,
            env=self._env,
            workspace=Path(workspace) if workspace else self._extra.get("workspace"),
            tools=tools,
        )


async def open_agent(
    provider: Provider, *, binary: Path, env: Mapping[str, str], **extra: Any
) -> AgentPort:
    """The entry point named in `pyproject.toml`, called by `providers.open_with`."""
    return JsonlProvider(provider, binary=binary, env=env, **extra)


__all__ = [
    "JsonlProvider",
    "UngovernableProvider",
    "argv_for",
    "mcp_config_for",
    "open_agent",
    "server_names",
]
