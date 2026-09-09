"""The layering is a property, not a claim (09 §1, §3).

Four rules, all AST walks, all build failures rather than review comments:

1. **No product.** Nothing under ``packages/*/src`` imports ``intent.*`` — the same mechanism that
   keeps Intent Studio's ``knowledge/`` liftable, pointed the other way.
2. **The kernel is pure.** Nothing under the kernel imports I/O, a clock, logging, or a framework.
   Frozen dataclasses and protocols only. The runtime is where LangGraph appears, and nowhere below.
3. **The runtime imports no adapter.** Arrows point one way: kernel ← runtime ← adapters. A runtime
   that knows an adapter's name has a favourite, and a favourite is a branch waiting to happen.
4. **No adapter imports another.** Each is meant to be replaceable on its own.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ROOT / "packages"
KERNEL = PACKAGES / "kernel" / "src" / "shadow_hdk" / "kernel"
RUNTIME = PACKAGES / "runtime" / "src" / "shadow_hdk" / "runtime"
ADAPTERS = PACKAGES / "adapters"

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


def test_no_package_imports_a_product() -> None:
    violations = [
        f"{path.relative_to(ROOT)}:{line}: {module}"
        for path in _sources(PACKAGES)
        for module, line in _imports(path)
        if _root_of(module) in PRODUCT_PREFIXES
    ]
    assert not violations, "the harness imports a product:\n  " + "\n  ".join(violations)


def test_the_kernel_is_pure() -> None:
    violations = [
        f"{path.relative_to(ROOT)}:{line}: {module}"
        for path in _sources(KERNEL)
        for module, line in _imports(path)
        if _root_of(module) in IMPURE
    ]
    assert not violations, "the kernel touches the world:\n  " + "\n  ".join(violations)


def test_the_runtime_imports_no_adapter() -> None:
    violations = [
        f"{path.relative_to(ROOT)}:{line}: {module}"
        for path in _sources(RUNTIME)
        for module, line in _imports(path)
        if module.startswith("shadow_hdk.adapters")
    ]
    assert not violations, "the runtime knows an adapter:\n  " + "\n  ".join(violations)


def test_no_adapter_imports_another() -> None:
    """Live from the day `packages/adapters/` has two entries; harmless and honest before that."""
    violations: list[str] = []
    for adapter in sorted(p for p in ADAPTERS.glob("*") if p.is_dir()) if ADAPTERS.exists() else []:
        own = f"shadow_hdk.adapters.{adapter.name}"
        for path in _sources(adapter):
            for module, line in _imports(path):
                if module.startswith("shadow_hdk.adapters.") and not module.startswith(own):
                    violations.append(f"{path.relative_to(ROOT)}:{line}: {module}")
    assert not violations, "an adapter reaches sideways:\n  " + "\n  ".join(violations)


def test_the_walks_look_where_the_code_is() -> None:
    """A guard that walks an empty directory proves nothing."""
    assert len(_sources(KERNEL)) >= 8, "the kernel walk found nothing"
    assert len(_sources(RUNTIME)) >= 6, "the runtime walk found nothing"
