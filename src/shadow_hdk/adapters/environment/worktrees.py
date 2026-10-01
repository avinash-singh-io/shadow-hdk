"""A workspace of its own, per agent (ENH-043's other half, lane P's ask 7).

Several agents working in parallel, each producing its own pull request, need somewhere of their
own to work — and on a repository that is a git worktree: a real directory, its own branch, sharing
the object store rather than copying the tree.

**This is deliberately host-side, not an agent's tool.** Deciding that a run gets its own workspace
is a *composition* decision — how many agents, on what branches, merged how — and the boundary rule
puts that in the product. An agent registration for it would let a model invent branches nobody
asked for, and no mode has a sensible thing to say about that.

Every branch is created under `shadow-hdk/` so a developer's own branch names stay theirs, and
nothing here ever touches the main worktree's HEAD, index or branch (D165).
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path

BRANCHES = "shadow-hdk"
"""The prefix every branch created here carries, so `git branch` stays readable (D165)."""


class CannotIsolate(Exception):
    """This root cannot give an agent a workspace of its own, and why."""


@dataclass(frozen=True)
class Worktree:
    """One agent's own checkout: where it is, what branch it is on, and the repository behind it."""

    path: Path
    branch: str
    repo: Path


async def _git(where: Path, *args: str) -> str:
    """One git command, with no inherited git environment — a `GIT_DIR` already set must not
    redirect a worktree into somebody else's repository."""
    environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    process = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=where,
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await process.communicate()
    if process.returncode != 0:
        raise CannotIsolate(
            f"git {' '.join(args)} failed in {where}: "
            f"{err.decode('utf-8', 'replace').strip() or 'no output'}"
        )
    return out.decode("utf-8", "replace").strip()


async def open_worktree(
    repo: Path, name: str, *, at: str = "HEAD", where: Path | None = None
) -> Worktree:
    """Give `name` a checkout of its own, on a branch of its own, off `at`.

    The branch is `shadow-hdk/<name>`, which is what makes several agents' work separable
    afterwards: each has a branch a product can open a pull request from. Sharing the object store
    rather than copying the tree is what makes this cheap enough to do per agent.
    """
    repo = Path(repo)
    if not (repo / ".git").exists():
        raise CannotIsolate(
            f"{repo} is not a git repository, so an agent cannot be given a worktree of its own "
            "here — isolate by handing each agent its own root instead"
        )
    if not name or "/" in name or name.startswith("."):
        raise CannotIsolate(f"{name!r} is not a usable worktree name")
    branch = f"{BRANCHES}/{name}"
    at_path = Path(where) if where is not None else repo.parent / f".{repo.name}-{name}"
    await _git(repo, "worktree", "add", "-b", branch, str(at_path), at)
    return Worktree(path=at_path.resolve(), branch=branch, repo=repo.resolve())


async def close_worktree(tree: Worktree, *, keep_branch: bool = True) -> None:
    """Take the checkout away. The **branch stays by default**, because the work on it is the
    point — an agent's pull request outlives the directory it was written in. Pass
    `keep_branch=False` for a run whose output was thrown away."""
    await _git(tree.repo, "worktree", "remove", "--force", str(tree.path))
    if not keep_branch:
        await _git(tree.repo, "branch", "-D", tree.branch)


async def worktrees(repo: Path) -> list[Worktree]:
    """Every worktree this module made for `repo`. A developer's own worktrees are not listed —
    only branches under `shadow-hdk/`, so a cleanup here cannot reach their work."""
    listed = await _git(Path(repo), "worktree", "list", "--porcelain")
    found: list[Worktree] = []
    path: Path | None = None
    for line in listed.splitlines():
        if line.startswith("worktree "):
            path = Path(line[len("worktree ") :])
        elif line.startswith("branch ") and path is not None:
            ref = line[len("branch ") :]
            short = ref.removeprefix("refs/heads/")
            if short.startswith(f"{BRANCHES}/"):
                found.append(Worktree(path=path, branch=short, repo=Path(repo).resolve()))
            path = None
    return found


__all__ = ["BRANCHES", "CannotIsolate", "Worktree", "close_worktree", "open_worktree", "worktrees"]
