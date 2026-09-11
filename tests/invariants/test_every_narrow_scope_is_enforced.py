"""A narrow scope is a claim, and every claim names what makes it true (BUG-018).

This runtime governs by asking a component what it touches — six fields — and judging those,
never its name. So every guarantee rests on the answer being **true**, and BUG-018 was three
adapters, in three packages that cannot import each other, answering `{workspace}` for things that
reach the whole machine. The enforcement worked perfectly on a false input, three times.

The rule was already written down. `sandbox.py` said *a governance system fed a lie is worse than
one fed nothing* — and applied it to one field of three. A principle in prose is applied when
somebody remembers it. This file is the principle as a build failure.

**The rule.** An adapter that declares a scope narrower than *everything* for `reads` or `writes`
must appear below, naming the **mechanism** that makes the narrow claim true and the **test** that
proves the mechanism by trying to cross the boundary. Adding a narrow scope without answering is a
failure. So is naming a test that does not exist, or one that never mentions the boundary.

It is the same shape as `test_every_port_is_held_to_its_contract.py`, for the same reason: a table
a reader can audit, checked by a walk that cannot be forgotten.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = ROOT / "packages" / "adapters"
RUNTIME = ROOT / "packages" / "runtime" / "src" / "shadow_hdk" / "runtime"

ENFORCED_BY: dict[str, tuple[str, str]] = {
    "workspace": (
        "every path is resolved and must be relative to the root; hard links are refused",
        "tests/adapters/workspace/test_a_hard_link_is_not_confined.py",
    ),
    "sandbox_subprocess": (
        "narrow only when `contained=True`; an uncontained subprocess declares everything",
        "tests/adapters/sandbox_subprocess/test_it_declares_what_it_can_really_do.py",
    ),
    "acp": (
        "our fs doors resolve inside the workspace; the child's own tools declare everything "
        "unless the deployment is contained",
        "tests/adapters/acp/test_the_childs_own_tools_are_judged_honestly.py",
    ),
    "contained": (
        "containment is proven at construction by what is denied (D36), or the sandbox refuses "
        "to exist",
        "tests/adapters/contained/test_contained.py",
    ),
    "devices": (
        "the device contract: a sensor reads the world and an actuator writes it; neither has a "
        "filesystem or a socket to reach — the scope names a different thing, not a narrower one",
        "tests/adapters/devices/test_devices.py",
    ),
    "runtime:environment": (
        "the one derivation (D48): `{workspace}` only where `Isolation` says writes or reads are "
        "confined, and `Isolation` is set by a watched denial or an honest no, never by a wrapper",
        "tests/runtime/test_an_environment_has_a_mode.py",
    ),
}
# `environment` the adapter is deliberately absent: it declares no scope of its own. Every
# profile it registers comes from the runtime's derivation above — the whole point of Phase 22, one
# place to be wrong — and this invariant is precise enough to refuse a stale entry for it.
"""Adapter → (what makes the narrow claim true, the test that crosses the boundary to prove it)."""

BOUNDARY_WORDS = ("outside", "everything", "denied", "OutsideTheRoot", "confine", "world")
"""A test that proves a boundary has to talk about the boundary."""


def _declares_a_narrow_scope(source: Path) -> bool:
    """`ScopeSet.of(...)` anywhere in the file: a scope with a name is a scope that is not
    *everything*, and the question this file asks applies."""
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "of"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "ScopeSet"
        ):
            return True
    return False


def narrowing_adapters(adapters: Path, runtime: Path | None = None) -> set[str]:
    """Adapters by package name, and — because the derivation moved below them in Phase 22 —
    runtime modules by `runtime:<module>`. A rule that walked only adapters would have gone quiet
    the day the narrow scope moved into the runtime, which is the day it mattered most."""
    found = {
        package.name
        for package in sorted(p for p in adapters.glob("*") if p.is_dir())
        if any(_declares_a_narrow_scope(s) for s in package.glob("src/**/*.py"))
    }
    if runtime is not None and runtime.exists():
        found |= {
            f"runtime:{module.stem}"
            for module in sorted(runtime.glob("*.py"))
            if _declares_a_narrow_scope(module)
        }
    return found


def unaccounted_for(narrowing: Iterable[str], enforced: Mapping[str, tuple[str, str]]) -> list[str]:
    """The rule, written once and called from the guard and from a case that breaks it."""
    return sorted(set(narrowing) - set(enforced))


def not_really_proven(enforced: Mapping[str, tuple[str, str]], root: Path) -> list[str]:
    """A filename in a table is a promise; this makes it one."""
    missing: list[str] = []
    for adapter, (_, where) in sorted(enforced.items()):
        path = root / where
        if not path.exists():
            missing.append(f"{adapter}: {where} does not exist")
            continue
        text = path.read_text(encoding="utf-8")
        if not any(word in text for word in BOUNDARY_WORDS):
            missing.append(f"{adapter}: {where} never mentions the boundary it is meant to cross")
    return missing


# --------------------------------------------------------------------------- the guards


def test_every_adapter_that_narrows_a_scope_says_what_makes_it_true() -> None:
    unaccounted = unaccounted_for(narrowing_adapters(ADAPTERS, RUNTIME), ENFORCED_BY)

    assert not unaccounted, (
        "these adapters declare a scope narrower than everything and nothing records what makes "
        f"the claim true: {unaccounted} — BUG-018 was exactly this, three times"
    )


def test_each_named_proof_exists_and_crosses_the_boundary() -> None:
    missing = not_really_proven(ENFORCED_BY, ROOT)

    assert not missing, "\n  ".join(["a claimed proof is not one:", *missing])


def test_nothing_is_listed_that_no_longer_narrows() -> None:
    """The direction that rots silently: an entry left behind keeps the table looking complete."""
    stale = sorted(set(ENFORCED_BY) - narrowing_adapters(ADAPTERS, RUNTIME))

    assert not stale, f"listed but no longer declares a narrow scope: {stale}"


# --------------------------------------------------------------------------- the anti-vacuity pair


def test_the_walk_finds_the_adapters() -> None:
    found = narrowing_adapters(ADAPTERS, RUNTIME)

    assert len(found) >= 4, f"the walk found only {sorted(found)}"
    assert "runtime:environment" in found, "the runtime's derivation is not in the walk"
    assert "sandbox_subprocess" in found, "the adapter BUG-018 was found in is not in the walk"


def test_the_rules_catch_what_they_look_for(tmp_path: Path) -> None:
    """Both rules against cases that break them, because the real tree satisfies them once fixed
    and a deleted predicate would otherwise leave the suite green."""
    assert unaccounted_for(["new_adapter"], {}) == ["new_adapter"]
    assert unaccounted_for(["new_adapter"], {"new_adapter": ("how", "where.py")}) == []

    (tmp_path / "test_vague.py").write_text(
        "def test_it_works():\n    assert True\n", encoding="utf-8"
    )
    (tmp_path / "test_real.py").write_text(
        "def test_a_write_outside_is_denied():\n    assert True\n", encoding="utf-8"
    )
    assert not_really_proven({"a": ("how", "gone.py")}, tmp_path) == ["a: gone.py does not exist"]
    assert not_really_proven({"b": ("how", "test_vague.py")}, tmp_path) == [
        "b: test_vague.py never mentions the boundary it is meant to cross"
    ]
    assert not_really_proven({"c": ("how", "test_real.py")}, tmp_path) == []

    narrowing = tmp_path / "pkg" / "src" / "m.py"
    narrowing.parent.mkdir(parents=True)
    narrowing.write_text('from x import ScopeSet\nW = ScopeSet.of("workspace")\n', encoding="utf-8")
    wide = tmp_path / "other" / "src" / "m.py"
    wide.parent.mkdir(parents=True)
    wide.write_text("from x import ScopeSet\nE = ScopeSet(everything=True)\n", encoding="utf-8")
    assert narrowing_adapters(tmp_path) == {"pkg"}
