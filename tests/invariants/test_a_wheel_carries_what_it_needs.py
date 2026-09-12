"""What a package declares is what a package needs, and it says so in types (TD-003).

Every test here reads the shipped metadata rather than the source, because the failure this file
exists to catch only happens to somebody who installed one wheel and not the workspace. Inside the
workspace `uv` resolves everything and each of these bugs is invisible.

Four claims:

1. **The wire imports no adapter.** It reached into `adapters.basic` for a clock, and declared
   kernel and runtime only — so `shadow-hdk-wire` installed on its own raised `ImportError` the
   first time a host called `ports()`. It is the same rule as *no adapter imports another*, one
   layer up, and the same remedy: what two layers need moves below both.
2. **Every package the gate covers has a rule here.** BUG-007 was a package the gate silently
   skipped; a package no invariant names is the same shape waiting to happen.
3. **Intra-workspace dependencies are pinned.** D9 moves every package together on a contract
   change, so an unbounded `shadow-hdk-kernel` lets a resolver pair adapters 0.12.0 with a
   kernel from before the field they need existed — and the error surfaces as an `AttributeError`
   in somebody else's deployment.
4. **Every package ships `py.typed`.** Without the marker a downstream `mypy` reports
   `import-untyped` and every one of our carefully typed surfaces arrives as `Any`.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from tests.invariants.test_stands_alone import ADAPTERS, PACKAGES, _sources, adapter_violations

WIRE = PACKAGES / "wire" / "src" / "shadow_hdk" / "wire"

INTRA = (
    "shadow-hdk",
    "shadow-hdk-kernel",
    "shadow-hdk-wire",
    "shadow-hdk-providers",
    "shadow-hdk-serve",
)
"""Our own distributions. Anything else is somebody's release, pinned by range and not equality."""


def _packages() -> list[Path]:
    return sorted(
        [
            PACKAGES / "kernel",
            PACKAGES / "runtime",
            PACKAGES / "wire",
            PACKAGES / "providers",
            PACKAGES / "serve",
        ]
        + [p for p in ADAPTERS.glob("*") if p.is_dir()]
    )


def _metadata(package: Path) -> dict[str, object]:
    return tomllib.loads((package / "pyproject.toml").read_text(encoding="utf-8"))


def _declared(package: Path) -> list[str]:
    project = _metadata(package)["project"]
    assert isinstance(project, dict)
    return [str(d) for d in project.get("dependencies", [])]


def test_the_wire_imports_no_adapter() -> None:
    """`test_the_runtime_imports_no_adapter` one layer along. The wire is the runtime reachable from
    another process, and a wire that needs an adapter is a wire a host cannot install."""
    violations = adapter_violations(_sources(WIRE), own=None)

    assert not violations, "the wire knows an adapter:\n  " + "\n  ".join(violations)


def test_the_wire_walk_looks_where_the_code_is() -> None:
    """The anti-vacuity half. A rule that walks an empty directory proves nothing, and this one
    would have walked an empty directory for nine phases without anybody noticing."""
    assert len(_sources(WIRE)) >= 3, "the wire walk found nothing"


def test_every_intra_workspace_dependency_is_pinned() -> None:
    """D9 says every package moves together on a contract change, so the wheels must say so.

    Equality rather than a range, because *together* is the whole rule: a floor would let a
    resolver pair today's adapters with a kernel from four contract changes ago, and the failure
    lands as an `AttributeError` in a deployment nobody here can see.
    """
    version = _version()
    loose = [
        f"{package.name}: {declared}"
        for package in _packages()
        for declared in _declared(package)
        if _distribution(declared) in INTRA and not _pinned(declared, version)
    ]

    assert not loose, "an unpinned dependency on our own package:\n  " + "\n  ".join(loose)


def test_the_pin_check_reads_the_name_and_not_the_spelling() -> None:
    """Found by a mutation that survived: a check comparing whole strings passed `>=0.12.0`, which
    is a floor and exactly the thing this rule exists to forbid. The name is parsed out and the
    specifier compared to one permitted form, so every other spelling is caught by construction.
    """
    assert _distribution("shadow-hdk-kernel>=0.12.0") == "shadow-hdk-kernel"
    assert _distribution("shadow-hdk-kernel==0.12.0") == "shadow-hdk-kernel"
    assert _distribution("shadow-hdk-kernel") == "shadow-hdk-kernel"
    assert _distribution("langgraph>=1.2,<2") == "langgraph"
    assert _distribution("shadow-hdk[serve]==0.12.0") == "shadow-hdk"


def _pinned(requirement: str, version: str) -> bool:
    """`name==X` or `name[extra]==X` — an extra is not a range."""
    name = _distribution(requirement)
    rest = requirement.strip()[len(name) :]
    if rest.startswith("["):
        rest = rest[rest.index("]") + 1 :]
    return rest == f"=={version}"


def _distribution(requirement: str) -> str:
    """The name out of a requirement, whatever follows it. `packaging` would do this and is not a
    dependency of the test suite; the grammar we actually write is this narrow."""
    return re.split(r"[\[<>=!~; ]", requirement.strip(), maxsplit=1)[0]


def test_every_package_ships_the_typing_marker() -> None:
    """Without `py.typed` a downstream `mypy` sees `import-untyped` and every surface we type with
    care arrives as `Any` — which is the same silence BUG-007 was, pointed at our users."""
    bare = [
        package.name for package in _packages() if not list((package / "src").rglob("py.typed"))
    ]

    assert not bare, f"packages that ship no py.typed marker: {sorted(bare)}"


def test_the_marker_is_inside_the_package_it_marks() -> None:
    """A marker beside the package rather than in it ships nothing and types nothing. This is the
    mistake that makes the previous test pass while the wheel is still untyped."""
    astray = [
        f"{package.name}: {marker.relative_to(package)}"
        for package in _packages()
        for marker in (package / "src").rglob("py.typed")
        if not (marker.parent / "__init__.py").exists()
    ]

    assert not astray, "a py.typed marker outside a package:\n  " + "\n  ".join(astray)


def test_this_file_covers_every_package_the_gate_does() -> None:
    """BUG-007's lesson, generalised: a package no invariant names is a package that can drift.

    `_packages()` is what every test above walks, so the claim is that it is the whole set — not
    that somebody remembered to add a line when a package was created.
    """
    on_disk = {p.name for p in ADAPTERS.glob("*") if p.is_dir() and (p / "pyproject.toml").exists()}
    walked = {p.name for p in _packages()}

    assert on_disk <= walked
    assert {"kernel", "runtime", "wire"} <= walked
    assert len(walked) == len(on_disk) + 5  # kernel, runtime, wire, providers, serve


def _version() -> str:
    project = _metadata(PACKAGES / "kernel")["project"]
    assert isinstance(project, dict)
    return str(project["version"])
