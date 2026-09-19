"""Linux confinement is native first, and the proof decides which mechanism is in force (D133).

A machine has *candidates*, in the field's order — the `shadow-hdk-linux-sandbox` helper (Landlock
and seccomp applied to itself before `exec`), bubblewrap behind it, seatbelt on macOS — and
`LocalEnvironment.open` proves each in turn (D36) and keeps the first the proof accepts. Nothing is
trusted for being found: a candidate that confines nothing is passed over, and when none confines
the refusal names each one tried. What was watched denying is then on the evidence by name, so a
host reads `landlock` or `bubblewrap` or `seatbelt` beside `proven`.

The helper itself is proven on a Linux kernel — the tests at the end skip elsewhere and run on the
Linux runner; the mechanism-independent rules above run everywhere.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.adapters.environment import local as module
from shadow_hdk.adapters.environment.local import (
    LocalSandbox,
    local_sandbox,
    local_sandboxes,
)
from shadow_hdk.kernel import Completed, Root, Workspace
from shadow_hdk.runtime.environment import CannotEnforce, Isolation, capabilities_of

ON_LINUX = sys.platform == "linux"
HELPER = "shadow-hdk-linux-sandbox"


def a_root(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    return root


# ------------------------------------------------------------------ the candidates, in order


def _pretend_machine(
    monkeypatch: Any,
    *,
    platform: str,
    on_path: dict[str, str],
    helper_probe: int | None = None,
) -> None:
    """A machine as `local_sandboxes` sees it: a platform, what `which` finds, and what the helper
    says to `--probe` (its exit code; `None` when it is not there)."""
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.delenv("SHADOW_HDK_SANDBOX", raising=False)
    monkeypatch.delenv("SHADOW_HDK_LINUX_SANDBOX", raising=False)
    monkeypatch.setattr(module.shutil, "which", lambda name: on_path.get(name))
    monkeypatch.setattr(module, "_helper_installed", lambda: None)

    def probe(binary: str) -> str | None:
        assert binary == on_path[HELPER]
        return "abi 4" if helper_probe == 0 else None

    monkeypatch.setattr(module, "_helper_probe", probe)
    module.local_sandboxes.cache_clear()


def test_on_linux_the_helper_comes_first_and_bubblewrap_behind_it(monkeypatch: Any) -> None:
    _pretend_machine(
        monkeypatch,
        platform="linux",
        on_path={HELPER: "/venv/bin/" + HELPER, "bwrap": "/usr/bin/bwrap"},
        helper_probe=0,
    )
    assert [box.name for box in local_sandboxes()] == ["landlock", "bubblewrap"]
    first = local_sandbox()
    assert first is not None and first.name == "landlock" and first.binary == "/venv/bin/" + HELPER
    assert "abi 4" in first.detail


def test_a_helper_whose_kernel_has_no_landlock_is_not_a_candidate(monkeypatch: Any) -> None:
    """`--probe` exits 120 where Landlock is absent or disabled: the helper is installed and
    useless, and the machine's candidates are what is left."""
    _pretend_machine(
        monkeypatch,
        platform="linux",
        on_path={HELPER: "/venv/bin/" + HELPER, "bwrap": "/usr/bin/bwrap"},
        helper_probe=120,
    )
    assert [box.name for box in local_sandboxes()] == ["bubblewrap"]


def test_without_the_helper_linux_has_bubblewrap_or_nothing(monkeypatch: Any) -> None:
    _pretend_machine(monkeypatch, platform="linux", on_path={"bwrap": "/usr/bin/bwrap"})
    assert [box.name for box in local_sandboxes()] == ["bubblewrap"]
    _pretend_machine(monkeypatch, platform="linux", on_path={})
    assert local_sandboxes() == [] and local_sandbox() is None


def test_on_macos_the_candidate_is_seatbelt_alone(monkeypatch: Any) -> None:
    _pretend_machine(
        monkeypatch,
        platform="darwin",
        on_path={"sandbox-exec": "/usr/bin/sandbox-exec", HELPER: "/x", "bwrap": "/y"},
        helper_probe=0,
    )
    assert [box.name for box in local_sandboxes()] == ["seatbelt"]


