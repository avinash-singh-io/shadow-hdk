"""This adapter, offered as a transport the selection surface can find (D39).

`providers` must hand back a `ModelPort` from one adapter or an `AgentPort` from another without
importing either — rule 5 of the stands-alone invariant fails the build otherwise, and a lazy import
would not evade it. So the arrow is inverted: this package **declares** itself in its own
distribution metadata,

    [project.entry-points."shadow_hdk.transports"]
    acp = "shadow_hdk.adapters.acp.transport:open_agent"

and the surface looks the name up. The detail depends on the abstraction; nothing depends on this.

The same door is open to anybody: a third party shipping a transport we have never heard of declares
it the same way, and nothing in this repository changes.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.acp.agent import AcpAgent

from shadow_hdk.kernel import AgentPort, AgentSession, Provider, ToolSource
from shadow_hdk.kernel.effects import EffectProfile


class AcpProvider(AgentPort):
    """One provider, opened over ACP. Sessions are resident, per Phase 4's measurement."""

    def __init__(
        self,
        provider: Provider,
        *,
        binary: Path,
        env: Mapping[str, str],
        workspace: Path | None = None,
        effects: EffectProfile | None = None,
        **extra: Any,
    ) -> None:
        self._provider = provider
        self._binary = binary
        self._env = dict(env)
        self._workspace = workspace
        self._effects = effects or EffectProfile(costs=True)
        self._extra = extra

    async def open(
        self,
        *,
        tools: tuple[ToolSource, ...] = (),
        workspace: str | None = None,
        behaviour: Any = None,
    ) -> AgentSession:
        """Start the provider and hand back the resident session.

        `behaviour` is accepted so this opener satisfies the port (D64); ACP carries a system
        prompt and model in `session/new` rather than as launch flags, so mapping it is a
        follow-up when a host asks — until then a set behaviour is reported by the thread, not
        dropped.

        `tools` is where D42's socket closes: whoever called this built the registry's address, and
        it travels through here into the child's `session/new`. This adapter never learns whose
        registry it is, which is exactly why it can carry one.
        """
        where = Path(workspace) if workspace else self._workspace
        agent = AcpAgent(
            str(self._binary),
            self._provider.launch_args,
            name=self._provider.id,
            effects=self._effects,
            workspace=where,
            tools=tools,
            **self._extra,
        )
        return agent


async def open_agent(
    provider: Provider, *, binary: Path, env: Mapping[str, str], **extra: Any
) -> AgentPort:
    """The entry point. Named in `pyproject.toml`, called by `providers.open_with`."""
    return AcpProvider(provider, binary=binary, env=env, **extra)


__all__ = ["AcpProvider", "open_agent"]
