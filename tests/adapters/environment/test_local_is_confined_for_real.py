"""A local environment in a confined mode is confined by the operating system, and proves it (D49).

Codex's model: the OS sandbox around the whole process — `sandbox-exec` on macOS, bubblewrap on
Linux — so the file tools and the shell tool are ordinary and the *environment* is what is
confined. Measured 2026-09-11 on macOS 26: a write outside the root is *Operation not permitted*,
a socket is denied, the interpreter runs.

**Proven at construction, by what is denied (D36).** The environment tries to write outside its
root and must fail; tries to open a socket and must fail; writes inside and must succeed. What it
then declares is what the proof found — never what the profile says.

Where no OS sandbox exists, a confined mode is **refused** naming what would fix it. `full` always
constructs and declares everything. These tests skip the proofs where there is nothing to prove
with, and still hold the refusal and `full`.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.environment import LocalEnvironment, local_sandbox
from shadow_hdk.kernel import (
    Completed,
    EnvironmentRequirements,
    IncompatibleCapabilities,
    Refused,
    ScopeSet,
)
from shadow_hdk.runtime.environment import CannotEnforce

HAS_SANDBOX = local_sandbox() is not None
needs_sandbox = pytest.mark.skipif(not HAS_SANDBOX, reason="no OS sandbox on this machine")


def a_root(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    return root


# ------------------------------------------------------------------ enforced or refused


async def test_full_always_constructs_and_declares_everything(tmp_path: Path) -> None:
    env = await LocalEnvironment.open(a_root(tmp_path), mode="full")

    by_id = {r.id: r.component.effects for r in await env.registrations()}
    assert by_id["run_shell"].writes == ScopeSet(everything=True)
    assert by_id["run_shell"].reaches is True
    assert by_id["run_shell"].contained is False


@pytest.mark.skipif(HAS_SANDBOX, reason="this machine has a sandbox; the refusal cannot be seen")
async def test_a_confined_mode_is_refused_where_nothing_can_enforce_it(tmp_path: Path) -> None:
    with pytest.raises(CannotEnforce, match="writes confined"):
        await LocalEnvironment.open(a_root(tmp_path), mode="workspace-write")


# ------------------------------------------------------------------ the proof


@needs_sandbox
async def test_workspace_write_is_proven_before_it_is_declared(tmp_path: Path) -> None:
    env = await LocalEnvironment.open(a_root(tmp_path), mode="workspace-write")

    assert env.isolation.proven is True
    assert env.isolation.writes_confined is True
    assert env.isolation.network_denied is True
    by_id = {r.id: r.component.effects for r in await env.registrations()}
    assert by_id["run_shell"].writes == ScopeSet.of("workspace")
    assert by_id["run_shell"].reaches is False
    assert by_id["run_shell"].contained is True


@needs_sandbox
async def test_local_truth_refuses_repository_only_reads_and_denied_secrets(
    tmp_path: Path,
) -> None:
    with pytest.raises(IncompatibleCapabilities) as refused:
        await LocalEnvironment.open(
            a_root(tmp_path),
            mode="workspace-write",
            requirements=EnvironmentRequirements(
                reads_within="workspace", secrets="denied", proven=True
            ),
        )

    available = refused.value.available_environment
    assert available is not None
    assert available.reads == "machine"
    assert available.writes == "workspace"
    assert available.network == "denied"
    assert available.secrets == "ambient"
    assert available.proven is True
    assert [gap.axis for gap in refused.value.compatibility.mismatches] == ["reads", "secrets"]


@needs_sandbox
async def test_a_command_cannot_write_outside_the_root(tmp_path: Path) -> None:
    """The bug this whole phase closes, at the size it was found: a shell command reaching past
    the workspace. Now it is the operating system saying no."""
    root = a_root(tmp_path)
    outside = tmp_path / "escaped.txt"
    env = await LocalEnvironment.open(root, mode="workspace-write")

    done = await env.invoke("run_shell", {"command": f"echo bad > {outside}"})

    assert not outside.exists(), "a confined command wrote outside the root"
    assert isinstance(done, Completed) and isinstance(done.output, dict)
    assert done.output["exit_code"] != 0


@needs_sandbox
async def test_a_command_can_write_inside_the_root(tmp_path: Path) -> None:
    root = a_root(tmp_path)
    env = await LocalEnvironment.open(root, mode="workspace-write")

    await env.invoke("run_shell", {"command": "echo fine > inside.txt"})

    assert (root / "inside.txt").read_text() == "fine\n"


@needs_sandbox
async def test_a_command_cannot_reach_the_network(tmp_path: Path) -> None:
    env = await LocalEnvironment.open(a_root(tmp_path), mode="workspace-write")
    probe = (
        "import socket; s=socket.socket(); s.settimeout(2); print(s.connect_ex(('127.0.0.1', 22)))"
    )

    done = await env.invoke("run_python", {"source": probe})

    assert isinstance(done, Completed) and isinstance(done.output, dict)
    assert str(done.output["stdout"]).strip() != "0", "a confined command reached a socket"


@needs_sandbox
async def test_read_only_refuses_a_write_before_asking_anyone(tmp_path: Path) -> None:
    """A mode is the environment's own promise, kept before governance is consulted."""
    root = a_root(tmp_path)
    env = await LocalEnvironment.open(root, mode="read-only")

    refused = await env.invoke("write_file", {"path": "x.txt", "content": "no"})
    listed = {r.id for r in await env.registrations()}

    assert isinstance(refused, Refused) and "read-only" in refused.reason
    assert "write_file" not in listed, "read-only still offered a write"
    assert not (root / "x.txt").exists()


