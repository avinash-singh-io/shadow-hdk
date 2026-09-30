"""Undo, where a root is a git work tree (ENH-043, D161–D165).

The kit checkpoints the **run** (behind every park and resume) and the **record**
(`Thread.rollback`, `fork`), and touches the filesystem not at all — so a thread rolled back to
turn 3 faces a workspace still carrying turn 7's files. Lane P narrowed the design question for us:
a port with a git-backed adapter, cheap where a root is a work tree, which covers their first use
case.

Three properties here are measured rather than asserted about, because each is a way this can be
quietly wrong:

* **a restore actually restores** — content changed, a file created since, a file deleted since
* **the product's git state is untouched** (D165) — a kit that left entries in `git stash list` or
  commits on somebody's branch is a kit a developer stops trusting with their repository
* **ignored files survive** (D164) — getting this wrong deletes somebody's `node_modules` or
  resurrects their `.env`, and it is the decision most likely to be got wrong
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from shadow_hdk.adapters.environment.history import GitHistory, NoHistory

pytestmark = pytest.mark.anyio


def git(where: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=where, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def a_repository(where: Path) -> Path:
    git(where, "init", "-q")
    git(where, "config", "user.email", "test@example.com")
    git(where, "config", "user.name", "A Test")
    (where / "app.py").write_text("def one():\n    return 1\n")
    (where / ".gitignore").write_text("node_modules/\n.env\n")
    (where / "node_modules").mkdir()
    (where / "node_modules" / "big.js").write_text("// pretend this is enormous\n")
    (where / ".env").write_text("SECRET=hunter2\n")
    git(where, "add", "app.py", ".gitignore")
    git(where, "commit", "-q", "-m", "first")
    return where


# ------------------------------------------------------------------ it puts things back


async def test_a_restore_puts_changed_content_back(tmp_path: Path) -> None:
    root = a_repository(tmp_path)
    history = GitHistory(root)

    taken = await history.snapshot("before")
    (root / "app.py").write_text("def one():\n    return 999\n")
    await history.restore(taken)

    assert (root / "app.py").read_text() == "def one():\n    return 1\n"


async def test_a_restore_removes_a_file_created_since(tmp_path: Path) -> None:
    """The half a naive `checkout` misses: writing the tree's files back leaves extras behind."""
    root = a_repository(tmp_path)
    history = GitHistory(root)

    taken = await history.snapshot("before")
    (root / "invented.py").write_text("the agent made this up\n")
    await history.restore(taken)

    assert not (root / "invented.py").exists()


async def test_a_restore_brings_back_a_file_deleted_since(tmp_path: Path) -> None:
    root = a_repository(tmp_path)
    history = GitHistory(root)

    taken = await history.snapshot("before")
    (root / "app.py").unlink()
    await history.restore(taken)

    assert (root / "app.py").read_text() == "def one():\n    return 1\n"


async def test_a_snapshot_captures_work_that_was_never_committed(tmp_path: Path) -> None:
    """The ordinary case: an agent's changes are not commits, so a snapshot of HEAD would be a
    snapshot of the wrong thing."""
    root = a_repository(tmp_path)
    (root / "app.py").write_text("uncommitted but mine\n")
    (root / "new.py").write_text("also uncommitted\n")
    history = GitHistory(root)

    taken = await history.snapshot("before")
    (root / "app.py").write_text("clobbered\n")
    (root / "new.py").unlink()
    await history.restore(taken)

    assert (root / "app.py").read_text() == "uncommitted but mine\n"
    assert (root / "new.py").read_text() == "also uncommitted\n"


async def test_snapshots_are_listed_newest_first_with_their_labels(tmp_path: Path) -> None:
    root = a_repository(tmp_path)
    history = GitHistory(root)

    first = await history.snapshot("turn 1")
    second = await history.snapshot("turn 2")

    # **The ids must order themselves.** A commit's date is second-resolution, so two snapshots
    # taken in the same second tie under a date sort and "newest first" becomes whatever git felt
    # like — which is precisely what a product checkpointing every turn will hit. Asserting the
    # ids sort is deterministic where asserting the listing alone is a coin flip that usually
    # lands right. (Found by a mutation that restored the date sort and passed anyway.)
    assert second > first, (first, second)

    listed = await history.snapshots()
    assert [s.id for s in listed][:2] == [second, first], listed
    assert listed[0].label == "turn 2"


