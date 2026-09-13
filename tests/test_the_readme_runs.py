"""The README's self-contained snippets run as printed.

The first code block a reader meets showed an `EffectProfile` with fields the kernel does not have
(`frozenset` scopes, a `reaches` set, a `Cost`) — true of an earlier draft, false of the kernel for
months, and the clean-venv proof of D78 was the first thing to run it. The three-lines snippet has
its own test; this holds the two blocks that need nothing but the kit.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from shadow_hdk.kernel import ASSUME_WORST, EffectProfile

README = Path(__file__).resolve().parents[1] / "README.md"


def _block(starting_with: str) -> str:
    readme = README.read_text(encoding="utf-8")
    found = re.search(rf"```python\n({re.escape(starting_with)}.*?)```", readme, re.S)
    assert found, f"the README has no python block starting {starting_with!r}"
    return found.group(1)


def test_the_effect_profile_block_is_the_kernels_shape() -> None:
    block = _block("from shadow_hdk.kernel import EffectProfile, ScopeSet")
    scope: dict[str, Any] = {}
    exec(block.replace("EffectProfile(\n", "profile = EffectProfile(\n", 1), scope)  # noqa: S102

    profile = scope["profile"]
    assert isinstance(profile, EffectProfile)
    assert profile.narrows(ASSUME_WORST), "the README's example is wider than the worst case"
    assert "workspace" in profile.writes


def test_the_bare_run_block_runs_with_no_model(capsys: Any) -> None:
    block = _block("from shadow_hdk.adapters.basic import AllowAll")
    scope: dict[str, Any] = {}
    exec(block, scope)  # noqa: S102 — the README, run
    asyncio.run(scope["main"]())

    kinds = [line.split()[0] for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert kinds[0] == "started" and kinds[-1] == "ended"
    assert "invoked" in kinds and "observed" in kinds
