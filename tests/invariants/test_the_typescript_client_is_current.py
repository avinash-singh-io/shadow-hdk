"""The checked-in TypeScript types are a pure function of the published schemas (D68).

`clients/typescript/src/schemas/*.ts` is generated; if the schemas move and the generation is not
re-run, a host in TypeScript compiles against a contract that no longer exists. The walk
regenerates into a temp directory with the same command and diffs. Where node is absent the test
SKIPS with the reason — it never fails for want of a toolchain — and CI installs node so the check
runs there.
"""

from __future__ import annotations

import filecmp
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "clients" / "typescript"


def _node_ready() -> str | None:
    if shutil.which("node") is None:
        return "node is not on this machine"
    if not (CLIENT / "node_modules" / "json-schema-to-typescript").exists():
        return "clients/typescript has no node_modules (`npm install` there, never globally)"
    return None


def test_the_generated_types_match_the_schemas(tmp_path: Path) -> None:
    if why := _node_ready():
        pytest.skip(why)
    import os

    out = tmp_path / "out"
    finished = subprocess.run(
        ["node", str(CLIENT / "generate.mjs")],
        cwd=CLIENT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env={**os.environ, "SHADOW_HDK_SCHEMAS": str(ROOT / "schemas"), "SHADOW_HDK_OUT": str(out)},
    )
    assert finished.returncode == 0, finished.stderr[-800:]
    fresh = out / "schemas"
    checked_in = CLIENT / "src" / "schemas"
    names = sorted(p.name for p in checked_in.glob("*.ts"))
    assert names == sorted(p.name for p in fresh.glob("*.ts")), "a contract was added or removed"
    stale = [
        name for name in names if not filecmp.cmp(checked_in / name, fresh / name, shallow=False)
    ]
    assert not stale, (
        f"generated types are stale for {stale}: run `npm run generate` in clients/typescript"
    )
    assert filecmp.cmp(CLIENT / "src" / "schemas.ts", out / "schemas.ts", shallow=False)


def test_the_client_type_checks() -> None:
    if why := _node_ready():
        pytest.skip(why)
    finished = subprocess.run(
        ["npm", "run", "--silent", "check"],
        cwd=CLIENT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert finished.returncode == 0, (finished.stdout + finished.stderr)[-1200:]


def test_a_silent_stream_reattaches_with_its_cursor() -> None:
    if why := _node_ready():
        pytest.skip(why)
    built = subprocess.run(
        ["npm", "run", "--silent", "build"],
        cwd=CLIENT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert built.returncode == 0, (built.stdout + built.stderr)[-1200:]
    finished = subprocess.run(
        ["node", str(CLIENT / "dist" / "silence-smoke.js")],
        cwd=CLIENT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert finished.returncode == 0, (finished.stdout + finished.stderr)[-1200:]
    assert '"reattachCursor":"1"' in finished.stdout


def test_the_generator_reads_the_published_index() -> None:
    """The set of contracts the client carries is the set the wire publishes — no hand list."""
    import json

    index = json.loads((ROOT / "schemas" / "index.json").read_text(encoding="utf-8"))
    generated = {p.stem for p in (CLIENT / "src" / "schemas").glob("*.ts")}
    assert generated == set(index["contracts"]), generated ^ set(index["contracts"])
