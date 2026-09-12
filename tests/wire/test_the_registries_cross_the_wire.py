"""The registries a host shows — the tools a thread's agent is offered under its mode, and the
skills the composition carries — cross the wire as `tools/list` and `skills/list` (Phase 28
group 1). What a page shows beside the conversation is the harness's data, read by method.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.wire.sides import loopback
from tests.wire.test_a_thread_crosses_the_wire import ScriptedThreads

pytestmark = pytest.mark.anyio


async def test_tools_list_says_what_the_agent_is_offered_with_effects_and_judgement(
    tmp_path: Path,
) -> None:
    threads = ScriptedThreads(tmp_path)
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        started = await host.peer.call(
            "thread/start", {"root": str(tmp_path), "mode": "workspace-write"}
        )
        listed = await host.peer.call("tools/list", {"thread_id": started["thread_id"]})
    tools = {t["id"]: t for t in listed["tools"]}
    assert "look" in tools, sorted(tools)
    assert tools["look"]["judgement"] == "allow"
    assert tools["look"]["effects"]["reads"] == {"names": ["workspace"], "everything": False}
    assert tools["look"]["source"].endswith(":InMemoryComponents")
    assert tools["look"]["description"], "the line the model chooses by"
    assert "turn" not in tools, "the turn is the thread's own step, not a tool the agent is offered"


class _Skills:
    async def all(self) -> tuple[Any, ...]:
        from shadow_hdk.adapters.agent.skills import Skill

        return (
            Skill(
                name="verify", prompt="check", description="Check before done.", source="shipped"
            ),
            Skill(name="summarise", prompt="sum", needs=frozenset({"look"}), source="store"),
        )


async def test_skills_list_names_every_skill_with_its_source(tmp_path: Path) -> None:
    threads = ScriptedThreads(tmp_path)
    threads.skills = _Skills()
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        listed = await host.peer.call("skills/list", {})
    assert listed["skills"] == [
        {"name": "verify", "description": "Check before done.", "needs": [], "source": "shipped"},
        {"name": "summarise", "description": "", "needs": ["look"], "source": "store"},
    ]


async def test_without_a_skill_registry_the_list_is_empty(tmp_path: Path) -> None:
    threads = ScriptedThreads(tmp_path)
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        assert await host.peer.call("skills/list", {}) == {"skills": []}
