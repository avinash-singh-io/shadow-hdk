"""A rule with one implementation (D35, D53): every process the harness starts as a session
leader — one whose whole group must end when it ends, and when we end — is started by
`runtime.processes.start_held`, and nowhere else.

Found by BUG-033: the fifth copy of `create_subprocess_exec(..., start_new_session=True)` +
`hold(process)` was the one that did not exist (the MCP SDK spawned the battery), and the
fourth and fifth were about to diverge on how the group is ended. The walk is over every
package's source; a new adapter that starts its own leader fails the build with the name of the
one place to start it.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGES = Path(__file__).resolve().parents[2] / "src" / "shadow_hdk"
THE_PLACE = "src/shadow_hdk/runtime/processes.py"


def _starts_a_leader(node: ast.Call) -> bool:
    callee = node.func
    name = callee.attr if isinstance(callee, ast.Attribute) else getattr(callee, "id", "")
    if name not in ("create_subprocess_exec", "create_subprocess_shell", "Popen"):
        return False
    return any(
        k.arg == "start_new_session" and isinstance(k.value, ast.Constant) and k.value.value is True
        for k in node.keywords
    )


def _sites() -> list[str]:
    found: list[str] = []
    for source in sorted(PACKAGES.glob("**/*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _starts_a_leader(node):
                found.append(f"{source.relative_to(PACKAGES.parents[1])}:{node.lineno}")
    return found


def test_every_session_leader_is_started_by_start_held() -> None:
    elsewhere = [s for s in _sites() if not s.startswith(THE_PLACE)]
    assert not elsewhere, (
        f"these start a session leader on their own: {elsewhere} — start it with "
        "`runtime.processes.start_held`, which holds it (D53) and is the one place its ending "
        "is decided (D35)"
    )


def test_the_one_place_exists_and_starts_one() -> None:
    sites = [s for s in _sites() if s.startswith(THE_PLACE)]
    assert len(sites) == 1, f"exactly one leader-starting call in {THE_PLACE}: {sites}"


def test_the_walk_sees_a_leader_it_would_refuse(tmp_path: Path) -> None:
    (tmp_path / "x.py").write_text(
        "import asyncio\nasync def f():\n"
        "    await asyncio.create_subprocess_exec('a', start_new_session=True)\n",
        encoding="utf-8",
    )
    tree = ast.parse((tmp_path / "x.py").read_text(encoding="utf-8"))
    assert [
        n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and _starts_a_leader(n)
    ] == [3]
