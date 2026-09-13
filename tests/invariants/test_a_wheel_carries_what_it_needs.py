"""What the distribution declares is what its parts need, and it says so in types (TD-003, D78).

One distribution since 0.27.0: `shadow-hdk`, with the specialised SDKs as extras. Every test here
reads the shipped metadata and the source's imports rather than trusting either, because the
failure this file exists to catch only happens to somebody who installed the wheel — inside the
workspace `uv` resolves everything and each of these bugs is invisible.

Four claims:

1. **The wire imports no adapter.** It reached into `adapters.basic` for a clock once, so a host
   that only wanted the wire raised `ImportError` the first time it called `ports()`. Same rule as
   *no adapter imports another*, one layer up.
2. **A base install needs no extra.** Every part that is not behind an extra imports only what
   the base `dependencies` declare — at the top of a module or inside a function, because a lazy
   import is still a dependency, it just fails later.
3. **Every extra covers the part it exists for.** The adapter behind `[mqtt]` imports `paho`; the
   extra must declare `paho-mqtt`, and nothing else may import it outside that adapter.
4. **The distribution ships `py.typed`**, once, at its root — without the marker a downstream
   `mypy` reports `import-untyped` and every one of our typed surfaces arrives as `Any`.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

from tests.invariants.test_stands_alone import PACKAGES, _sources, adapter_violations

ROOT = Path(__file__).resolve().parents[2]
WIRE = PACKAGES / "wire"

#: import root → the distribution that provides it (the name a `pip install` line uses).
PROVIDED_BY: dict[str, str] = {
    "pydantic": "pydantic",
    "langgraph": "langgraph",
    "mcp": "mcp",
    "mcp_types": "mcp",
    "anyio": "anyio",
    "acp": "agent-client-protocol",
    "starlette": "starlette",
    "uvicorn": "uvicorn",
    "httpx": "httpx",
    "langchain": "langchain",
    "langchain_core": "langchain",
    "paho": "paho-mqtt",
    "opentelemetry": "opentelemetry-api",
    "opensandbox": "opensandbox",
    "ddgs": "ddgs",
}

#: The part behind each extra: what may import that extra's SDKs, and nothing else may.
BEHIND_AN_EXTRA: dict[str, tuple[str, ...]] = {
    "adapters/langchain": ("langchain",),
    "adapters/mqtt": ("mqtt",),
    "adapters/otel": ("otel",),
    "adapters/environment": ("sandbox",),  # the OpenSandbox backend only; the rest is base
    "serve": ("search",),  # the ddgs battery only; the rest is base
}


def _project() -> dict[str, Any]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert isinstance(project, dict)
    return project


def _base_requirements() -> list[str]:
    requirements = _project()["dependencies"]
    assert isinstance(requirements, list)
    return [str(r) for r in requirements]


def _names(requirements: list[str]) -> set[str]:
    return {re.split(r"[\s\[<>=!~;]", r, maxsplit=1)[0].lower() for r in requirements}


def _extras() -> dict[str, set[str]]:
    """Each extra's distributions, with `shadow-hdk[other]` self-references resolved — the way a
    resolver sees `[openai]`: langchain-openai *and* langchain."""
    declared = _project().get("optional-dependencies", {})
    assert isinstance(declared, dict)
    raw = {name: [str(r) for r in reqs] for name, reqs in declared.items()}

    def resolve(name: str, seen: frozenset[str] = frozenset()) -> set[str]:
        out: set[str] = set()
        for requirement in raw[name]:
            if requirement.startswith("shadow-hdk["):
                for inner in requirement[len("shadow-hdk[") : -1].split(","):
                    if inner not in seen:
                        out |= resolve(inner, seen | {name})
            else:
                out |= _names([requirement])
        return out

    return {name: resolve(name) for name in raw}


def _third_party_imports(paths: list[Path]) -> dict[str, set[str]]:
    """Import root → the files that import it; the stdlib and our own tree left out."""
    found: dict[str, set[str]] = {}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            for name in names:
                root = name.split(".")[0]
                if root in sys.stdlib_module_names or root == "shadow_hdk":
                    continue
                found.setdefault(root, set()).add(str(path.relative_to(ROOT)))
    return found


def _part_of(relative: str) -> str:
    inner = Path(relative).relative_to("src/shadow_hdk").parts
    return f"adapters/{inner[1]}" if inner[0] == "adapters" else inner[0]


def test_the_wire_imports_no_adapter() -> None:
    violations = adapter_violations(_sources(WIRE), own=None)
    assert not violations, "the wire knows an adapter:\n  " + "\n  ".join(violations)


def test_the_wire_walk_looks_where_the_code_is() -> None:
    assert len(_sources(WIRE)) >= 3, "the wire walk found nothing"


def test_a_base_install_needs_no_extra() -> None:
    base = _names(_base_requirements())
    extras = _extras()
    behind = {sdk for names in extras.values() for sdk in names if sdk != "shadow-hdk"}
    unprovided: list[str] = []
    for root, files in _third_party_imports(_sources(PACKAGES)).items():
        distribution = PROVIDED_BY.get(root)
        assert distribution, (
            f"{root!r} is imported by {sorted(files)} and no table says who provides it"
        )
        if distribution in base:
            continue
        assert distribution in behind, (
            f"{distribution} is imported by {sorted(files)} and declared nowhere"
        )
        allowed = {
            part
            for part, extra_names in BEHIND_AN_EXTRA.items()
            if any(distribution in extras[e] for e in extra_names)
        }
        for file in files:
            if _part_of(file) not in allowed:
                unprovided.append(
                    f"{file} imports {root} ({distribution}), which only an extra provides"
                )
    assert not unprovided, "a base install would fail here:\n  " + "\n  ".join(unprovided)


def test_every_extra_covers_the_part_it_exists_for() -> None:
    extras = _extras()
    for part, extra_names in BEHIND_AN_EXTRA.items():
        imported = {
            PROVIDED_BY[root]
            for root, files in _third_party_imports(_sources(PACKAGES / part)).items()
            if any(_part_of(f) == part for f in files)
        }
        covered = set().union(*(extras[e] for e in extra_names)) | _names(_base_requirements())
        missing = {d for d in imported if d not in covered and d != "shadow-hdk"}
        assert not missing, (
            f"{part} imports {sorted(missing)}; its extra(s) {extra_names} do not declare them"
        )


def test_the_all_extra_is_everything() -> None:
    extras = _extras()
    everything = set().union(*(v for k, v in extras.items() if k != "all"))
    assert extras["all"] == everything, f"[all] misses {sorted(everything - extras['all'])}"


def test_the_distribution_ships_the_typing_marker_once_at_its_root() -> None:
    markers = sorted(p.relative_to(ROOT) for p in PACKAGES.rglob("py.typed"))
    assert markers == [Path("src/shadow_hdk/py.typed")], markers


def test_the_walks_see_a_violation(tmp_path: Path) -> None:
    leaky = tmp_path / "leaky.py"
    leaky.write_text("import paho\n", encoding="utf-8")
    tree = ast.parse(leaky.read_text(encoding="utf-8"))
    roots = {n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)}
    assert roots == {"paho"} and PROVIDED_BY["paho"] == "paho-mqtt"
    assert _part_of("src/shadow_hdk/adapters/mqtt/link.py") == "adapters/mqtt"
    assert _part_of("src/shadow_hdk/serve/web.py") == "serve"
