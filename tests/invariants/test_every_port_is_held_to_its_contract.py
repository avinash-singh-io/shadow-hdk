"""Every implementation of a port is held to that port's contract, or exempt with a reason (TD-004).

The contract suites in `tests/adapters/contract/suites.py` are what makes a port a port rather than
a convention: an unknown id is an observation and not an exception, a registration round-trips
through JSON, an observation does too. Seven of fourteen adapters ran against them, and the other
seven were the ones nothing held to the shape.

**That is BUG-007's shape.** There, `mypy_path` omitted three packages and the wire — the one
package outside the net — was where nine errors sat. A net that covers half the surface reports on
half the surface, and the half it does not cover is the half nobody looks at.

So the wiring is not the fix; this file is. It scans the packages for classes that implement a port
and requires each one to appear below, either with the test module that contracts it — **which is
then checked to really contain that contract** — or with a reason it does not apply. A new adapter
cannot be added without answering the question, which is the only property that survives the next
fourteen.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ROOT / "packages"
TESTS = ROOT / "tests"

PORTS = {
    "ComponentPort": "ComponentPortContract",
    "ModelPort": "ModelPortContract",
    "GovernancePort": "GovernancePortContract",
    "SinkPort": "SinkPortContract",
    "ObserverPort": "ObserverPortContract",
    "ClockPort": "ClockPortContract",
}
"""Each port, and the suite that says what implementing it means."""

CONTRACTED: dict[str, str] = {
    # the adapters
    "AcpAgent": "tests/adapters/acp/test_agent.py",
    "AgentComponent": "tests/adapters/agent/test_agent_is_a_component.py",
    "AllowAll": "tests/adapters/basic/test_basic.py",
    "CallableComponents": "tests/adapters/basic/test_basic.py",
    "CallbackSink": "tests/adapters/basic/test_basic.py",
    "ContainedSandbox": "tests/adapters/contained/test_contained_is_a_component.py",
    "Controlled": "tests/adapters/basic/test_controlled.py",
    "DerivationComponents": "tests/adapters/derivation/test_derivation_is_a_component.py",
    "DeviceComponents": "tests/adapters/devices/test_devices_are_components.py",
    "FileSink": "tests/adapters/basic/test_basic.py",
    "LangChainModel": "tests/adapters/langchain/test_langchain.py",
    "Mailbox": "tests/adapters/basic/test_mailbox.py",
    "McpComponents": "tests/adapters/mcp/test_mcp.py",
    "ModeGovernance": "tests/adapters/modes/test_modes.py",
    "OpenTelemetryObserver": "tests/adapters/otel/test_otel_is_an_observer.py",
    "RuleGovernance": "tests/adapters/modes/test_rules.py",
    "StdoutObserver": "tests/adapters/basic/test_basic.py",
    "StdoutSink": "tests/adapters/basic/test_basic.py",
    "SubprocessSandbox": "tests/adapters/sandbox_subprocess/test_sandbox.py",
    "SystemClock": "tests/adapters/basic/test_basic.py",
    "WorkspaceComponents": "tests/adapters/workspace/test_workspace.py",
    # the runtime's own testing doubles, which hosts import and therefore depend on
    "CallbackObserver": "tests/adapters/contract/test_the_doubles.py",
    "FixedClock": "tests/adapters/contract/test_the_doubles.py",
    "InMemoryComponents": "tests/adapters/contract/test_the_doubles.py",
    "Judge": "tests/adapters/contract/test_the_doubles.py",
    "ListObserver": "tests/adapters/contract/test_the_doubles.py",
    "ListSink": "tests/adapters/contract/test_the_doubles.py",
    "RecordedModel": "tests/adapters/contract/test_the_doubles.py",
    "ScriptedModel": "tests/adapters/contract/test_the_doubles.py",
}
"""Implementation → the test module that runs a contract suite against it."""

EXEMPT: dict[str, str] = {}
"""Implementation → why no contract suite applies. Empty today, and kept because the next adapter
may well belong here: `mqtt` and `recording` implement no port at all and so never reach this file
— a link is a transport the devices adapter speaks over, and the recording server is the registry
exposed *outward*, which is the arrow pointing the other way."""


def _implementations() -> dict[str, Path]:
    """Every class under `packages/*/src` whose bases name a port."""
    found: dict[str, Path] = {}
    for source in sorted(PACKAGES.glob("**/src/**/*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                isinstance(base, ast.Name) and base.id in PORTS for base in node.bases
            ):
                found[node.name] = source
    return found


def unaccounted_for(
    implementations: Iterable[str], contracted: Mapping[str, str], exempt: Mapping[str, str]
) -> list[str]:
    """The rule, written once (TD-004).

    **Called from the guard below and from a synthetic case that breaks it**, which is what stops
    the guard being vacuous: the real tree is clean, so a deleted predicate leaves the suite green.
    `test_stands_alone.py` learned this the same way, twice, under a mutation pass — and a mutation
    pass caught this file with the identical hole before the pair existed.
    """
    return sorted(set(implementations) - set(contracted) - set(exempt))


def not_really_contracted(contracted: Mapping[str, str], root: Path) -> list[str]:
    """The other rule: a filename in a table is a promise, and this makes it one."""
    missing: list[str] = []
    for implementation, where in sorted(contracted.items()):
        path = root / where
        if not path.exists():
            missing.append(f"{implementation}: {where} does not exist")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        suites = {
            base.id
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
            for base in node.bases
            if isinstance(base, ast.Name)
        }
        if not suites & set(PORTS.values()):
            missing.append(f"{implementation}: {where} runs no contract suite")
    return missing


def test_every_port_implementation_is_accounted_for() -> None:
    """The whole point: a new adapter cannot appear without answering *is it contracted*."""
    unaccounted = unaccounted_for(_implementations(), CONTRACTED, EXEMPT)

    assert not unaccounted, (
        "these implement a port and no contract suite runs against them, and no reason is "
        f"recorded: {unaccounted}"
    )


def test_the_walk_finds_the_implementations() -> None:
    """A scan that finds nothing would make the guard above vacuous — the failure this repository
    has already had once, when `mypy_path` quietly covered three packages fewer than it claimed."""
    implementations = _implementations()

    assert len(implementations) >= 12, f"the walk found only {sorted(implementations)}"
    assert "AgentComponent" in implementations
    assert "OpenTelemetryObserver" in implementations


def test_nothing_is_listed_that_does_not_exist() -> None:
    """The other direction, and the one that rots silently: an entry left behind by a rename keeps
    the count looking right while covering nothing."""
    implementations = _implementations()
    stale = sorted((set(CONTRACTED) | set(EXEMPT)) - set(implementations))

    assert not stale, f"listed here but no longer implements a port: {stale}"


def test_each_named_module_really_runs_a_contract() -> None:
    """A filename in a table is a promise, and this is what makes it one. The module must exist and
    must contain a class inheriting one of the suites — not merely a test that mentions one."""
    missing = not_really_contracted(CONTRACTED, ROOT)

    assert not missing, "\n  ".join(["a named module does not hold its contract:", *missing])


# --------------------------------------------------------------------------- the anti-vacuity pair


def test_the_rules_catch_what_they_look_for(tmp_path: Path) -> None:
    """Both rules, run against cases that **do** break them.

    Without this the guards above pass on an empty predicate, because the real tree satisfies them.
    A mutation pass proved exactly that: deleting the body of either left the suite green.
    """
    assert unaccounted_for(["NewSink"], {}, {}) == ["NewSink"]
    assert unaccounted_for(["NewSink"], {"NewSink": "somewhere.py"}, {}) == []
    assert unaccounted_for(["NewSink"], {}, {"NewSink": "a reason"}) == []

    (tmp_path / "test_absent.py").write_text("", encoding="utf-8")
    (tmp_path / "test_mentions.py").write_text(
        "# ComponentPortContract appears only in a comment\nclass Thing:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "test_real.py").write_text(
        "class TestItIsAComponentPort(ComponentPortContract):\n    pass\n", encoding="utf-8"
    )

    assert not_really_contracted({"A": "gone.py"}, tmp_path) == ["A: gone.py does not exist"]
    assert not_really_contracted({"B": "test_mentions.py"}, tmp_path) == [
        "B: test_mentions.py runs no contract suite"
    ]
    assert not_really_contracted({"C": "test_real.py"}, tmp_path) == []


def test_every_suite_is_used_by_something() -> None:
    """A suite nobody inherits is a suite that cannot fail, and reads on the page as coverage."""
    used: set[str] = set()
    for source in sorted(TESTS.glob("**/*.py")):
        if source.name == "suites.py":
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                used |= {
                    base.id
                    for base in node.bases
                    if isinstance(base, ast.Name) and base.id in set(PORTS.values())
                }

    assert set(PORTS.values()) - used == set(), (
        f"suites nothing inherits: {sorted(set(PORTS.values()) - used)}"
    )
