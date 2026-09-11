"""The live proofs run on demand and never on a push (Phase 23, Group 5).

A workflow that calls real providers on every push spends money on every typo. The `live` job is
`workflow_dispatch` only, applies the `live` marker whatever it was asked to run, and prints why
each skipped test skipped — a green run has to be readable as "what could run, passed".

Read as text, not YAML: the file is ours, its shape is fixed, and a stub-less parser is one more
dependency for three assertions.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIVE = ROOT / ".github" / "workflows" / "live.yml"
ORDINARY = ROOT / ".github" / "workflows" / "ci.yml"


def triggers_of(text: str) -> list[str]:
    """The keys under `on:` — everything indented beneath it until the next top-level key."""
    block = re.search(r"^on:\n((?:[ \t]+.*\n|\n)*)", text, re.MULTILINE)
    assert block is not None, "no `on:` block"
    return re.findall(r"^  (\w+):", block.group(1), re.MULTILINE)


def test_it_runs_only_when_dispatched() -> None:
    assert triggers_of(LIVE.read_text()) == ["workflow_dispatch"], (
        "the live job must not run on push or PR"
    )


def test_it_selects_the_live_marker_and_explains_skips() -> None:
    runs = [line for line in LIVE.read_text().splitlines() if "pytest" in line]
    assert runs, "no pytest step"
    assert all("-m live" in line for line in runs)
    assert all("-rs" in line for line in runs), "skips must be explained, or green says nothing"


def test_the_ordinary_job_never_selects_live() -> None:
    assert "-m live" not in ORDINARY.read_text(), "CI on a push must never call a provider"
    assert "push" in triggers_of(ORDINARY.read_text())