def test_an_operator_narrows_the_candidates_to_one_by_name(monkeypatch: Any) -> None:
    """`SHADOW_HDK_SANDBOX=bubblewrap` on a machine that has both: the helper is set aside — a
    CI job proving the fallback, or a machine where one mechanism misbehaves. The proof still
    runs on what is left."""
    _pretend_machine(
        monkeypatch,
        platform="linux",
        on_path={HELPER: "/venv/bin/" + HELPER, "bwrap": "/usr/bin/bwrap"},
        helper_probe=0,
    )
    monkeypatch.setenv("SHADOW_HDK_SANDBOX", "bubblewrap")
    module.local_sandboxes.cache_clear()
    assert [box.name for box in local_sandboxes()] == ["bubblewrap"]


def test_an_unknown_name_in_the_setting_is_refused_naming_the_known_ones(monkeypatch: Any) -> None:
    _pretend_machine(monkeypatch, platform="linux", on_path={"bwrap": "/usr/bin/bwrap"})
    monkeypatch.setenv("SHADOW_HDK_SANDBOX", "firejail")
    module.local_sandboxes.cache_clear()
    with pytest.raises(ValueError, match="firejail.*landlock.*bubblewrap.*seatbelt"):
        local_sandboxes()


# ------------------------------------------------------------------ the helper's argv


def test_the_helper_is_invoked_with_the_mode_and_every_root(tmp_path: Path) -> None:
    box = LocalSandbox("landlock", "/venv/bin/" + HELPER)
    one, two = tmp_path / "one", tmp_path / "two"
    one.mkdir(), two.mkdir()
    workspace = Workspace.of(one).with_root(Root("two", str(two)))

    wrapped = box.wrap(["sh", "-c", "true"], root=workspace, mode="workspace-write")

    assert wrapped == [
        "/venv/bin/" + HELPER,
        "--mode",
        "workspace-write",
        "--root",
        str(one.resolve()),
        "--root",
        str(two.resolve()),
        "--",
        "sh",
        "-c",
        "true",
    ]


def test_read_only_names_no_root_and_full_is_untouched(tmp_path: Path) -> None:
    box = LocalSandbox("landlock", "/venv/bin/" + HELPER)
    root = a_root(tmp_path)

    assert box.wrap(["true"], root=root, mode="read-only") == [
        "/venv/bin/" + HELPER,
        "--mode",
        "read-only",
        "--",
        "true",
    ]
    assert box.wrap(["true"], root=root, mode="full") == ["true"]


# ------------------------------------------------------------------ the proof decides


class ConfinesNothing(LocalSandbox):
    """A candidate that is found and wraps nothing — a broken install, a kernel that ignores
    the profile. The proof must pass it over, never trust it for being first."""

    def wrap(self, argv: list[str], *, root: Path | Workspace, mode: str) -> list[str]:
        return argv


@pytest.mark.skipif(local_sandbox() is None, reason="no OS sandbox on this machine")
async def test_a_candidate_that_confines_nothing_is_passed_over_for_one_that_does(
    tmp_path: Path, monkeypatch: Any
) -> None:
    real = local_sandbox()
    assert real is not None
    monkeypatch.setattr(
        module, "local_sandboxes", lambda: [ConfinesNothing("pretend", "/bin/true"), real]
    )

    env = await LocalEnvironment.open(a_root(tmp_path), mode="workspace-write")

    assert env.isolation.proven is True
    assert env.isolation.mechanism == real.name, "the one the proof accepted, not the first"


