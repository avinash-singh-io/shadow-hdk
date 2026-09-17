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
from dataclasses import replace
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.jsonl.session import JsonlSession
from shadow_hdk.kernel import AgentPort, AgentSession, Behaviour, Dialect, Provider, ToolSource
from shadow_hdk.kernel.providers import unmapped_behaviour


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


def _toml(value: Any) -> str:
    """A TOML literal for one override value — a string, a list of strings, or a flat table."""
    if isinstance(value, str):
        return json.dumps(value)  # TOML basic strings share JSON's escapes
    if isinstance(value, list):
        return "[" + ",".join(_toml(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(f"{k}={_toml(v)}" for k, v in value.items()) + "}"
    return json.dumps(value)


def mcp_overrides_for(flag: str, tools: tuple[ToolSource, ...]) -> list[str]:
    """The same servers as `mcp_config_for`, spelled as repeated `<flag> key=value` overrides for a
    CLI that takes its configuration that way (Codex: `-c mcp_servers.<name>.command=…`)."""
    servers = json.loads(mcp_config_for(tools))["mcpServers"]
    argv: list[str] = []
    for name, server in servers.items():
        for field in ("command", "args", "env"):
            argv += [flag, f"mcp_servers.{name}.{field}={_toml(server[field])}"]
    return argv


def server_names(tools: tuple[ToolSource, ...]) -> set[str]:
    """What the injected servers are called — the names the CLI will prefix its tool ids with."""
    return {f"shadow-hdk-{i}" if i else "shadow-hdk" for i in range(len(tools))}


def _behaviour_flags(dialect: Dialect, behaviour: Behaviour | None) -> list[str]:
    """A behaviour's set fields as this CLI's flags (D64); an unset field adds nothing."""
    if behaviour is None:
        return []
    by_field = {a.field: a.flag for a in dialect.behaviour_args}
    flags: list[str] = []
    for name, flag in by_field.items():
        value = getattr(behaviour, name, None)
        if name == "tools_offered":
            continue  # offered-set narrowing is the registry's, not a launch flag
        if value not in (None, "", ()):
            flags += [flag, str(value)]
    return flags


def argv_for(
    provider: Provider,
    tools: tuple[ToolSource, ...],
    *,
    behaviour: Behaviour | None = None,
) -> list[str]:
    """The launch arguments, with the registry wired in, the CLI's own tools refused, and the
    behaviour's flags (D64) added."""
    dialect = provider.dialect or Dialect()
    argv = list(provider.launch_args) + _behaviour_flags(dialect, behaviour)
    if not tools:
        return argv
    if not dialect.mcp_config_arg:
        raise UngovernableProvider(
            f"{provider.called} has no way to be handed tools, so nothing this run offers it could "
            "be governed; refusing rather than starting it ungoverned (D42)"
        )
    if dialect.mcp_config_shape == "overrides":
        argv += mcp_overrides_for(dialect.mcp_config_arg, tools)
    else:
        argv += [dialect.mcp_config_arg, mcp_config_for(tools)]
    argv += list(dialect.mcp_strict_args)
    if dialect.allow_arg:
        prefix = dialect.allow_tool_prefix
        argv += [dialect.allow_arg, *sorted(prefix + n for n in server_names(tools))]
    if dialect.allow_override and dialect.mcp_config_arg:
        for name in sorted(server_names(tools)):
            argv += [dialect.mcp_config_arg, dialect.allow_override.format(name=name)]
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
        self,
        *,
        tools: tuple[ToolSource, ...] = (),
        workspace: str | None = None,
        behaviour: Behaviour | None = None,
        resume: str | None = None,
    ) -> AgentSession:
        # `replace`, not `__class__(**__dict__)`: copying a frozen dataclass around its own
        # constructor discards every argument's type.
        launched = replace(
            self._provider,
            launch_args=tuple(argv_for(self._provider, tools, behaviour=behaviour)),
        )
        return JsonlSession(
            launched,
            binary=self._binary,
            env=self._env,
            workspace=Path(workspace) if workspace else self._extra.get("workspace"),
            tools=tools,
            resume=resume,
            unmapped=tuple(unmapped_behaviour(self._provider, behaviour)),
        )


async def open_agent(
    provider: Provider, *, binary: Path, env: Mapping[str, str], **extra: Any
) -> AgentPort:
    """The entry point named in `pyproject.toml`, called by `providers.open_with`."""
    return JsonlProvider(provider, binary=binary, env=env, **extra)


__all__ = [
    "JsonlProvider",
    "unmapped_behaviour",
    "UngovernableProvider",
    "argv_for",
    "mcp_config_for",
    "open_agent",
    "server_names",
]
