"""Every package under `packages/` is type-checked, and mypy is asked for that in writing.

BUG-007: `mypy_path` omitted `wire`, `contained` and `derivation`. All three ship `py.typed`, so
mypy resolved them through the editable install's `.pth` entries and reported them as clean
site-packages — the gate said *Success* over the other fourteen while nine errors sat in the wire.
A gate that silently narrows is worse than no gate, so the configuration is asserted here rather
than trusted, and the assertion is on the *set of packages*, so a package added later fails this
test on the day it is added instead of being quietly skipped.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _sources() -> set[str]:
    return {
        str(pyproject.parent.relative_to(ROOT) / "src")
        for pyproject in ROOT.glob("packages/**/pyproject.toml")
    }


def _config() -> dict[str, object]:
    with (ROOT / "pyproject.toml").open("rb") as raw:
        return dict(tomllib.load(raw))


def test_mypy_is_pointed_at_every_package() -> None:
    tool = _config()["tool"]
    assert isinstance(tool, dict)
    on_the_path = set(str(tool["mypy"]["mypy_path"]).split(":"))
    missing = _sources() - on_the_path
    assert not missing, (
        f"mypy_path omits {sorted(missing)}; they would be silenced as site-packages"
    )


def test_ruff_is_pointed_at_every_package() -> None:
    """The same trap for the linter: `src` decides first-party, so an omitted package has its
    imports sorted as third-party and its rules applied against the wrong assumptions."""
    tool = _config()["tool"]
    assert isinstance(tool, dict)
    entries = {part for entry in tool["ruff"]["src"] for part in str(entry).split(":")}
    missing = _sources() - entries
    assert not missing, f"ruff src omits {sorted(missing)}"
