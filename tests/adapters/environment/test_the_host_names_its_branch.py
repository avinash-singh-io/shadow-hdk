"""N-W2: host branch names, persistent exact ownership and conservative cleanup."""

from pathlib import Path

import pytest

from shadow_hdk.adapters.environment.worktrees import (
    CannotIsolate,
    close_worktree,
    open_worktree,
    worktrees,
)
from tests.adapters.environment.test_an_agent_gets_a_workspace_of_its_own import a_repository, git

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("check", ["branch", "head", "listed", "kept", "person"])
async def test_custom_branch_lifecycle(tmp_path: Path, check: str) -> None:
    repo = a_repository(tmp_path)
    theirs = tmp_path / "personal"
    git(repo, "worktree", "add", "-b", "intent/person", str(theirs))
    tree = await open_worktree(repo, "agent", branch="intent/task-1234")
    listed = [(w.path, w.branch) for w in await worktrees(repo)]
    head = git(tree.path, "branch", "--show-current")
    if check == "listed":
        assert listed == [(tree.path, "intent/task-1234")]
    await close_worktree(tree)
    actual = {
        "branch": tree.branch,
        "head": head,
        "listed": listed,
        "kept": git(repo, "branch", "--list", "intent/task-1234").strip(),
        "person": (theirs.exists(), git(repo, "branch", "--show-current")),
    }
    expected = {
        "branch": "intent/task-1234",
        "head": "intent/task-1234",
        "listed": [(tree.path, "intent/task-1234")],
        "kept": "intent/task-1234",
        "person": (True, "main"),
    }
    if check != "listed":
        assert actual[check] == expected[check]


@pytest.mark.parametrize("branch", ["", "../escape", "bad name", "HEAD", "-flag", "main"])
async def test_invalid_or_existing_branch_changes_nothing(tmp_path: Path, branch: str) -> None:
    repo = a_repository(tmp_path)
    with pytest.raises(CannotIsolate):
        await open_worktree(repo, "agent", branch=branch)
    assert git(repo, "worktree", "list", "--porcelain").count("worktree ") == 1


async def test_custom_branch_can_be_discarded(tmp_path: Path) -> None:
    repo = a_repository(tmp_path)
    tree = await open_worktree(repo, "agent", branch="feature/discard")
    await close_worktree(tree, keep_branch=False)
    assert (await worktrees(repo), git(repo, "branch", "--list", "feature/discard")) == ([], "")


async def test_a_reused_custom_branch_is_not_owned(tmp_path: Path) -> None:
    repo = a_repository(tmp_path)
    tree = await open_worktree(repo, "agent", branch="feature/reused")
    git(repo, "worktree", "remove", str(tree.path))
    personal = tmp_path / "personal"
    git(repo, "worktree", "add", str(personal), "feature/reused")
    assert await worktrees(repo) == []


@pytest.mark.parametrize("branch", ["feature/recreated", None])
async def test_recreating_the_same_path_and_branch_is_a_different_worktree(
    tmp_path: Path, branch: str | None
) -> None:
    repo = a_repository(tmp_path)
    tree = await open_worktree(repo, "agent", branch=branch)
    git(repo, "worktree", "remove", str(tree.path))
    git(repo, "worktree", "add", str(tree.path), tree.branch)
    assert await worktrees(repo) == []
