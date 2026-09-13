"""One thread, one holder — as a host across the wire sees it (Phase 29 group 2, D81).

`thread/list` rows say `held_by`; a thread another process holds is refused by name at
`thread/resume`; `turn/start {when}` names what a second turn does while one runs, and `reject`
comes back as the refusal it is. `ServeHost` names itself as the holder — host, pid, a nonce —
so two processes on one store never share a thread.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import anyio
import pytest

from shadow_hdk.adapters.environment import local_sandbox
from shadow_hdk.kernel import Turn
from shadow_hdk.kernel.ports import AgentSession
from shadow_hdk.runtime.environment import Mode
from shadow_hdk.serve import ServeHost, Settings
from shadow_hdk.wire.peer import RemoteError
from shadow_hdk.wire.sides import loopback

pytestmark = pytest.mark.anyio

ENFORCEABLE: Mode = "workspace-write" if local_sandbox() is not None else "full"


class SlowProvider:
    """Each turn waits to be released, so a second `turn/start` can arrive while one runs."""

    def __init__(self) -> None:
        self.current: asyncio.Event | None = None
        self.turns: list[str] = []

    async def running(self, count: int) -> None:
        for _ in range(300):
            if len(self.turns) >= count:
                return
            await asyncio.sleep(0.01)
        raise AssertionError(f"only {self.turns} reached the provider")

    async def open(self, **_: Any) -> AgentSession:
        provider = self

        class _Session:
            async def turn(self, prompt: str) -> Turn:
                mine = asyncio.Event()
                provider.current = mine
                provider.turns.append(prompt)
                await mine.wait()
                return Turn(text="said " + prompt)

            async def interrupt(self) -> bool:
                assert provider.current is not None
                provider.current.set()
                return True

            async def steer(self, text: str) -> bool:
                return False

            async def close(self) -> None:
                pass

            async def stream(self, prompt: str) -> Any:  # pragma: no cover
                raise NotImplementedError

        return cast(AgentSession, _Session())


def _host(tmp_path: Path, url: str) -> ServeHost:
    return ServeHost(Settings(root=tmp_path, mode=ENFORCEABLE, store=url), agent=SlowProvider())


async def test_the_list_says_who_holds_each_thread_and_a_second_host_is_refused(
    tmp_path: Path,
) -> None:
    url = f"sqlite:///{tmp_path}/live.sqlite"
    one, two = _host(tmp_path, url), _host(tmp_path, url)
    assert one.holder and two.holder and one.holder != two.holder
    try:
        async with loopback(threads=one) as (client, _r), loopback(threads=two) as (other, _s):
            await client.initialize()
            await other.initialize()
            started = await client.peer.call("thread/start", {"root": "", "mode": "", "name": ""})
            tid = started["thread_id"]
            listed = await client.peer.call("thread/list", {})
            (row,) = [t for t in listed["threads"] if t["id"] == tid]
            assert row["held_by"] == one.holder

            with pytest.raises(RemoteError, match=one.holder):
                await other.peer.call("thread/resume", {"thread_id": tid})

            await client.peer.call("thread/close", {"thread_id": tid})
            listed = await other.peer.call("thread/list", {})
            (row,) = [t for t in listed["threads"] if t["id"] == tid]
            assert row["held_by"] is None
            resumed = await other.peer.call("thread/resume", {"thread_id": tid})
            assert resumed["thread_id"] == tid
            listed = await client.peer.call("thread/list", {})
            (row,) = [t for t in listed["threads"] if t["id"] == tid]
            assert row["held_by"] == two.holder
    finally:
        await one.aclose()
        await two.aclose()


async def test_turn_start_names_what_a_second_turn_does(tmp_path: Path) -> None:
    host = _host(tmp_path, f"sqlite:///{tmp_path}/live.sqlite")
    provider = cast(SlowProvider, host._agent)  # noqa: SLF001 — the double handed in
    try:
        async with loopback(threads=host) as (client, _runtime):
            await client.initialize()
            started = await client.peer.call("thread/start", {"root": "", "mode": "", "name": ""})
            tid = started["thread_id"]
            with anyio.fail_after(30):
                first = asyncio.create_task(
                    client.peer.call("turn/start", {"thread_id": tid, "text": "one"})
                )
                await provider.running(1)
                with pytest.raises(RemoteError, match="turn-1"):
                    await client.peer.call(
                        "turn/start", {"thread_id": tid, "text": "two", "when": "reject"}
                    )
                with pytest.raises(RemoteError, match="sometime"):
                    await client.peer.call(
                        "turn/start", {"thread_id": tid, "text": "two", "when": "sometime"}
                    )
                second = asyncio.create_task(
                    client.peer.call(
                        "turn/start", {"thread_id": tid, "text": "three", "when": "interrupt"}
                    )
                )
                done = await first
                assert done["turn"]["outcome"] == "cancelled"
                await provider.running(2)
                assert provider.current is not None
                provider.current.set()
                done = await second
                assert done["turn"]["outcome"] == "completed" and done["turn"]["id"] == "turn-2"
    finally:
        await host.aclose()
