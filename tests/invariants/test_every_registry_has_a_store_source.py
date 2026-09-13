"""Data changes live; code changes restart (principle 10, D66) — held as an invariant.

Every registry in the tree — a class whose name ends in `Registry` or `Rules`, or that wraps
components with switches — must take a `Store` as a source, and the source must exist by name.
A registry that could only be filled from code or files is a restart waiting to happen. The walk
is over `src/shadow_hdk`; the table says, for each registry, which store source feeds it and
which test proves a row written now is read at the next read.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGES = Path(__file__).resolve().parents[2] / "src" / "shadow_hdk"

LIVE: dict[str, tuple[str, str]] = {
    "ModeRegistry": ("store_modes", "tests/runtime/test_a_store_makes_every_registry_live.py"),
    "ActRules": ("store_rules", "tests/runtime/test_a_store_makes_every_registry_live.py"),
    "SkillRegistry": ("store_skills", "tests/runtime/test_a_store_makes_every_registry_live.py"),
    "Switched": ("store_switches", "tests/runtime/test_a_store_makes_every_registry_live.py"),
    "BatteryRegistry": ("store_batteries", "tests/serve/test_a_battery_is_a_file.py"),
}
"""Registry → (the store source that feeds it, the test that proves the next read sees a write)."""

LIVE_FUNCTIONS: dict[str, tuple[str, str]] = {
    "library_from": ("store_providers", "tests/runtime/test_a_store_makes_every_registry_live.py"),
}
"""A registry that is a function rather than a class — the provider library — and its source."""

NOT_A_REGISTRY: dict[str, str] = {
    "Registry": "the runtime's component registry — a union over the *ports* handed in, refreshed "
    "at every step; a store reaches it through `Switched` and any port a host wraps",
}
"""Classes the walk finds that are not registries in principle 10's sense, and why."""


def _classes() -> dict[str, Path]:
    found: dict[str, Path] = {}
    for source in sorted(PACKAGES.glob("**/*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ClassDef)
                and not node.name.startswith("Store")  # a source, not a registry
                and (
                    node.name.endswith("Registry")
                    or node.name.endswith("Rules")
                    or node.name == "Switched"
                )
            ):
                found[node.name] = source
    return found


def _functions() -> set[str]:
    names: set[str] = set()
    for source in sorted(PACKAGES.glob("**/*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        names.update(
            n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
        )
    return names


def test_every_registry_has_a_store_source() -> None:
    classes = _classes()
    unaccounted = sorted(set(classes) - set(LIVE) - set(NOT_A_REGISTRY))
    assert not unaccounted, (
        f"these registries have no store source and no reason recorded: {unaccounted} — "
        "a registry filled only from code or files is a restart waiting to happen (principle 10)"
    )


def test_every_named_source_exists_and_its_proof_is_a_real_test() -> None:
    functions = _functions()
    root = PACKAGES.parents[1]
    for registry, (source, proof) in {**LIVE, **LIVE_FUNCTIONS}.items():
        assert source in functions, f"{registry}: store source {source!r} does not exist"
        text = (root / proof).read_text(encoding="utf-8")
        assert source in text, f"{registry}: {proof} never uses {source}"
    for function in LIVE_FUNCTIONS:
        assert function in functions, f"{function} is listed as a registry and does not exist"


def test_nothing_is_listed_that_is_not_there() -> None:
    classes = _classes()
    stale = sorted((set(LIVE) | set(NOT_A_REGISTRY)) - set(classes))
    assert not stale, f"listed but no longer in the tree: {stale}"


def test_the_walk_sees_a_registry_it_would_refuse(tmp_path: Path) -> None:
    """The rule can be seen to work: a registry with no store source is caught."""
    (tmp_path / "x.py").write_text("class LonelyRegistry:\n    pass\n", encoding="utf-8")
    tree = ast.parse((tmp_path / "x.py").read_text(encoding="utf-8"))
    names = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    assert names == ["LonelyRegistry"]
    assert set(names) - set(LIVE) - set(NOT_A_REGISTRY) == {"LonelyRegistry"}
