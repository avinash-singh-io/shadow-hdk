"""First-use provisioning and cancellation own their processes and disposable directories."""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.browser import BrowserComponents, PlaywrightEngine
from shadow_hdk.adapters.browser import engine as implementation


async def test_construction_and_catalogue_do_not_import_or_provision_optional_engines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "uv", None)
    pack = BrowserComponents()
    registrations = await pack.registrations()
    assert {r.id for r in registrations} >= {"browser_open", "browser_screenshot"}


async def test_missing_binary_is_explicit_and_closes_the_started_driver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from playwright import async_api

    stopped: list[str] = []

    class Driver:
        chromium = type("Chromium", (), {"executable_path": str(tmp_path / "missing")})()

        async def stop(self) -> None:
            stopped.append("driver")

    class Start:
        async def start(self) -> Driver:
            return Driver()

    directories: list[Path] = []
    original = tempfile.TemporaryDirectory

    def directory(*args: Any, **kwargs: Any) -> Any:
        value = original(*args, **kwargs)
        directories.append(Path(value.name))
        return value

    monkeypatch.setattr(async_api, "async_playwright", Start)
    monkeypatch.setattr(tempfile, "TemporaryDirectory", directory)
    engine = PlaywrightEngine(install_browser=False)
    result = await engine.execute("open", {"url": "http://localhost"}, "missing")
    assert result.kind == "failed" and "playwright install chromium" in str(result)
    assert (stopped, [d.exists() for d in directories], engine._profiles) == (
        ["driver"],
        [False],
        {},
    )


async def test_cancelling_first_use_installation_stops_the_installer_and_reports_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = asyncio.Event()
    processes: list[asyncio.subprocess.Process] = []
    commands: list[tuple[Any, ...]] = []
    activities: list[tuple[str, str]] = []
    real_spawn = asyncio.create_subprocess_exec

    class Context:
        async def activity(self, kind: str, text: str) -> None:
            activities.append((kind, text))

    async def spawn(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
        commands.append(args)
        process = await real_spawn(sys.executable, "-c", "import time; time.sleep(300)", **kwargs)
        processes.append(process)
        started.set()
        return process

    monkeypatch.setattr(implementation, "current_run", Context)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    task = asyncio.create_task(PlaywrightEngine()._install())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert (commands, activities) == (
        [(sys.executable, "-I", "-m", "playwright", "install", "chromium")],
        [("install", "Installing Chromium for the optional browser component.")],
    )
    assert processes[0].returncode is not None, "cancelled provisioning must leave no installer"