@needs_sandbox
async def test_read_only_denies_a_commands_write_too(tmp_path: Path) -> None:
    root = a_root(tmp_path)
    env = await LocalEnvironment.open(root, mode="read-only")

    await env.invoke("run_shell", {"command": "echo sneaky > inside.txt"})

    assert not (root / "inside.txt").exists(), "read-only let a command write"


# ------------------------------------------------------------------ files, confined by path


async def test_file_operations_stay_inside_the_root_in_every_mode(tmp_path: Path) -> None:
    root = a_root(tmp_path)
    (tmp_path / "secret.txt").write_text("outside")
    env = await LocalEnvironment.open(root, mode="full")

    refused = await env.invoke("read_file", {"path": "../secret.txt"})

    assert isinstance(refused, Refused) and "outside" in refused.reason


async def test_the_leash_still_holds_inside_the_box(tmp_path: Path) -> None:
    """Confinement is not a reason to lose the timeout: a command that never ends is still ended."""
    env = await LocalEnvironment.open(a_root(tmp_path), mode="full", timeout_s=0.5)

    done = await env.invoke("run_python", {"source": "import time; time.sleep(30)"})

    assert "timed out" in str(done)


def test_which_sandbox_this_machine_has_is_reported_not_guessed() -> None:
    """The first of the machine's candidates in the field's order (D133): seatbelt on macOS; on
    Linux the helper when it is installed and its kernel has Landlock, else bubblewrap; else
    nothing. An operator's `SHADOW_HDK_SANDBOX` narrows the order, so the test reads it too."""
    found = local_sandbox()
    narrowed = os.environ.get("SHADOW_HDK_SANDBOX")
    if sys.platform == "darwin":
        assert found is not None and found.name == "seatbelt"
    elif narrowed:
        assert found is not None and found.name == narrowed
    elif shutil.which("shadow-hdk-linux-sandbox") and _helper_probe_exits_zero():
        assert found is not None and found.name == "landlock"
    elif shutil.which("bwrap"):
        assert found is not None and found.name == "bubblewrap"
    else:
        assert found is None


def _helper_probe_exits_zero() -> bool:
    import subprocess

    done = subprocess.run(
        ["shadow-hdk-linux-sandbox", "--probe"], capture_output=True, text=True, check=False
    )
    return done.returncode == 0


async def test_a_sandbox_that_does_not_actually_confine_is_refused(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """The proof's own proof (D36). A wrapper that *says* it confines and does not — a broken
    install, a future macOS that ignores the profile — must be caught at construction, not found
    in the record after a write landed outside. Without this test a `_prove` that returned
    `proven=True` without watching anything would pass every other test here, because the real
    sandbox works."""
    from shadow_hdk.adapters.environment import local as module

    class Pretends(module.LocalSandbox):
        def wrap(self, argv: list[str], *, root: Any, mode: str) -> list[str]:
            return argv  # confines nothing

    monkeypatch.setattr(module, "local_sandboxes", lambda: (Pretends("pretend", "/bin/true"),))

    with pytest.raises(CannotEnforce, match="did not see the denials"):
        await LocalEnvironment.open(a_root(tmp_path), mode="workspace-write")