async def test_when_no_candidate_confines_the_refusal_names_each_one_tried(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(
        module,
        "local_sandboxes",
        lambda: [ConfinesNothing("pretend", "/bin/true"), ConfinesNothing("other", "/bin/true")],
    )

    with pytest.raises(CannotEnforce) as refused:
        await LocalEnvironment.open(a_root(tmp_path), mode="workspace-write")

    said = str(refused.value)
    assert "pretend" in said and "other" in said, said
    assert "did not see the denials" in said


async def test_where_there_is_no_candidate_the_refusal_names_the_mechanisms_and_the_fix(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(module, "local_sandboxes", lambda: [])

    with pytest.raises(CannotEnforce) as refused:
        await LocalEnvironment.open(a_root(tmp_path), mode="read-only")

    said = str(refused.value)
    assert "shadow-hdk-linux-sandbox" in said and "bwrap" in said and "sandbox-exec" in said, said


# ------------------------------------------------------------------ the mechanism, on the evidence


def test_the_evidence_names_the_mechanism_that_was_watched_denying() -> None:
    watched = Isolation(
        writes_confined=True,
        reads_confined=False,
        network_denied=True,
        proven=True,
        secrets_denied=False,
        mechanism="landlock",
    )

    capabilities = capabilities_of(watched, "workspace-write")

    by_axis = {e.axis: e.source for e in capabilities.evidence}
    assert "landlock" in by_axis["writes"] and "landlock" in by_axis["network"]
    assert capabilities.proven is True


def test_an_honest_no_has_no_mechanism() -> None:
    assert Isolation.none().mechanism == ""
    by_axis = {e.axis: e.source for e in capabilities_of(Isolation.none(), "full").evidence}
    assert "confines" not in by_axis["writes"]


@pytest.mark.skipif(local_sandbox() is None, reason="no OS sandbox on this machine")
async def test_this_machines_environment_says_which_mechanism_confines_it(tmp_path: Path) -> None:
    box = local_sandbox()
    assert box is not None
    env = await LocalEnvironment.open(a_root(tmp_path), mode="workspace-write")

    assert env.isolation.mechanism == box.name
    sources = " ".join(e.source for e in env.capabilities.evidence)
    assert box.name in sources


# ------------------------------------------------------------------ Linux, for real

needs_the_helper = pytest.mark.skipif(
    not ON_LINUX or shutil.which(HELPER) is None,
    reason="the Linux helper is proven on a Linux kernel with it installed (the CI runner)",
)


@needs_the_helper
def test_the_helper_probe_reports_the_kernels_landlock() -> None:
    binary = shutil.which(HELPER)
    assert binary is not None
    done = subprocess.run([binary, "--probe"], capture_output=True, text=True, check=False)

    assert done.returncode == 0, done.stderr
    said = json.loads(done.stdout)
    assert said["supported"] is True and said["landlock_abi"] >= 1
    assert said["version"], said


@needs_the_helper
async def test_on_this_linux_the_helper_is_what_confines_unless_set_aside(
    tmp_path: Path,
) -> None:
    """With nothing narrowing, the helper is the mechanism in force; a CI job that sets
    `SHADOW_HDK_SANDBOX=bubblewrap` proves the fallback the same way and this test then holds
    for the fallback."""
    box = local_sandbox()
    assert box is not None
    env = await LocalEnvironment.open(a_root(tmp_path), mode="workspace-write")

    assert env.isolation.proven is True
    assert env.isolation.mechanism == box.name
    expected = os.environ.get("SHADOW_HDK_SANDBOX", "landlock")
    assert env.isolation.mechanism == expected, (env.isolation, expected)


@needs_the_helper
async def test_under_the_helper_a_write_outside_the_root_leaves_no_file(tmp_path: Path) -> None:
    root = a_root(tmp_path)
    outside = tmp_path / "escaped.txt"
    env = await LocalEnvironment.open(root, mode="workspace-write")

    done = await env.invoke("run_shell", {"command": f"echo bad > {outside}"})

    assert not outside.exists(), "a confined command wrote outside the root"
    assert isinstance(done, Completed) and isinstance(done.output, dict)
    assert done.output["exit_code"] != 0


@needs_the_helper
async def test_under_the_helper_a_socket_is_refused(tmp_path: Path) -> None:
    env = await LocalEnvironment.open(a_root(tmp_path), mode="workspace-write")
    probe = "import socket; s = socket.socket(); print(s.connect_ex(('127.0.0.1', 22)))"

    done = await env.invoke("run_python", {"source": probe})

    assert isinstance(done, Completed) and isinstance(done.output, dict)
    assert str(done.output["stdout"]).strip() != "0", "a confined command reached a socket"


@needs_the_helper
async def test_under_the_helper_devices_are_not_files_in_read_only(tmp_path: Path) -> None:
    """BUG-023's rule holds on Linux too: `git status` opens `/dev/null` read-write and must not
    die of it in `read-only`."""
    env = await LocalEnvironment.open(a_root(tmp_path), mode="read-only")

    done = await env.invoke("run_shell", {"command": "echo x > /dev/null && echo ok"})

    assert isinstance(done, Completed) and isinstance(done.output, dict)
    assert done.output["exit_code"] == 0 and "ok" in str(done.output["stdout"])


@needs_the_helper
async def test_under_the_helper_a_temp_file_lands_under_the_root(tmp_path: Path) -> None:
    """The leash points `TMPDIR` at the root; a command's temp file is a write inside."""
    root = a_root(tmp_path)
    env = await LocalEnvironment.open(root, mode="workspace-write")

    done = await env.invoke(
        "run_python",
        {"source": "import tempfile; f = tempfile.NamedTemporaryFile(delete=False); print(f.name)"},
    )

    assert isinstance(done, Completed) and isinstance(done.output, dict)
    assert done.output["exit_code"] == 0, done.output
    assert str(done.output["stdout"]).strip().startswith(str(root.resolve()))
