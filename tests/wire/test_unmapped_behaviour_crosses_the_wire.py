"""ENH-020 over the wire: `thread/start`, `thread/resume` and `thread/set_mode` say which behaviour
fields the provider could not take, so a host in any language can hide those controls."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec
from shadow_hdk.kernel import Ceiling, Floor, Lease
from shadow_hdk.kernel.providers import Behaviour
from shadow_hdk.runtime.threads import Thread
from shadow_hdk.wire.sides import loopback

from .test_a_thread_crosses_the_wire import ScriptedThreads

pytestmark = pytest.mark.anyio


class WordedThreads(ScriptedThreads):
    """The scripted host with a mode registry, over a provider that cannot take `system` or
    `model` — the shape of a product mode on Codex or OpenCode."""

    def __init__(self, tmp_path: Path) -> None:
        super().__init__(tmp_path)
        self.modes = ModeRegistry(
            (
                ModeSpec.of("worded", behaviour=Behaviour(system="be brief", model="fast")),
                ModeSpec.of("plain"),
            )
        )
        original = self.agent.open

        async def open(**kw: Any) -> Any:
            session: Any = await original(**kw)
            behaviour = kw.get("behaviour")
            session.unmapped = tuple(
                name
                for name in ("system", "model")
                if behaviour is not None and getattr(behaviour, name, None)
            )
            return session

        self.agent.open = open  # type: ignore[method-assign]

    async def open(
        self, *, root: str, mode: str, want: str | None, name: str, observer: Any, roots: Any = None
    ) -> Thread:  # noqa: E501
        thread = await Thread.open(
            agent=cast(Any, self.agent),
            ports=self._ports(observer),
            store=self.threads,
            root=root or str(self._tmp),
            lease=Lease(Ceiling(20, 600, None), Floor(0)),
            name=name,
            approvals=self.approvals,
            mode=mode,
            modes=self.modes,
            provider="scripted",
        )
        self.agent.reach = thread.registry.call
        return thread

    async def resume(self, thread_id: str, *, observer: Any) -> Thread:
        thread = await Thread.resume(
            thread_id,
            agent=cast(Any, self.agent),
            ports=self._ports(observer),
            store=self.threads,
            lease=Lease(Ceiling(20, 600, None), Floor(0)),
            approvals=self.approvals,
            modes=self.modes,
        )
        self.agent.reach = thread.registry.call
        return thread


async def test_start_resume_and_set_mode_say_what_was_not_taken(tmp_path: Path) -> None:
    threads = WordedThreads(tmp_path)
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        started = await host.peer.call("thread/start", {"root": str(tmp_path), "mode": "worded"})
        assert started["unmapped_behaviour"] == ["system", "model"]
        changed = await host.peer.call(
            "thread/set_mode", {"thread_id": started["thread_id"], "mode": "plain"}
        )
        assert changed["unmapped_behaviour"] == []
        await host.peer.call("thread/close", {"thread_id": started["thread_id"]})
        resumed = await host.peer.call("thread/resume", {"thread_id": started["thread_id"]})
        assert resumed["unmapped_behaviour"] == [], "resumed on the record's mode, `plain`"
        changed = await host.peer.call(
            "thread/set_mode", {"thread_id": started["thread_id"], "mode": "worded"}
        )
        assert changed["unmapped_behaviour"] == ["system", "model"]
