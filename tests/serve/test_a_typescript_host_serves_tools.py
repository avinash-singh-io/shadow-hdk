"""ENH-031: tools as code from TypeScript, proven through a real wire two ways — HTTP and a spawned
stdio runtime. The TypeScript side is `host-tools-smoke.ts`; this file starts the runtime with the
scripted thread host whose agent calls `greet`, and reads what the TypeScript process saw."""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import anyio
import pytest

from tests.wire.test_a_hosts_tools_cross_on_the_thread_door import ToolCallingThreads

pytestmark = pytest.mark.anyio

CLIENT = Path(__file__).resolve().parents[2] / "clients" / "typescript"
SMOKE = CLIENT / "dist" / "host-tools-smoke.js"


def _node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not on this machine; the TypeScript client is proven where it is")
    if not (CLIENT / "dist" / "smoke.js").exists():
        pytest.skip("clients/typescript is not built here (`npm install && npm run build`)")
    assert SMOKE.exists(), "the client is built but host-tools-smoke.js is not in it"
    return node


def _saw(finished: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert finished.returncode == 0, finished.stderr[-1200:]
    seen: dict[str, Any] = json.loads(finished.stdout.strip().splitlines()[-1])
    return seen


async def test_a_typescript_tool_is_called_back_over_http(tmp_path: Path) -> None:
    node = _node()
    from shadow_hdk.wire import served_over_http

    threads = ToolCallingThreads(tmp_path, [("greet", {"name": "typescript"})])
    with anyio.fail_after(90):
        async with served_over_http(threads=threads) as address:
            finished = await asyncio.to_thread(
                subprocess.run,
                [node, str(SMOKE), "http", address],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
    seen = _saw(finished)
    assert seen["source"] == "host"
    assert seen["greeted"] == ["typescript"], "the function ran in the Node process"
    assert seen["observed"] == {
        "kind": "completed",
        "output": {"greeting": "hello, typescript — from typescript"},
    }


async def test_a_typescript_tool_is_called_back_over_a_spawned_stdio_runtime(
    tmp_path: Path,
) -> None:
    node = _node()
    command = [sys.executable, "-m", "tests.serve._stdio_runtime_double", str(tmp_path)]
    with anyio.fail_after(90):
        finished = await asyncio.to_thread(
            subprocess.run,
            [node, str(SMOKE), "stdio", *command],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            cwd=str(Path(__file__).resolve().parents[2]),
        )
    seen = _saw(finished)
    assert seen["how"] == "stdio"
    assert seen["source"] == "host"
    assert seen["greeted"] == ["typescript"]
    assert seen["observed"]["output"]["greeting"] == "hello, typescript — from typescript"
