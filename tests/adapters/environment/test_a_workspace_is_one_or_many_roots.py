"""A workspace is one or many roots (Phase 28 group 3, D76): a thread works on the directories a
product names — the primary, where relative paths resolve, and the rest addressed by name — and
the environment confines to all of them and proves it.

`full` mode for the path tests, so they run on any machine (confinement by `inside()`); the
sandbox tests skip where there is no OS sandbox, as the single-root ones do.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.adapters.environment.local import local_sandbox
from shadow_hdk.kernel import Completed, Refused
from shadow_hdk.kernel.workspace import Root, Workspace

HAS_SANDBOX = local_sandbox() is not None
needs_sandbox = pytest.mark.skipif(not HAS_SANDBOX, reason="no OS sandbox on this machine")


def two(tmp_path: Path) -> tuple[Path, Path, Workspace]:
    finance, sales = tmp_path / "finance", tmp_path / "sales"
    finance.mkdir()
    sales.mkdir()
    (finance / "revenue.csv").write_text("r\n", encoding="utf-8")
    (sales / "notes.md").write_text("n\n", encoding="utf-8")
    return finance, sales, Workspace((Root("finance", str(finance)), Root("sales", str(sales))))


def test_a_workspace_names_its_roots_and_the_first_is_primary(tmp_path: Path) -> None:
    finance, sales, workspace = two(tmp_path)
    assert workspace.primary.name == "finance" and workspace.primary.path == str(finance)
    assert [r.name for r in workspace.roots] == ["finance", "sales"]
    assert workspace.named("sales").path == str(sales)
    assert Workspace.of(finance).roots == (Root("finance", str(finance)),), "one root, its name"


async def test_two_roots_cannot_share_a_name_or_nest(tmp_path: Path) -> None:
    a = tmp_path / "a"
    a.mkdir()
    (a / "inner").mkdir()
    with pytest.raises(ValueError, match="same name"):
        Workspace((Root("x", str(a)), Root("x", str(tmp_path / "b"))))
    with pytest.raises(ValueError, match="at least one"):
        Workspace(())
    # Nesting is the environment's to refuse: the kernel holds strings and touches no filesystem.
    nested = Workspace((Root("a", str(a)), Root("inner", str(a / "inner"))))
    with pytest.raises(ValueError, match="inside"):
        await LocalEnvironment.open(workspace=nested, mode="full")


async def test_relative_paths_resolve_in_the_primary_and_a_name_reaches_another_root(
    tmp_path: Path,
) -> None:
    finance, sales, workspace = two(tmp_path)
    env = await LocalEnvironment.open(workspace=workspace, mode="full")
    assert await env.invoke("read_file", {"path": "revenue.csv"}) == Completed("r\n")
    assert await env.invoke("read_file", {"path": "sales/notes.md"}) == Completed("n\n")
    assert await env.invoke("read_file", {"path": "finance/revenue.csv"}) == Completed("r\n")
    await env.invoke("write_file", {"path": "sales/new.md", "content": "x"})
    assert (sales / "new.md").read_text(encoding="utf-8") == "x"
    listed = await env.invoke("list_dir", {"path": "sales"})
    assert listed == Completed(["new.md", "notes.md"])


async def test_a_path_outside_every_root_is_refused_and_says_the_roots(tmp_path: Path) -> None:
    _finance, _sales, workspace = two(tmp_path)
    (tmp_path / "elsewhere.txt").write_text("e", encoding="utf-8")
    env = await LocalEnvironment.open(workspace=workspace, mode="full")
    refused = await env.invoke("read_file", {"path": "../elsewhere.txt"})
    assert (
        isinstance(refused, Refused) and "finance" in refused.reason and "sales" in refused.reason
    )
    absolute = await env.invoke("read_file", {"path": str(tmp_path / "elsewhere.txt")})
    assert isinstance(absolute, Refused)
    inside_by_absolute = await env.invoke(
        "read_file", {"path": str(tmp_path / "sales" / "notes.md")}
    )
    assert inside_by_absolute == Completed("n\n"), "an absolute path under a root is that root's"


async def test_the_tools_say_which_roots_there_are(tmp_path: Path) -> None:
    _f, _s, workspace = two(tmp_path)
    env = await LocalEnvironment.open(workspace=workspace, mode="full")
    described = {r.id: r.component.interface.description for r in await env.registrations()}
    assert "finance (primary)" in described["read_file"] and "sales" in described["read_file"]
    assert "sales/" in described["write_file"], "how to address a file in another root"


@needs_sandbox
async def test_a_confined_command_may_write_in_every_root_and_nowhere_else(
    tmp_path: Path,
) -> None:
    finance, sales, workspace = two(tmp_path)
    env = await LocalEnvironment.open(workspace=workspace, mode="workspace-write")
    assert env.isolation.proven and env.isolation.writes_confined
    for root in (finance, sales):
        done = await env.invoke("run_shell", {"command": f"echo hi > {root}/from-shell.txt"})
        assert isinstance(done, Completed) and cast(dict[str, Any], done.output)["exit_code"] == 0
        assert (root / "from-shell.txt").exists()
    outside = tmp_path / "outside.txt"
    denied = await env.invoke("run_shell", {"command": f"echo hi > {outside}"})
    assert isinstance(denied, Completed) and cast(dict[str, Any], denied.output)["exit_code"] != 0
    assert not outside.exists()


@needs_sandbox
async def test_the_proof_runs_over_every_root(tmp_path: Path) -> None:
    """A workspace whose second root the sandbox could not confine would be refused — the proof
    writes inside each and outside all, and reports what it saw."""
    from shadow_hdk.adapters.environment.local import _prove

    _f, _s, workspace = two(tmp_path)
    box = local_sandbox()
    assert box is not None
    isolation = _prove(box, workspace, "workspace-write")
    assert isolation.proven and isolation.writes_confined and isolation.network_denied


@needs_sandbox
async def test_a_relative_root_is_resolved_before_the_proof(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """Found by running the README's snippet: `Root("finance", "./finance")` reached the OS
    profile as written, the sandbox allowed nothing, and the proof said *not proven*."""
    (tmp_path / "finance").mkdir()
    (tmp_path / "sales").mkdir()
    monkeypatch.chdir(tmp_path)
    env = await LocalEnvironment.open(
        workspace=Workspace((Root("finance", "./finance"), Root("sales", "./sales"))),
        mode="workspace-write",
    )
    assert env.isolation.proven
    assert env.roots[0].path == str((tmp_path / "finance").resolve())
    assert await env.invoke("write_file", {"path": "sales/x.txt", "content": "x"}) == Completed(
        {"path": "sales/x.txt", "bytes": 1}
    )
