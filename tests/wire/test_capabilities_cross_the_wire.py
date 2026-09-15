"""Discovery, requirements, selections and typed mismatches cross the same wire."""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.adapters.environment import local_sandbox
from shadow_hdk.kernel import ProviderCapabilities
from shadow_hdk.serve import ServeHost, Settings
from shadow_hdk.testing import ScriptedAgent
from shadow_hdk.wire.peer import RemoteError
from shadow_hdk.wire.sides import loopback

pytestmark = pytest.mark.anyio

MODE = "workspace-write" if local_sandbox() is not None else "full"


async def test_thread_start_returns_the_same_accepted_selection(tmp_path: Path) -> None:
    host = ServeHost(
        Settings(root=tmp_path, mode=MODE),
        agent=ScriptedAgent([]),
        provider_capabilities=ProviderCapabilities(tool_path="controlled", streaming="live"),
    )
    try:
        async with loopback(threads=host) as (client, _runtime):
            await client.initialize()
            started = await client.peer.call(
                "thread/start",
                {
                    "requirements": {
                        "provider": {"tool_path": "controlled", "streaming": "live"},
                        "environment": {},
                    }
                },
            )

        assert started["capabilities"]["compatibility"]["mismatches"] == []
        assert started["capabilities"]["provider"]["tool_path"] == "controlled"
    finally:
        await host.aclose()


async def test_wire_refusal_carries_identical_typed_mismatches(tmp_path: Path) -> None:
    host = ServeHost(
        Settings(root=tmp_path, mode=MODE),
        agent=ScriptedAgent([]),
        provider_capabilities=ProviderCapabilities(tool_path="uncontrolled"),
    )
    try:
        async with loopback(threads=host) as (client, _runtime):
            await client.initialize()
            with pytest.raises(RemoteError) as refused:
                await client.peer.call(
                    "capabilities/check",
                    {
                        "mode": MODE,
                        "requirements": {
                            "provider": {"tool_path": "controlled"},
                            "environment": {},
                        },
                    },
                )

        assert refused.value.data["kind"] == "capability_mismatch"
        assert refused.value.data["mismatches"][0]["subject"] == "provider"
        assert refused.value.data["mismatches"][0]["axis"] == "tool_path"
        assert cast_agent(host).opened == 0
    finally:
        await host.aclose()


def cast_agent(host: ServeHost) -> ScriptedAgent:
    agent = host._agent  # noqa: SLF001 - asserting the handed test double was not opened
    assert isinstance(agent, ScriptedAgent)
    return agent


async def test_provider_discovery_exposes_capabilities(tmp_path: Path) -> None:
    host = ServeHost(Settings(root=tmp_path, mode=MODE), agent=ScriptedAgent([]))
    try:
        async with loopback(threads=host) as (client, _runtime):
            await client.initialize()
            listed = await client.peer.call("providers/list", {})

        assert {row["id"] for row in listed["providers"]} >= {
            "claude-code",
            "codex",
            "opencode",
        }
        assert all("capabilities" in row for row in listed["providers"])
    finally:
        await host.aclose()
