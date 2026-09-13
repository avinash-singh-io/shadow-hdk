"""The layering is a property, not a claim (09 §1, §3).

Four rules, all AST walks, all build failures rather than review comments:

1. **No product.** Nothing under ``src/shadow_hdk`` imports ``intent.*`` — the same mechanism that
   keeps Intent Studio's ``knowledge/`` liftable, pointed the other way.
2. **The kernel is pure.** Nothing under the kernel imports I/O, a clock, logging, or a framework.
   Frozen dataclasses and protocols only. The runtime is where LangGraph appears, and nowhere below.
3. **The runtime imports no adapter.** Arrows point one way: kernel ← runtime ← adapters. A runtime
   that knows an adapter's name has a favourite, and a favourite is a branch waiting to happen.
4. **No adapter imports another.** Each is meant to be replaceable on its own.
5. **The selection surface imports no adapter.** `providers` decides *which* model or agent to
   open, and a module that imported the two it chooses between would have a favourite and a
   hard dependency on both. It discovers them through entry points instead, which is what makes
   the dependency arrow point from detail to abstraction (D39) rather than the other way.

**Each rule is written once**, as a ``_violations`` function, and called from two places: the guard
that walks the real tree, and ``test_the_rules_catch_what_they_look_for``, which walks synthetic
files that *do* break them. That second caller is what stops all four from being vacuous — the real
tree is clean, so without it a deleted predicate leaves the suite green. A mutation check on
2026-09-10 proved exactly that, twice: first for the adapter rule, then for a version of this file
where the synthetic test carried its own copy of each predicate and therefore tested nothing.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ROOT / "src" / "shadow_hdk"
"""One distribution since 0.27.0 (D78); the parts are packages of the one tree, and every rule
below is about the parts, not about how they ship."""
KERNEL = PACKAGES / "kernel"
RUNTIME = PACKAGES / "runtime"
PROVIDERS = PACKAGES / "providers"
ADAPTERS = PACKAGES / "adapters"
EXAMPLES = ROOT / "examples"

ADAPTER_ROOT = "shadow_hdk.adapters"

PRODUCT_PREFIXES = ("intent", "intent_studio")

#: What a pure kernel may not touch. The list is the definition of "no I/O, no clock, no logging,
#: no framework" — extend it when a new way to cheat appears.
IMPURE = (
    "asyncio",
    "datetime",
    "httpx",
    "langchain",
    "langchain_core",
    "langgraph",
    "logging",
    "os",
    "pathlib",
    "random",
    "socket",
    "subprocess",
    "sys",
    "threading",
    "time",
    "uuid",
)


def _imports(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(), filename=str(path))
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.append((node.module, node.lineno))
        elif isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
    return found


def _sources(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _root_of(module: str) -> str:
    return module.split(".", 1)[0]


def _cite(path: Path, line: int, module: str) -> str:
    where = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    return f"{where}:{line}: {module}"


# --------------------------------------------------------------------------- the four rules


def product_violations(paths: Iterable[Path]) -> list[str]:
    return [
        _cite(path, line, module)
        for path in paths
        for module, line in _imports(path)
        if _root_of(module) in PRODUCT_PREFIXES
    ]


def purity_violations(paths: Iterable[Path]) -> list[str]:
    return [
        _cite(path, line, module)
        for path in paths
        for module, line in _imports(path)
        if _root_of(module) in IMPURE
    ]


def adapter_violations(paths: Iterable[Path], *, own: str | None) -> list[str]:
    """Reaching into an adapter. `own=None` forbids every adapter — the runtime's rule; a package
    name forbids every adapter but that one — an adapter's rule."""
    return [
        _cite(path, line, module)
        for path in paths
        for module, line in _imports(path)
        if module.startswith(ADAPTER_ROOT) and (own is None or not module.startswith(own))
    ]


# --------------------------------------------------------------------------- the guards


def test_the_selection_surface_imports_no_adapter() -> None:
    """Rule 5. `providers` hands back a `ModelPort` from one adapter or an `AgentPort` from another,
    and the naive way to write that imports both — which is a hard dependency on every provider it
    can ever choose between, and the opposite of the inversion D39 is for.

    Deferring the import inside a function does not evade this walk, and should not: a lazy import
    is still a dependency, it just fails later and somewhere less obvious.
    """
    violations = adapter_violations(_sources(PROVIDERS), own=None)
    assert not violations, "the selection surface knows an adapter:\n  " + "\n  ".join(violations)


def test_no_package_imports_a_product() -> None:
    violations = product_violations(_sources(PACKAGES))
    assert not violations, "the harness imports a product:\n  " + "\n  ".join(violations)


def test_the_kernel_is_pure() -> None:
    violations = purity_violations(_sources(KERNEL))
    assert not violations, "the kernel touches the world:\n  " + "\n  ".join(violations)


def test_the_runtime_imports_no_adapter() -> None:
    violations = adapter_violations(_sources(RUNTIME), own=None)
    assert not violations, "the runtime knows an adapter:\n  " + "\n  ".join(violations)


def test_no_adapter_imports_another() -> None:
    violations: list[str] = []
    packages = sorted(p for p in ADAPTERS.glob("*") if p.is_dir() and p.name != "__pycache__")
    for package in packages:
        violations += adapter_violations(_sources(package), own=f"{ADAPTER_ROOT}.{package.name}")
    assert not violations, "an adapter reaches sideways:\n  " + "\n  ".join(violations)


# --------------------------------------------------------------------------- the anti-vacuity pair


def test_the_walks_look_where_the_code_is() -> None:
    """A guard that walks an empty directory proves nothing."""
    assert len(_sources(KERNEL)) >= 8, "the kernel walk found nothing"
    assert len(_sources(RUNTIME)) >= 6, "the runtime walk found nothing"
    assert len(_sources(PROVIDERS)) >= 5, "the providers walk found nothing"


def test_the_rules_catch_what_they_look_for(tmp_path: Path) -> None:
    """The same four functions the guards use, over files that break every rule on purpose."""
    product = tmp_path / "leaks_a_product.py"
    product.write_text("from intent.domain.intents import Claim\nimport intent_studio\n")
    assert len(product_violations([product])) == 2

    world = tmp_path / "touches_the_world.py"
    world.write_text("import time\nfrom langgraph.graph import StateGraph\n")
    assert len(purity_violations([world])) == 2

    sideways = tmp_path / "reaches_sideways.py"
    sideways.write_text(f"from {ADAPTER_ROOT}.mcp import McpComponents\n")
    assert len(adapter_violations([sideways], own=None)) == 1
    assert len(adapter_violations([sideways], own=f"{ADAPTER_ROOT}.acp")) == 1
    assert adapter_violations([sideways], own=f"{ADAPTER_ROOT}.mcp") == []

    # Rule 5 shares `adapter_violations` with rules 3 and 4, so the synthetic case that breaks
    # it is the same file read with `own=None` — asserted here so deleting the guard above
    # cannot leave the suite green on a tree that happens to be clean.
    deferred = tmp_path / "imports_late.py"
    deferred.write_text(
        f"def open_it():\n    from {ADAPTER_ROOT}.acp import AcpAgent\n    return AcpAgent\n"
    )
    assert len(adapter_violations([deferred], own=None)) == 1, (
        "a deferred import is still a dependency and must still be caught"
    )

    clean = tmp_path / "clean.py"
    clean.write_text("from shadow_hdk.kernel import EffectProfile\n")
    assert product_violations([clean]) == purity_violations([clean]) == []
    assert adapter_violations([clean], own=None) == []
