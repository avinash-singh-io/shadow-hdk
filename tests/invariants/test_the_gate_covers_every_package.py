"""Every source file in this tree is type-checked — measured, not trusted.

BUG-007: `mypy_path` omitted `wire`, `contained` and `derivation`. All three ship `py.typed`, so
mypy resolved them through the editable install's `.pth` entries and reported them as clean
site-packages — the gate said *Success* over the other fourteen while nine errors sat in the wire.
The first guard asserted the configuration. It was not enough: under the eighteen-package layout
the configuration named every package and mypy still discovered 253 of 371 files, because a PEP 420
namespace split across eighteen source roots is not a package mypy walks (D78 found it — one tree,
and 63 errors nobody had seen). So the guard below asks mypy itself what it would check and holds
that set against the files on disk; the configuration checks stay, because they say *why*.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHECKED_ROOTS = ("src", "tests", "examples")
"""Every directory that holds Python this repository owns; a new one is added here and to
`[tool.mypy] packages`, or the discovery test says which."""


def _sources() -> set[str]:
    """One distribution (D78): one source root, and every part must be reachable through it."""
    assert (ROOT / "src" / "shadow_hdk" / "kernel").is_dir()
    return {"src"}


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


def _on_disk() -> set[Path]:
    return {
        path.resolve()
        for root in CHECKED_ROOTS
        for path in (ROOT / root).rglob("*.py")
        if "__pycache__" not in path.parts
    }


def _discovered_by_mypy() -> set[Path]:
    """The files mypy would check, from its own option processing — the same `pyproject.toml`,
    the same `packages`, the same walk. Discovery only; nothing is type-checked here."""
    from mypy.main import process_options

    sources, _options = process_options(["--config-file", str(ROOT / "pyproject.toml")])
    return {Path(s.path).resolve() for s in sources if s.path and s.path.endswith(".py")}


def test_mypy_discovers_every_source_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """The measurement: the set mypy walks equals the set on disk. A file in a directory mypy does
    not reach is a file the gate does not cover, whatever the configuration says."""
    monkeypatch.chdir(ROOT)  # `mypy_path` is relative to the working directory, not the config
    discovered = _discovered_by_mypy()
    on_disk = _on_disk()

    missed = sorted(str(p.relative_to(ROOT)) for p in on_disk - discovered)
    assert not missed, f"mypy never sees these {len(missed)} files: {missed[:12]}"
    stray = sorted(str(p) for p in discovered - on_disk)
    assert not stray, f"mypy checks files outside {CHECKED_ROOTS}: {stray[:12]}"


def test_the_discovery_is_not_vacuous(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two empty sets are equal. The walk must find the tree — the count at D78 was 371 — and the
    file BUG-007 was found in."""
    monkeypatch.chdir(ROOT)
    discovered = _discovered_by_mypy()

    assert len(discovered) >= 300, f"mypy discovered only {len(discovered)} files"
    assert (ROOT / "src" / "shadow_hdk" / "wire" / "peer.py").resolve() in discovered
    assert (ROOT / "tests" / "invariants" / "test_the_gate_covers_every_package.py").resolve() in (
        discovered
    )
