"""ENH-020, D64: a behaviour field the provider maps no flag for is *named*, never dropped.

Only `claude-code.toml` maps `system`, `append_system`, `model` and `effort`; Codex and OpenCode
map none. A host that set a system prompt or a model on such a thread used to get neither and no
word of it. Now the opened session says what it could not take, the thread carries it, and the
wire crosses it — so a host can hide the controls it cannot honour for that provider.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.adapters.jsonl.transport import JsonlProvider
from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec
from shadow_hdk.kernel import Ceiling, Floor, Lease
from shadow_hdk.kernel.providers import Behaviour
from shadow_hdk.providers import shipped
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink
from shadow_hdk.runtime.threads import InMemoryThreads, Thread
from shadow_hdk.testing import ScriptedAgent

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------- the session says


async def test_a_codex_session_names_the_fields_its_record_maps_no_flag_for(tmp_path: Path) -> None:
    provider = JsonlProvider(shipped()["codex"], binary=Path("/nonexistent/codex"), env={})
    session = await provider.open(
        workspace=str(tmp_path),
        behaviour=Behaviour(system="be brief", model="o3", effort="high"),
    )
    assert session.unmapped == ("system", "model", "effort"), "named, in the behaviour's order"


async def test_a_claude_code_session_maps_them_all(tmp_path: Path) -> None:
    provider = JsonlProvider(shipped()["claude-code"], binary=Path("/nonexistent/claude"), env={})
    session = await provider.open(
        workspace=str(tmp_path),
        behaviour=Behaviour(system="be brief", model="opus", effort="high"),
    )
    assert session.unmapped == ()


async def test_an_unset_behaviour_names_nothing(tmp_path: Path) -> None:
    provider = JsonlProvider(shipped()["codex"], binary=Path("/nonexistent/codex"), env={})
    session = await provider.open(workspace=str(tmp_path), behaviour=Behaviour())
    assert session.unmapped == ()


# ---------------------------------------------------------------- the thread carries it


class _CannotTakeSystem(ScriptedAgent):
    """A provider double whose sessions cannot take a system prompt or a model."""

    async def open(self, **kw: Any) -> Any:
        session: Any = await super().open(**kw)
        behaviour = kw.get("behaviour")
        session.unmapped = tuple(
            name
            for name in ("system", "model")
            if behaviour is not None and getattr(behaviour, name, None)
        )
        return session


async def test_the_thread_carries_what_the_provider_could_not_take_and_updates_on_set_mode(
    tmp_path: Path,
) -> None:
    modes = ModeRegistry(
        (
            ModeSpec.of("worded", behaviour=Behaviour(system="be brief", model="fast")),
            ModeSpec.of("plain"),
        )
    )
    agent = _CannotTakeSystem([([], "one"), ([], "two")])
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=Ports(
            model=None,
            components=(InMemoryComponents([]),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(20, 600, None), Floor(0)),
        modes=modes,
        mode="worded",
    )
    agent.reach = thread.registry.call
    try:
        assert list(thread.unmapped_behaviour) == ["system", "model"], "named at open"
        await thread.set_mode("plain")
        assert list(thread.unmapped_behaviour) == [], "a mode that sets nothing loses nothing"
        changed = await thread.conversation.set_mode("worded")
        assert changed is not None and list(changed.unmapped) == ["system", "model"]
        assert list(thread.unmapped_behaviour) == ["system", "model"]
    finally:
        await thread.close()
