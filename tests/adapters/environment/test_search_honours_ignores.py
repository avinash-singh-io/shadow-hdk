"""N-W3: prune ignored directories; Git and portable roots share nested ignore behaviour."""

from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.kernel import Completed
from shadow_hdk.runtime.environment import Environment
from tests.adapters.environment.test_an_agent_gets_a_workspace_of_its_own import git

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("repository", [False, True])
@pytest.mark.parametrize("operation", ["glob", "grep"])
async def test_nested_ignore_and_negation(tmp_path: Path, repository: bool, operation: str) -> None:
    if repository:
        git(tmp_path, "init", "-q")
    (tmp_path / ".gitignore").write_text("node_modules/\n*.tmp\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "big.py").write_text("needle\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / ".gitignore").write_text("*.py\n!keep.py\n")
    for name in ("keep.py", "hide.py", "hide.tmp"):
        (tmp_path / "src" / name).write_text("needle\n")
    env = await LocalEnvironment.open(tmp_path, mode="full")
    try:
        args: dict[str, Any] = (
            {"pattern": "**/*.py"}
            if operation == "glob"
            else {"pattern": "needle", "glob": "**/*.py"}
        )
        answer = await env.invoke(operation, args)
        value: Any = answer.output if isinstance(answer, Completed) else answer
        assert value == (
            ["src/keep.py"]
            if operation == "glob"
            else [{"path": "src/keep.py", "line": 1, "text": "needle"}]
        )
    finally:
        await env.close()


async def test_starting_below_root_still_applies_ancestor_ignores(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("*.tmp\nignored/\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "keep.txt").write_text("x")
    (tmp_path / "src" / "hide.tmp").write_text("x")
    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored" / "hide.txt").write_text("x")
    env = await LocalEnvironment.open(tmp_path, mode="full")
    try:
        assert [await env._walk("src"), await env._walk("ignored")] == [["src/keep.txt"], []]
    finally:
        await env.close()


async def test_tracked_ignored_files_remain_searchable_and_metadata_does_not(
    tmp_path: Path,
) -> None:
    git(tmp_path, "init", "-q")
    (tmp_path / "tracked.tmp").write_text("needle")
    git(tmp_path, "add", "tracked.tmp")
    (tmp_path / ".gitignore").write_text("*.tmp\n")
    (tmp_path / "untracked.tmp").write_text("needle")
    env = await LocalEnvironment.open(tmp_path, mode="full")
    try:
        assert await env._walk(".") == [".gitignore", "tracked.tmp"]
    finally:
        await env.close()


class LargePortable(Environment):
    """100,001 paths, no filesystem cost; last subtree used to vanish past the ceiling."""

    async def _list(self, path: str) -> list[str]:
        if path == ".":
            return ["last/", "many/"]
        return ["target.py"] if path == "last" else [f"f{i}.txt" for i in range(100_000)]

    async def _read(self, path: str) -> str:
        raise FileNotFoundError(path)


async def test_portable_search_has_no_silent_repository_ceiling() -> None:
    env = object.__new__(LargePortable)
    result = await env._glob("**/*.py", ".", 100)
    assert isinstance(result, Completed) and result.output == ["last/target.py"]


async def test_portable_search_never_lists_an_ignored_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".gitignore").write_text("ignored/\n")
    (tmp_path / "ignored").mkdir()
    env = await LocalEnvironment.open(tmp_path, mode="full")
    original = env._search_entries
    visited: list[str] = []

    async def listing(path: str) -> list[str]:
        visited.append(path)
        return await original(path)

    monkeypatch.setattr(env, "_search_entries", listing)
    try:
        await env._walk(".")
        assert visited == ["."]
    finally:
        await env.close()


async def test_non_git_search_does_not_follow_directory_cycles_or_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / "keep.py").write_text("needle")
    (tmp_path / "outside.py").write_text("needle")
    (root / "loop").symlink_to(root, target_is_directory=True)
    (root / "escape.py").symlink_to(tmp_path / "outside.py")
    env = await LocalEnvironment.open(root, mode="full")
    try:
        import asyncio

        answer = await asyncio.wait_for(env._walk("."), 2)
        assert answer == ["keep.py"]
    finally:
        await env.close()
