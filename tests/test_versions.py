"""Every package moves together until 1.0 (D9).

Pre-1.0 the four are one thing released four ways: a contract change is a minor bump here *and* a
row on `intent-ecosystem/lanes/board.md` under *Pins*, because the join with the product lane is the
only place two lanes can break each other.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "0.1.0"


def _packages() -> dict[str, str]:
    found = {}
    for pyproject in sorted(ROOT.glob("packages/**/pyproject.toml")):
        project = tomllib.loads(pyproject.read_text())["project"]
        found[project["name"]] = project["version"]
    return found


def test_every_package_is_at_the_same_version() -> None:
    versions = _packages()
    assert versions, "the version walk found no packages"
    assert set(versions.values()) == {EXPECTED}, versions


def test_the_four_packages_phase_zero_ships_are_all_here() -> None:
    assert set(_packages()) == {
        "shadow-hdk-kernel",
        "shadow-hdk",
        "shadow-hdk-adapters-basic",
        "shadow-hdk-adapters-agent",
    }
