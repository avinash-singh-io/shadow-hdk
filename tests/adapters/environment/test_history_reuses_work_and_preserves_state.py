"""N-W4: stable private index, sparse restore and external edits; correctness before budgets."""

import asyncio
from pathlib import Path

import pytest

from shadow_hdk.adapters.environment.history import GitHistory
from tests.adapters.environment.test_an_agent_gets_a_workspace_of_its_own import a_repository, git

pytestmark = pytest.mark.anyio


async def test_restore_does_not_rewrite_unchanged_files_or_walk_ignored_folders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = a_repository(tmp_path)
    (repo / ".gitignore").write_text("node_modules/\n")
    (repo / "stable.txt").write_text("stable")
    (repo / "node_modules").mkdir()
    (repo / "node_modules" / "dependency").write_text("keep")
    history = GitHistory(repo)
    taken = await history.snapshot()
    stable = (repo / "stable.txt").stat().st_mtime_ns
    (repo / "app.py").write_text("changed")
    (repo / "new" / "deep").mkdir(parents=True)
    (repo / "new" / "deep" / "created").write_text("new")
    walks: list[Path] = []
    old = Path.rglob

    def walking(self: Path, pattern: str) -> object:
        walks.append(self)
        return old(self, pattern)

    monkeypatch.setattr(Path, "rglob", walking)
    await history.restore(taken)
    assert (
        (repo / "stable.txt").stat().st_mtime_ns,
        walks,
        (repo / "new").exists(),
        (repo / "node_modules" / "dependency").read_text(),
    ) == (stable, [], False, "keep")


async def test_snapshots_reuse_a_private_index_across_instances_and_capture_external_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = a_repository(tmp_path)
    used: list[str] = []
    original = asyncio.create_subprocess_exec

    async def launched(*args: object, **kw: object) -> asyncio.subprocess.Process:
        env = kw.get("env")
        if args[:3] == ("git", "add", "-A") and isinstance(env, dict):
            used.append(str(env.get("GIT_INDEX_FILE")))
        return await original(*args, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(asyncio, "create_subprocess_exec", launched)
    before = await GitHistory(repo).snapshot()
    (repo / "app.py").write_text("external edit")
    (repo / "external.txt").write_text("external new")
    after = await GitHistory(repo).snapshot()
    (repo / "app.py").write_text("later")
    (repo / "external.txt").unlink()
    await GitHistory(repo).restore(after)
    await GitHistory(repo).snapshot()
    assert (
        len(set(used)),
        Path(used[0]).exists(),
        (repo / "app.py").read_text(),
        (repo / "external.txt").read_text(),
        before != after,
    ) == (1, True, "external edit", "external new", True)


async def test_tracked_ignored_files_and_file_modes_are_restored_without_touching_git(
    tmp_path: Path,
) -> None:
    repo = a_repository(tmp_path)
    (repo / ".gitignore").write_text("*.secret\n")
    (repo / "tracked.secret").write_text("tracked")
    git(repo, "add", "-f", "tracked.secret")
    (repo / "app.py").chmod(0o755)
    state = [git(repo, "rev-parse", "HEAD"), git(repo, "write-tree"), git(repo, "stash", "list")]
    history = GitHistory(repo)
    taken = await history.snapshot()
    (repo / "tracked.secret").write_text("changed")
    (repo / "app.py").chmod(0o644)
    await history.restore(taken)
    assert [
        (repo / "tracked.secret").read_text(),
        bool((repo / "app.py").stat().st_mode & 0o111),
        [git(repo, "rev-parse", "HEAD"), git(repo, "write-tree"), git(repo, "stash", "list")],
    ] == ["tracked", True, state]


async def test_newly_ignored_untracked_content_is_not_kept_by_the_cache(tmp_path: Path) -> None:
    repo = a_repository(tmp_path)
    (repo / "cache.tmp").write_text("untracked")
    await GitHistory(repo).snapshot()
    (repo / ".gitignore").write_text("*.tmp\n")
    history = GitHistory(repo)
    taken = await history.snapshot()
    (repo / "cache.tmp").write_text("ignored now")
    await history.restore(taken)
    assert (repo / "cache.tmp").read_text() == "ignored now"


async def test_concurrent_history_instances_serialize_and_restart_after_cache_loss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = a_repository(tmp_path)
    histories = [GitHistory(repo), GitHistory(repo)]
    original = GitHistory._capture
    active = 0
    peak = 0

    async def capturing(self: GitHistory, index: str) -> str:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        try:
            await asyncio.sleep(0.02)
            return await original(self, index)
        finally:
            active -= 1

    monkeypatch.setattr(GitHistory, "_capture", capturing)
    taken = await asyncio.gather(*(h.snapshot() for h in histories), return_exceptions=True)
    assert peak == 1 and all(isinstance(t, str) for t in taken)
    snapshots = [t for t in taken if isinstance(t, str)]
    state = Path(git(repo, "rev-parse", "--git-path", "shadow-hdk-history"))
    if not state.is_absolute():
        state = repo / state
    for path in state.glob("index*"):
        path.unlink()
    (repo / "app.py").write_text("changed")
    await GitHistory(repo).snapshot()
    await histories[0].restore(snapshots[0])
    assert (len(set(snapshots)), (repo / "app.py").read_text()) == (2, "shared\n")
