"""gVisor and Firecracker as backends that must prove themselves — the half buildable here.

This machine has neither binary and the rules forbid installing them, so what these tests prove is
the **shape**: that each backend reports absence honestly, produces the argv it would run without
running anything, and refuses to claim a proof it did not observe. The live tests below **skip**
when the binary is absent — never pass, never fail — and the command that would run them on a
Linux host is in this phase's tasks.

A backend that has never been run is not done, and this file does not say it is.
"""

from __future__ import annotations

import shutil

import pytest

from shadow_hdk.adapters.contained import ContainedSandbox, NotContained
from shadow_hdk.adapters.contained.backends import Firecracker, GVisor

ARGV = ["/bin/sh", "-c", "echo hello"]


# ---------------------------------------------------------------- gVisor


def test_gvisor_reports_presence_by_the_binary_and_nothing_else() -> None:
    assert GVisor().present() == (shutil.which("runsc") is not None)
    assert GVisor().binary == "runsc"


def test_gvisor_wraps_argv_into_a_sandboxed_do_without_network() -> None:
    """`runsc do` runs one command in a sandbox over the current directory, which is exactly a
    leashed argv. The network is off by construction — a box that reaches is a different
    component (Phase 3's `reaches = network or not contained`)."""
    assert GVisor().wrap(ARGV) == ["runsc", "--network=none", "do", *ARGV]


def test_gvisor_does_not_claim_a_proof_when_absent() -> None:
    if shutil.which("runsc") is not None:
        pytest.skip("runsc is present here; the absent-path test does not apply")
    assert GVisor().probe() is None


def test_gvisor_absent_refuses_the_sandbox_naming_runsc(tmp_path) -> None:  # type: ignore[no-untyped-def]
    if shutil.which("runsc") is not None:
        pytest.skip("runsc is present here")
    with pytest.raises(NotContained, match="runsc"):
        ContainedSandbox(tmp_path, backend=GVisor())


# ---------------------------------------------------------------- Firecracker


def test_firecracker_needs_a_launcher_because_it_has_no_do() -> None:
    """Firecracker boots a microVM from a kernel and a rootfs over an API socket; there is no
    `firecracker do`. So the deployment supplies the command that boots the guest and executes
    argv inside it, and the backend wraps by prefixing it. Pretending otherwise would be a fake."""
    backend = Firecracker(launch=["fc-exec", "--vm", "sandbox"])
    assert backend.wrap(ARGV) == ["fc-exec", "--vm", "sandbox", *ARGV]
    assert backend.binary == "fc-exec"


def test_firecracker_reports_presence_by_its_launcher() -> None:
    backend = Firecracker(launch=["definitely-not-installed-anywhere"])
    assert backend.present() is False
    assert backend.probe() is None


def test_firecracker_with_no_launcher_is_refused_at_construction() -> None:
    with pytest.raises(ValueError, match="launch"):
        Firecracker(launch=[])


# ---------------------------------------------------------------- live, and honest about it


@pytest.mark.live
def test_gvisor_proves_itself_on_a_host_that_has_it(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Settled by: `uv run pytest -m live tests/adapters/contained/test_backends.py -k gvisor`
    on a Linux host with `runsc` on PATH."""
    if shutil.which("runsc") is None:
        pytest.skip("runsc is not present; this proof needs a Linux host with gVisor")
    sandbox = ContainedSandbox(tmp_path, backend=GVisor())
    assert "gVisor" in sandbox.proof.observed


@pytest.mark.live
def test_firecracker_proves_itself_on_a_host_that_has_it(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Settled by: `SHADOW_HDK_FC_LAUNCH="fc-exec --vm sandbox" uv run pytest -m live
    tests/adapters/contained/test_backends.py -k firecracker` on a Linux host with a configured
    microVM and a launcher that executes argv inside it."""
    import os

    launch = os.environ.get("SHADOW_HDK_FC_LAUNCH", "").split()
    if not launch or shutil.which(launch[0]) is None:
        pytest.skip("no Firecracker launcher configured; this proof needs a Linux host with one")
    sandbox = ContainedSandbox(tmp_path, backend=Firecracker(launch=launch))
    assert "Firecracker" in sandbox.proof.observed
