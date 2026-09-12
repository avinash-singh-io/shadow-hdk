"""The TypeScript client, against a live `serve --http` (D68): the proof that a product in another
language can. Skips, never fails, where node is absent or the client is not built."""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from pathlib import Path

import anyio
import pytest

from shadow_hdk.serve import ServeHost
from shadow_hdk.serve.config import Settings
from tests.serve.test_serve_answers_a_host_in_any_language import ScriptedProvider

pytestmark = pytest.mark.anyio

CLIENT = Path(__file__).resolve().parents[2] / "clients" / "typescript"


async def test_the_typescript_client_starts_a_thread_and_turns_it(tmp_path: Path) -> None:
    node = shutil.which("node")
    smoke = CLIENT / "dist" / "smoke.js"
    if node is None:
        pytest.skip("node is not on this machine; the TypeScript client is proven where it is")
    if not smoke.exists():
        pytest.skip("clients/typescript is not built here (`npm install && npm run build`)")
    from shadow_hdk.wire import served_over_http

    host = ServeHost(Settings(root=tmp_path, mode="workspace-write"), agent=ScriptedProvider())
    with anyio.fail_after(90):
        async with served_over_http(threads=host) as address:
            finished = await asyncio.to_thread(
                subprocess.run,
                [node, str(smoke), address],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
    assert finished.returncode == 0, finished.stderr[-800:]
    seen = json.loads(finished.stdout.strip().splitlines()[-1])
    assert seen["text"] == "scripted: hello from typescript"
    assert seen["provider"] == "handed in"
    assert "item:turn-1" in seen["seen"] and "event:started" in seen["seen"]
    assert seen["modes"] == ["read-only", "workspace-write", "full"]
    assert seen["version"] == 0
