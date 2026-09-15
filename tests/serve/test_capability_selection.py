"""One capability decision guards the facade and the deeper host before an agent opens."""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.adapters.environment import local_sandbox
from shadow_hdk.kernel import (
    EnvironmentRequirements,
    ExecutionRequirements,
    IncompatibleCapabilities,
    ModelResponse,
    ProviderCapabilities,
    ProviderRequirements,
)
from shadow_hdk.runtime.environment import Mode
from shadow_hdk.runtime.testing import ScriptedModel
from shadow_hdk.serve import Harness, ServeHost, Settings, a_thread
from shadow_hdk.testing import ScriptedAgent

pytestmark = pytest.mark.anyio

MODE: Mode = "workspace-write" if local_sandbox() is not None else "full"
CONTROLLED = ProviderCapabilities(tool_path="controlled", streaming="live")
UNCONTROLLED = ProviderCapabilities(tool_path="uncontrolled", streaming="live")
STRICT = ExecutionRequirements(
    provider=ProviderRequirements(tool_path="controlled", streaming="live"),
    environment=EnvironmentRequirements(
        writes_within="workspace" if MODE == "workspace-write" else "machine"
    ),
)


async def test_an_incompatible_handed_provider_is_refused_before_open(tmp_path: Path) -> None:
    agent = ScriptedAgent([])
    host = ServeHost(
        Settings(root=tmp_path, mode=MODE),
        agent=agent,
        provider_capabilities=UNCONTROLLED,
        requirements=STRICT,
    )
    try:
        with pytest.raises(IncompatibleCapabilities) as refused:
            await host.open(root="", mode="", want=None, name="")

        assert agent.opened == 0
        assert refused.value.compatibility.mismatches[0].axis == "tool_path"
        assert refused.value.available_provider is UNCONTROLLED
    finally:
        await host.aclose()


async def test_an_incompatible_handed_model_uses_the_same_pre_open_gate(tmp_path: Path) -> None:
    model = ScriptedModel([ModelResponse(text="must not be called")])
    host = ServeHost(
        Settings(root=tmp_path, mode=MODE),
        model=model,
        provider_capabilities=UNCONTROLLED,
        requirements=STRICT,
    )
    try:
        with pytest.raises(IncompatibleCapabilities) as refused:
            await host.open(root="", mode="", want=None, name="")

        assert model.requests == []
        assert refused.value.compatibility.mismatches[0].axis == "tool_path"
        assert refused.value.available_provider is UNCONTROLLED
    finally:
        await host.aclose()


async def test_a_compatible_selection_is_kept_for_the_thread(tmp_path: Path) -> None:
    agent = ScriptedAgent([])
    host = ServeHost(
        Settings(root=tmp_path, mode=MODE),
        agent=agent,
        provider_capabilities=CONTROLLED,
        requirements=STRICT,
    )
    try:
        thread = await host.open(root="", mode="", want=None, name="")
        selected = host.capabilities_for(thread.id)

        assert selected.compatibility.ok
        assert selected.provider is CONTROLLED
        assert selected.environment.writes in ("workspace", "machine")
        assert agent.opened == 1
        await thread.close()
    finally:
        await host.aclose()


async def test_the_facade_carries_the_same_requirements(tmp_path: Path) -> None:
    agent = ScriptedAgent([])
    harness = Harness(
        tmp_path,
        mode=MODE,
        agent=agent,
        provider_capabilities=UNCONTROLLED,
        requirements=STRICT,
    )

    with pytest.raises(IncompatibleCapabilities):
        await harness.open()
    assert agent.opened == 0
    await harness.close()


async def test_no_requirements_preserves_the_additive_compatibility_path(tmp_path: Path) -> None:
    agent = ScriptedAgent([])
    host = ServeHost(Settings(root=tmp_path, mode=MODE), agent=agent)
    try:
        thread = await host.open(root="", mode="", want=None, name="")
        assert host.capabilities_for(thread.id).compatibility.ok
        assert agent.opened == 1
        await thread.close()
    finally:
        await host.aclose()


async def test_the_deep_python_door_uses_the_same_selection(tmp_path: Path) -> None:
    agent = ScriptedAgent([])

    with pytest.raises(IncompatibleCapabilities):
        async with a_thread(
            tmp_path,
            mode=MODE,
            agent=agent,
            provider_capabilities=UNCONTROLLED,
            requirements=STRICT,
        ):
            pass

    assert agent.opened == 0
