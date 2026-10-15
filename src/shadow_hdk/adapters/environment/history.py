"""Undo, where a root is a git work tree (ENH-043, D161–D165).

Lane P narrowed the design question to this: a port with a git-backed adapter, cheap where a root
is a work tree, which covers their first use case. `GitHistory` is that adapter.

**D165 is the constraint everything here is shaped by: none of this touches the product's git
state.** Not HEAD, not a branch, not the index, not the stash, not the reflog of anything a
developer reads. A kit that left entries in `git stash list`, or commits on somebody's branch, is a
kit a developer stops trusting with their repository — and rightly, because a snapshot taken for an
agent's convenience is not a thing they asked to have in their history.

A private index per worktree retains stat information between snapshots (N-W4).
A cross-process lock serializes its updates. Snapshots are built the plumbing way:

    GIT_INDEX_FILE=<private>    git add -A          # a scratch index, never theirs
                                git write-tree      # the tree that index describes
                                git commit-tree     # a commit object, parented on nothing
                                git update-ref refs/shadow-hdk/snapshots/<id>

Nothing in that sequence writes to `.git/index`, moves HEAD, or creates a branch. The commits are
parentless and live under the kit's own ref namespace, so `git log`, `git branch` and `git stash
list` are unchanged and a month of snapshots is one `git for-each-ref` away from being cleaned up.

**D164: a snapshot holds what git would track.** `git add -A` respects `.gitignore`, so
`node_modules` and `.venv` are not captured — which is what makes a snapshot cheap enough that
somebody actually takes one. The consequence has to be honest in both directions, and both are
tested: a restore does not delete an ignored file, and it does not resurrect one either.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
import uuid
from contextlib import suppress
from pathlib import Path

from filelock import AsyncFileLock

from shadow_hdk.kernel.ports import Snapshot

REFS = "refs/shadow-hdk/snapshots"
"""The kit's own ref namespace (D165). Never `refs/heads`, never `refs/stash`."""


class NoHistory(Exception):
    """This root has no history mechanism, or the snapshot asked for is not one of ours.

    Raised rather than returned because the port's callers turn it into a `Refused` — the
    refuse-not-crash default project-rules requires of a port lives at the call site, where an
    observation can be made of it.
    """


