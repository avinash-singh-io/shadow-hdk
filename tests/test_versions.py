"""Every package moves together until 1.0 (D9).

Pre-1.0 the four are one thing released four ways: a contract change is a minor bump here *and* a
row on `intent-ecosystem/lanes/board.md` under *Pins*, because the join with the product lane is the
only place two lanes can break each other.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "0.4.0"
"""0.4.0 because `Ended` grew `detail` — the words of whoever stopped a run, so a host can tell a
cancellation from a ceiling from a broken port. 0.3.0 was `Provenance.posture`; 0.2.0 was
`ModelPort.stream`. Each is a contract change, so every package moves (D9)."""


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


def test_the_packages_every_phase_relies_on_are_still_here() -> None:
    """A subset, not an equality: each phase adds adapters, and a test that had to be edited every
    time one arrived would be edited without being read."""
    assert {
        "shadow-hdk-kernel",
        "shadow-hdk",
        "shadow-hdk-adapters-basic",
        "shadow-hdk-adapters-agent",
    } <= set(_packages())
