"""A write to `/dev/null` is not an effect on the world; a confined mode allows it (BUG-023).

Measured 2026-09-12 through the studio on macOS: `git` opens `/dev/null` read-write at startup
and died with *fatal: could not open '/dev/null'* inside `workspace-write`; `echo x > /dev/null`
failed the same way. The profile denied every `file-write*` outside the root, and the character
devices are outside the root. The agent could refactor and test but not commit — and read-only
mode, which exists so an agent can *look*, could not run `git status` either.

The devices a program writes to without changing anything — `/dev/null`, `/dev/zero`, the
randomness devices, its own terminal — are allowed in every mode; the proof stays what it was
(a write outside the root is denied).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from shadow_hdk.adapters.environment import LocalEnvironment, local_sandbox
from shadow_hdk.kernel import Completed

needs_sandbox = pytest.mark.skipif(local_sandbox() is None, reason="no OS sandbox on this machine")


def a_root(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    return root


@needs_sandbox
@pytest.mark.parametrize("mode", ["workspace-write", "read-only"])
async def test_the_null_device_takes_a_write_in_a_confined_mode(tmp_path: Path, mode: str) -> None:
    env = await LocalEnvironment.open(a_root(tmp_path), mode=mode)  # type: ignore[arg-type]

    done = await env.invoke("run_shell", {"command": "echo x > /dev/null && echo WROTE-NULL"})

    assert isinstance(done, Completed) and isinstance(done.output, dict), done
    assert done.output["exit_code"] == 0, done.output
    assert "WROTE-NULL" in str(done.output["stdout"])


@needs_sandbox
async def test_git_runs_in_a_confined_mode(tmp_path: Path) -> None:
    """`git status` in read-only, `git commit` in workspace-write: the two things a person asks
    an agent to do with a repository it has been handed."""
    root = a_root(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / "a.txt").write_text("one\n")

    looking = await LocalEnvironment.open(root, mode="read-only")
    status = await looking.invoke("run_shell", {"command": "git status --short"})
    assert isinstance(status, Completed) and isinstance(status.output, dict), status
    assert status.output["exit_code"] == 0, status.output
    assert "a.txt" in str(status.output["stdout"])

    writing = await LocalEnvironment.open(root, mode="workspace-write")
    committed = await writing.invoke(
        "run_shell",
        {
            "command": "git add a.txt && git -c user.name=t -c user.email=t@x commit -q -m one "
            "&& git log --oneline"
        },
    )
    assert isinstance(committed, Completed) and isinstance(committed.output, dict), committed
    assert committed.output["exit_code"] == 0, committed.output
    assert "one" in str(committed.output["stdout"])


@needs_sandbox
async def test_a_write_outside_the_root_is_still_denied(tmp_path: Path) -> None:
    """Allowing the devices must not have widened anything else."""
    root = a_root(tmp_path)
    outside = tmp_path / "outside.txt"
    env = await LocalEnvironment.open(root, mode="workspace-write")

    done = await env.invoke("run_shell", {"command": f"echo bad > {outside}; echo rc=$?"})

    assert isinstance(done, Completed) and isinstance(done.output, dict)
    assert not outside.exists()
    assert "rc=0" not in str(done.output["stdout"])
