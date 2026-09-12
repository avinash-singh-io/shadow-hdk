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
    assert seen["root"] == str(tmp_path) and seen["files"] == [], "the workspace, read (D69)"
    assert seen["mode_events"] == ["mode_changed"], "set_mode returned the record's own event"


def test_the_readme_snippet_is_what_the_smoke_run_runs(tmp_path: Path) -> None:
    """The README's TypeScript lines are run for real: every call in them is in `smoke.ts`, which
    the test above drives against a live server, and the snippet itself type-checks against the
    client as it is."""
    import re

    readme = (CLIENT.parents[1] / "README.md").read_text(encoding="utf-8")
    block = re.search(r"```ts\n(.*?)```", readme, re.S)
    assert block, "the README has the TypeScript snippet"
    smoke = (CLIENT / "src" / "smoke.ts").read_text(encoding="utf-8")
    for line in block.group(1).splitlines():
        statement = line.strip()
        if not statement or statement.startswith("import") or statement in ("}", "});"):
            continue
        if statement.startswith("const client"):
            continue  # the address is the test's, not a literal
        if "console.log" in statement or "process.stdout" in statement:
            continue  # what the snippet prints is its reader's business
        assert statement.split(" {")[0] in smoke, statement
    tsc = CLIENT / "node_modules" / ".bin" / "tsc"
    if shutil.which("node") is None or not tsc.exists():
        pytest.skip(
            "node or the client's typescript is not here; the snippet is checked where it is"
        )
    snippet = block.group(1).replace(
        'from "shadow-hdk-client"', f'from "{(CLIENT / "src" / "client.js").as_posix()}"'
    )
    # `.mts`: a module, so top-level `await` is allowed wherever the file happens to sit.
    (tmp_path / "snippet.mts").write_text(snippet, encoding="utf-8")
    checked = subprocess.run(
        [
            str(tsc),
            "--noEmit",
            "--strict",
            "--target",
            "es2022",
            "--module",
            "nodenext",
            "--moduleResolution",
            "nodenext",
            "--skipLibCheck",
            "--types",
            "node",
            "--typeRoots",
            str(CLIENT / "node_modules" / "@types"),
            str(tmp_path / "snippet.mts"),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert checked.returncode == 0, checked.stdout[-1500:] + checked.stderr[-500:]