class GitHistory:
    """A workspace's history, in the repository it already is (D161)."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    # ------------------------------------------------------------------ the plumbing

    async def _git(self, *args: str, index: str | None = None, input: bytes | None = None) -> str:
        """One git command, with an optional scratch index. Never inherits a caller's git
        environment, so a `GIT_INDEX_FILE` or `GIT_DIR` already set cannot redirect this."""
        environment = dict(os.environ)
        for name in [n for n in environment if n.startswith("GIT_")]:
            del environment[name]
        if index is not None:
            environment["GIT_INDEX_FILE"] = index
        process = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=self.root,
            env=environment,
            stdin=asyncio.subprocess.PIPE if input is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await process.communicate(input)
        if process.returncode != 0:
            raise NoHistory(
                f"git {' '.join(args)} failed in {self.root}: "
                f"{err.decode('utf-8', 'replace').strip() or 'no output'}"
            )
        return out.decode("utf-8", "surrogateescape").rstrip("\n")

    async def _must_be_a_repository(self) -> None:
        try:
            inside = await self._git("rev-parse", "--is-inside-work-tree")
        except NoHistory as not_git:
            raise NoHistory(
                f"{self.root} is not a git work tree, so there is no history to snapshot here — "
                "supply a WorkspaceHistoryPort of your own for this root"
            ) from not_git
        if inside != "true":
            raise NoHistory(f"{self.root} is not a git work tree")

    async def _state(self) -> Path:
        """Git's private directory is per linked worktree; the person's index is never reused."""
        where = Path(await self._git("rev-parse", "--git-path", "shadow-hdk-history"))
        if not where.is_absolute():
            where = self.root / where
        where.mkdir(parents=True, exist_ok=True)
        return where.resolve()

    async def _capture(self, index: str) -> str:
        """Update a private index with external edits, reusing unchanged-file stat information.

        Git's real index supplies tracking eligibility, never staged content. A file captured when
        untracked and later ignored must be evicted from our cache; tracked ignored files stay.
        """
        if not Path(index).exists():
            real_index = Path(await self._git("rev-parse", "--git-path", "index"))
            if not real_index.is_absolute():
                real_index = self.root / real_index
            if real_index.exists():
                shutil.copy2(real_index, index)
            else:
                await self._git("read-tree", "--empty", index=index)
        eligible = set(
            (await self._git("ls-files", "-z", "--cached", "--others", "--exclude-standard")).split(
                "\0"
            )
        )
        cached = set((await self._git("ls-files", "-z", "--cached", index=index)).split("\0"))
        # Newly staged ignored files may be absent from our older cache. Seed their tracking,
        # then add -A reads working content, never taking a person's staged content as a snapshot.
        staged = await self._git("ls-files", "--stage", "-z")
        added = [
            entry for entry in staged.split("\0") if entry and entry.split("\t", 1)[1] not in cached
        ]
        if added:
            await self._git(
                "update-index",
                "-z",
                "--index-info",
                index=index,
                input=os.fsencode("\0".join(added) + "\0"),
            )
        tracked = [entry.split("\t", 1)[1] for entry in staged.split("\0") if entry]
        if tracked:
            await self._git(
                "update-index",
                "--no-assume-unchanged",
                "--no-skip-worktree",
                "-z",
                "--stdin",
                index=index,
                input=os.fsencode("\0".join(tracked) + "\0"),
            )
        removed = cached - eligible
        if removed:
            await self._git(
                "update-index",
                "--force-remove",
                "-z",
                "--stdin",
                index=index,
                input=os.fsencode("\0".join(sorted(removed)) + "\0"),
            )
        await self._git("add", "-A", index=index)
        return await self._git("write-tree", index=index)

    def _path(self, relative: str) -> Path:
        """Do not let a symlink directory redirect a restore outside its workspace."""
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or ".git" in path.parts:
            raise NoHistory(f"{relative!r} is not a restorable workspace path")
        where = self.root / path
        for parent in where.parents:
            if parent == self.root:
                break
            if parent.is_symlink():
                raise NoHistory(f"{relative!r} has a symlink parent; nothing was restored")
        return where

    # ------------------------------------------------------------------ the port

    async def snapshot(self, label: str = "") -> str:
        """Capture what git would track, and hand back the snapshot's name.

        Through a scratch index, so the product's own staged changes are neither read as ours nor
        disturbed (D165) — an agent snapshotting mid-review must not unstage a developer's work.
        """
        await self._must_be_a_repository()
        state = await self._state()
        async with AsyncFileLock(str(state / "operation.lock"), timeout=60):
            tree = await self._capture(str(state / "index"))
        # Parentless on purpose: a snapshot is not a point in the project's history and must not
        # look like one to anything that walks commits.
        commit = await self._git("commit-tree", tree, "-m", label or "snapshot")
        # **Sortable, because git cannot order these.** A commit's date is second-resolution,
        # so two snapshots taken in the same second tie under `--sort=-creatordate` and
        # "newest first" becomes "whichever git felt like" — found by a test taking two in a
        # row, which is exactly what a product checkpointing each turn will do. The id carries
        # the order instead, and the listing sorts by name.
        name = f"{time.time_ns():020d}-{uuid.uuid4().hex[:8]}"
        await self._git("update-ref", f"{REFS}/{name}", commit)
        return name

    async def restore(self, snapshot: str) -> None:
        """Put the workspace back to that snapshot: content, files created since, files deleted
        since. Ignored files are left exactly as they are (D164).
        """
        await self._must_be_a_repository()
        try:
            commit = await self._git("rev-parse", f"{REFS}/{snapshot}")
        except NoHistory as unknown:
            raise NoHistory(
                f"{snapshot!r} is not a snapshot taken here — nothing was restored"
            ) from unknown

        state = await self._state()
        async with AsyncFileLock(str(state / "operation.lock"), timeout=60):
            index = str(state / "index")
            current = await self._capture(index)
            held = set((await self._git("ls-tree", "-r", "--name-only", "-z", commit)).split("\0"))
            changed = [
                p
                for p in (
                    await self._git(
                        "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", current, commit
                    )
                ).split("\0")
                if p
            ]
            paths = {p: self._path(p) for p in changed}
            emptied: set[Path] = set()
            for relative, where in paths.items():
                if relative not in held and (where.is_file() or where.is_symlink()):
                    where.unlink()
                    emptied.update(
                        p for p in where.parents if p != self.root and p.is_relative_to(self.root)
                    )
            # Only ancestors of removed files can have become empty. Never enumerate dependencies.
            for where in sorted(emptied, key=lambda p: -len(p.parts)):
                # Nonempty, already gone, or somebody else's directory stays.
                with suppress(OSError):
                    where.rmdir()
            await self._git("read-tree", "-m", commit, index=index)
            checkout = [p for p in changed if p in held]
            if checkout:
                await self._git(
                    "checkout-index",
                    "-f",
                    "-z",
                    "--stdin",
                    index=index,
                    input=os.fsencode("\0".join(checkout) + "\0"),
                )

    async def snapshots(self) -> list[Snapshot]:
        """Every snapshot taken here, newest first."""
        await self._must_be_a_repository()
        listed = await self._git(
            "for-each-ref",
            "--sort=-refname",
            "--format=%(refname:strip=3)%09%(contents:subject)%09%(creatordate:iso-strict)",
            REFS,
        )
        found: list[Snapshot] = []
        for line in listed.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            found.append(
                Snapshot(
                    id=parts[0],
                    label=parts[1] if len(parts) > 1 else "",
                    at=parts[2] if len(parts) > 2 else "",
                )
            )
        return found


__all__ = ["GitHistory", "NoHistory", "REFS"]