# ------------------------------------------------------------------ and leaves git alone (D165)


def git_state(where: Path) -> dict[str, str]:
    return {
        "head": git(where, "rev-parse", "HEAD"),
        "branch": git(where, "rev-parse", "--abbrev-ref", "HEAD"),
        "branches": git(where, "branch", "--format=%(refname)"),
        "stash": git(where, "stash", "list"),
        "index": git(where, "diff", "--cached", "--name-only"),
        "log": git(where, "log", "--format=%H", "-5"),
    }


async def test_taking_a_snapshot_touches_nothing_of_the_products_git(tmp_path: Path) -> None:
    root = a_repository(tmp_path)
    (root / "app.py").write_text("work in progress\n")
    before = git_state(root)

    await GitHistory(root).snapshot("before")

    assert git_state(root) == before, "a snapshot changed the repository's own state"
    assert git(root, "status", "--porcelain") != "", "and the work in progress is still uncommitted"


async def test_restoring_touches_nothing_of_the_products_git_either(tmp_path: Path) -> None:
    root = a_repository(tmp_path)
    history = GitHistory(root)
    taken = await history.snapshot("before")
    before = git_state(root)

    (root / "app.py").write_text("changed\n")
    await history.restore(taken)

    assert git_state(root) == before


async def test_a_snapshot_lives_under_the_kits_own_refs(tmp_path: Path) -> None:
    """So `git branch`, `git log` and `git stash list` stay the developer's, and a repository full
    of a month's snapshots is one `git for-each-ref` away from being cleaned up."""
    root = a_repository(tmp_path)

    await GitHistory(root).snapshot("before")

    refs = git(root, "for-each-ref", "--format=%(refname)")
    assert any(r.startswith("refs/shadow-hdk/snapshots/") for r in refs.splitlines()), refs
    assert not any(r.startswith("refs/stash") for r in refs.splitlines()), refs


# ------------------------------------------------------------------ and leaves ignored files (D164)


async def test_an_ignored_file_is_not_deleted_by_a_restore(tmp_path: Path) -> None:
    """`node_modules` must survive an undo. Deleting it would make undo a thing nobody dares use."""
    root = a_repository(tmp_path)
    history = GitHistory(root)

    taken = await history.snapshot("before")
    (root / "app.py").write_text("changed\n")
    await history.restore(taken)

    assert (root / "node_modules" / "big.js").exists(), "an undo deleted an ignored directory"
    assert (root / ".env").read_text() == "SECRET=hunter2\n"


async def test_an_ignored_file_changed_since_is_left_as_it_is(tmp_path: Path) -> None:
    """The other direction: a snapshot did not capture it, so a restore must not claim to know
    what it should say. Resurrecting somebody's old `.env` is its own kind of bug."""
    root = a_repository(tmp_path)
    history = GitHistory(root)

    taken = await history.snapshot("before")
    (root / ".env").write_text("SECRET=rotated\n")
    await history.restore(taken)

    assert (root / ".env").read_text() == "SECRET=rotated\n", "a restore resurrected a secret"


# ------------------------------------------------------------------ and refuses rather than crashes


async def test_a_root_that_is_not_a_repository_refuses_rather_than_crashing(
    tmp_path: Path,
) -> None:
    """The refuse-not-crash default every port default here keeps (project-rules)."""
    history = GitHistory(tmp_path)

    with pytest.raises(NoHistory) as refused:
        await history.snapshot("before")

    # Not merely "it raised NoHistory" — a raw `git add` failure does that too. The guard's whole
    # value is telling a reader what to do about it, and a test that accepts either message does
    # not cover the guard at all. (Found by a mutation that deleted the guard and passed.)
    said = str(refused.value)
    assert "not a git work tree" in said, said
    assert "WorkspaceHistoryPort" in said, "it must say what to supply instead"


async def test_restoring_a_snapshot_nobody_took_is_refused_by_name(tmp_path: Path) -> None:
    root = a_repository(tmp_path)

    with pytest.raises(NoHistory) as refused:
        await GitHistory(root).restore("not-a-snapshot")

    assert "not-a-snapshot" in str(refused.value)
