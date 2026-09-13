"""Simple by default, deep by choice (principle 9), held as an invariant: the facade reaches only
**public** names of the packages it composes — every `from X import y` names a `y` in `X.__all__`,
and nothing it touches is spelled with a leading underscore — so nothing a product does through
`Harness` is closed to a product that goes one level down and composes the same ports itself.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FACADE = ROOT / "src" / "shadow_hdk" / "serve" / "facade.py"

STDLIB = {"asyncio", "collections", "dataclasses", "pathlib", "typing", "__future__"}


def _imports(tree: ast.Module) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.extend((node.module, alias.name) for alias in node.names)
        elif isinstance(node, ast.Import):
            found.extend((alias.name, "") for alias in node.names)
    return found


def test_every_name_the_facade_imports_is_public() -> None:
    tree = ast.parse(FACADE.read_text(encoding="utf-8"), filename=str(FACADE))
    private: list[str] = []
    for module, name in _imports(tree):
        top = module.split(".")[0]
        if top in STDLIB:
            continue
        assert top == "shadow_hdk", f"the facade imports {module}: only the harness's own"
        exported = getattr(importlib.import_module(module), "__all__", None)
        assert exported is not None, f"{module} publishes no __all__, so nothing in it is public"
        if name and name not in exported:
            private.append(f"{module}.{name}")
    assert not private, f"the facade reaches names that are not public: {private}"


def test_the_facade_touches_nothing_spelled_private() -> None:
    tree = ast.parse(FACADE.read_text(encoding="utf-8"), filename=str(FACADE))
    reached = sorted(
        {
            f"{FACADE.name}:{node.lineno}: .{node.attr}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and node.attr.startswith("_")
            and not node.attr.startswith("__")
            and not (isinstance(node.value, ast.Name) and node.value.id == "self")
        }
    )
    assert not reached, f"the facade reaches private attributes of what it composes: {reached}"


def test_the_walk_sees_what_it_refuses(tmp_path: Path) -> None:
    source = "from shadow_hdk.serve.host import _POLICY\nx = host._agent\n"
    tree = ast.parse(source)
    assert ("shadow_hdk.serve.host", "_POLICY") in _imports(tree)
    names = [n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)]
    assert names == ["_agent"]
    exported = importlib.import_module("shadow_hdk.serve.host").__all__
    assert "_POLICY" not in exported
