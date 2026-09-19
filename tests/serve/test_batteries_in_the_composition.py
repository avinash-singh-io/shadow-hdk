"""Batteries in the composition (Phase 27 group 2): `[tools] batteries = [...]` in `harness.toml`
switches them on; `ServeHost` opens them once for the process and offers their components beside
the environment's; `batteries/list` says what is on, off, or unavailable and why; the modes judge
them by their profiles; `aclose` stops their processes.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import anyio
import pytest

from shadow_hdk.adapters.environment import local_sandbox
from shadow_hdk.kernel import Turn
from shadow_hdk.kernel.ports import AgentSession
from shadow_hdk.runtime.environment import Mode
from shadow_hdk.serve import ServeHost, load_settings
from shadow_hdk.serve.config import Settings
from shadow_hdk.wire.sides import loopback

pytestmark = pytest.mark.anyio

LOOKING: Mode = "read-only" if local_sandbox() is not None else "full"
"""A mode whose ceiling offers a battery (D70): `read-only` reads the web as it reads anything;
where no sandbox can enforce a confined mode, `full`. Never `workspace-write`, which hides it;
`ask` (0.34, D138) offers it and asks before each call."""

REFERENCE_SERVER = Path(__file__).resolve().parents[1] / "adapters" / "mcp" / "server.py"


def _reference_battery(where: Path) -> Path:
    """A battery file over the suite's own MCP server, exposing `look_up` as `web_search`."""
    where.mkdir(parents=True, exist_ok=True)
    (where / "reference.toml").write_text(
        "[battery]\n"
        'id = "reference"\nname = "The reference server"\nkind = "mcp"\n'
        f'command = "{sys.executable}"\nargs = ["{REFERENCE_SERVER}"]\n'
        '[tools.web_search]\ntool = "look_up"\n'
        "effects = { reaches = true, contained = false }\n",
        encoding="utf-8",
    )
    return where


class LookingProvider:
    """Reads what is visible, calls `web_search` when it is there, says what it saw."""

    def __init__(self) -> None:
        self.reach: Any = None
        self.visible: list[str] = []

    async def open(self, *, tools: Any = (), workspace: Any = None, behaviour: Any = None) -> Any:
        provider = self

        class _Session:
            async def turn(self, prompt: str) -> Turn:
                from shadow_hdk.runtime import current_run

                context = current_run()
                assert context is not None
                provider.visible = sorted(r.id for r in await context.visible())
                if "web_search" in provider.visible:
                    answer = await provider.reach("web_search", {"topic": prompt})
                    found = answer.output if hasattr(answer, "output") else answer
                    return Turn(text=f"found {found['asset']}")
                return Turn(text="no web here")

            async def close(self) -> None:
                pass

            async def stream(self, prompt: str) -> AsyncIterator[Any]:  # pragma: no cover
                raise NotImplementedError
                yield

        return cast(AgentSession, _Session())


class BatteryHost(ServeHost):
    def __init__(self, settings: Settings) -> None:
        self.looking = LookingProvider()
        super().__init__(settings, agent=cast(Any, self.looking))

    async def open(self, **kw: Any) -> Any:
        thread = await super().open(**kw)
        self.looking.reach = thread.registry.call
        return thread


def test_settings_read_the_batteries_wanted_and_where_more_files_are(tmp_path: Path) -> None:
    (tmp_path / "harness.toml").write_text(
        '[environment]\nroot = "."\n[tools]\nbatteries = ["ddgs", "mine"]\ndir = "batteries"\n',
        encoding="utf-8",
    )
    settings = load_settings(tmp_path / "harness.toml")
    assert settings.batteries == ("ddgs", "mine")
    assert settings.batteries_dir == (tmp_path / "batteries").resolve()
    assert Settings(root=tmp_path).batteries == () and Settings(root=tmp_path).batteries_dir is None
    (tmp_path / "harness.toml").write_text('[tools]\nbattery = ["x"]\n', encoding="utf-8")
    with pytest.raises(ValueError, match="battery"):
        load_settings(tmp_path / "harness.toml")


async def test_a_battery_switched_on_is_offered_and_listed_and_an_absent_one_is_reported(
    tmp_path: Path,
) -> None:
    files = _reference_battery(tmp_path / "batteries")
    host = BatteryHost(
        Settings(
            root=tmp_path / "ws",
            mode=LOOKING,
            batteries=("reference", "ddgs", "nowhere"),
            batteries_dir=files,
        )
    )
    with anyio.fail_after(60):
        async with loopback(threads=host) as (client, _runtime):
            await client.initialize()
            started = await client.peer.call("thread/start", {})
            listed = await client.peer.call("batteries/list", {})
            by_id = {b["id"]: b for b in listed["batteries"]}
            assert by_id["reference"]["status"] == "on"
            assert by_id["reference"]["tools"] == ["web_search"]
            assert by_id["wigolo"]["status"] == "off", "shipped, not wanted"
            assert by_id["ddgs"]["status"] in ("on", "unavailable")
            if by_id["ddgs"]["status"] == "unavailable":
                assert (
                    "ddgs" in by_id["ddgs"]["problem"] and "pip install" in by_id["ddgs"]["problem"]
                )
            assert by_id["nowhere"]["status"] == "unavailable"
            assert "no battery" in by_id["nowhere"]["problem"]
            done = await client.peer.call(
                "turn/start", {"thread_id": started["thread_id"], "text": "lathe"}
            )
        held = [b.port for b in host.batteries_opened if b.port is not None]
        assert held, "the reference server was held open for the process"
        await host.aclose()
    assert done["turn"]["text"] == "found LATHE-3"
    assert "web_search" in host.looking.visible
    assert host.batteries_opened == (), "closed: nothing is held open after aclose"
    for port in held:
        assert await port.registrations() == [], "its session is gone, not just forgotten"


@pytest.mark.skipif(local_sandbox() is None, reason="no OS sandbox on this machine")
async def test_a_confined_mode_hides_the_battery_and_a_looking_mode_offers_it(
    tmp_path: Path,
) -> None:
    """The battery's profile says it reaches from its own process; the shipped modes judge it as
    they judge anything (D70) — no rule was added."""
    files = _reference_battery(tmp_path / "batteries")
    for mode, expected in (("workspace-write", False), ("read-only", True)):
        host = BatteryHost(
            Settings(root=tmp_path / "ws", mode=mode, batteries=("reference",), batteries_dir=files)
        )
        thread = await host.open(root="", mode=mode, want=None, name="tools", observer=None)
        try:
            with anyio.fail_after(60):
                async for _event in thread.turn("lathe"):
                    pass
        finally:
            await thread.close()
            await host.aclose()
        assert ("web_search" in host.looking.visible) is expected, (mode, host.looking.visible)


async def test_a_thread_takes_batteries_by_name(tmp_path: Path) -> None:
    """The Python door: `a_thread(..., batteries=[...])` — the same files, the same names."""
    from shadow_hdk.serve import a_thread

    files = _reference_battery(tmp_path / "batteries")
    looking = LookingProvider()
    with anyio.fail_after(60):
        async with a_thread(
            tmp_path / "ws",
            mode=LOOKING,
            agent=cast(Any, looking),
            batteries=("reference",),
            batteries_dir=files,
        ) as thread:
            looking.reach = thread.registry.call
            async for _event in thread.turn("press"):
                pass
    assert thread.record.turns[-1].text == "found PRESS-1"
