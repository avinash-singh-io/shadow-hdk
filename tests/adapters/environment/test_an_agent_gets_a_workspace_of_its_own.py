"""Several agents in parallel, each with a checkout of its own (lane P's ask 7).

"Several agents in parallel, each producing its own pull request. Git worktrees locally first." A
worktree is a real directory on its own branch, sharing the object store rather than copying the
tree — cheap enough to do per agent, and separable afterwards because each has a branch a product
can open a pull request from.

**Host-side on purpose.** Deciding a run gets its own workspace is a composition decision, so it is
not an agent registration: a model inventing branches nobody asked for is not something a mode has
anything sensible to say about.

The property that matters most is the last one: a developer's own branches and worktrees are not
reachable by anything here.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from shadow_hdk.adapters.environment.local import LocalEnvironment
from shadow_hdk.adapters.environment.worktrees import (
    CannotIsolate,
    close_worktree,
    open_worktree,
    worktrees,
)

pytestmark = pytest.mark.anyio


def git(where: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=where, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def a_repository(where: Path) -> Path:
    root = where / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "A Test")
    (root / "app.py").write_text("shared\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "first")
    return root


# ------------------------------------------------------------------ each agent gets its own


async def test_two_agents_get_two_independent_checkouts(tmp_path: Path) -> None:
    repo = a_repository(tmp_path)

    one = await open_worktree(repo, "agent-one")
    two = await open_worktree(repo, "agent-two")

    assert one.path != two.path
    assert one.path.is_dir() and two.path.is_dir()
    assert (one.path / "app.py").read_text() == "shared\n"

    (one.path / "app.py").write_text("agent one was here\n")

    assert (two.path / "app.py").read_text() == "shared\n", "one agent's work leaked into another"
    assert (repo / "app.py").read_text() == "shared\n", "and into the developer's own checkout"


async def test_each_one_is_on_its_own_branch_so_it_can_open_its_own_pull_request(
    tmp_path: Path,
) -> None:
    repo = a_repository(tmp_path)

    one = await open_worktree(repo, "agent-one")
    two = await open_worktree(repo, "agent-two")

    assert one.branch == "shadow-hdk/agent-one"
    assert two.branch == "shadow-hdk/agent-two"
    assert git(one.path, "rev-parse", "--abbrev-ref", "HEAD") == "shadow-hdk/agent-one"
    assert git(two.path, "rev-parse", "--abbrev-ref", "HEAD") == "shadow-hdk/agent-two"


async def test_an_environment_on_a_worktree_has_a_history_of_its_own(tmp_path: Path) -> None:
    """A linked worktree's `.git` is a *file*, not a directory — so an environment that tested for
    a directory would silently have no undo in exactly the setup lane P is asking for."""
    repo = a_repository(tmp_path)
    tree = await open_worktree(repo, "agent-one")

    environment = await LocalEnvironment.open(tree.path, mode="full")
    try:
        assert environment.history is not None, "a linked worktree has a history too"
        taken = await environment.history.snapshot("in its own tree")
        (tree.path / "app.py").write_text("changed\n")
        await environment.history.restore(taken)
        assert (tree.path / "app.py").read_text() == "shared\n"
    finally:
        await environment.close()


# ------------------------------------------------------------------ and is taken away cleanly


async def test_closing_one_leaves_the_other_and_the_developers_own_alone(tmp_path: Path) -> None:
    repo = a_repository(tmp_path)
    one = await open_worktree(repo, "agent-one")
    two = await open_worktree(repo, "agent-two")

    await close_worktree(one)

    assert not one.path.exists()
    assert two.path.is_dir() and (two.path / "app.py").exists()
    assert (repo / "app.py").read_text() == "shared\n"
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"


async def test_the_branch_outlives_the_directory_because_the_work_is_the_point(
    tmp_path: Path,
) -> None:
    repo = a_repository(tmp_path)
    tree = await open_worktree(repo, "agent-one")
    (tree.path / "app.py").write_text("work worth keeping\n")
    git(tree.path, "add", "-A")
    git(tree.path, "commit", "-q", "-m", "the agent's work")

    await close_worktree(tree)

    branches = git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert "shadow-hdk/agent-one" in branches, "an agent's pull request lost its branch"


async def test_a_run_whose_output_was_thrown_away_can_drop_its_branch_too(tmp_path: Path) -> None:
    repo = a_repository(tmp_path)
    tree = await open_worktree(repo, "agent-one")

    await close_worktree(tree, keep_branch=False)

    branches = git(repo, "branch", "--format=%(refname:short)").splitlines()
    assert "shadow-hdk/agent-one" not in branches


# ------------------------------------------------------------------ and cannot reach their work


async def test_only_the_kits_own_worktrees_are_listed(tmp_path: Path) -> None:
    """The property that matters most. A cleanup that swept up a developer's own worktree would
    be unforgivable, so the listing is filtered by the branch prefix rather than trusted."""
    repo = a_repository(tmp_path)
    theirs = tmp_path / "their-own-worktree"
    git(repo, "worktree", "add", "-b", "my-feature", str(theirs))
    ours = await open_worktree(repo, "agent-one")

    listed = await worktrees(repo)

    assert [w.branch for w in listed] == ["shadow-hdk/agent-one"], listed
    assert ours.path in [w.path for w in listed]
    assert theirs.resolve() not in [w.path.resolve() for w in listed]


async def test_a_root_that_is_not_a_repository_says_what_to_do_instead(tmp_path: Path) -> None:
    with pytest.raises(CannotIsolate) as cannot:
        await open_worktree(tmp_path, "agent-one")

    assert "not a git repository" in str(cannot.value)
    assert "its own root" in str(cannot.value), "it must say what to do instead"


async def test_a_name_that_would_escape_the_prefix_is_refused(tmp_path: Path) -> None:
    repo = a_repository(tmp_path)

    for bad in ("../escape", "a/b", "", ".hidden"):
        with pytest.raises(CannotIsolate):
            await open_worktree(repo, bad)
