"""gVisor and Firecracker as backends that must prove themselves.

Written on a machine that has neither, under a rule against installing either — so what is
claimed here is the **shape**, and each backend's proof is a `[~]` until a Linux host runs it. A
backend that has never been run is not done, and this module does not say it is.

Each **says** what it is, and neither is believed on its word (D36). `declares()` is a claim for
the record: gVisor's user-space kernel announces itself in `dmesg`, and Firecracker's virtual
hardware names its maker in the guest's DMI product name. That is *all* it is — matching those
strings was once the whole proof, and a five-line shell script called `runsc` passed it. The proof
is now a capability test the **sandbox** runs through `wrap`: something a contained program must
not manage, attempted and denied.
"""

from __future__ import annotations

import shutil
import subprocess

PROBE_TIMEOUT_S = 15.0


def _run_quietly(argv: list[str]) -> str | None:
    """Stdout of a short command, or `None` if it could not run or did not finish."""
    try:
        done = subprocess.run(  # noqa: S603 — argv is ours, not a model's
            argv, capture_output=True, text=True, timeout=PROBE_TIMEOUT_S, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


class GVisor:
    """`runsc do`: one command in a sandbox over the current directory, network off."""

    name = "gvisor"
    binary = "runsc"

    def present(self) -> bool:
        return shutil.which(self.binary) is not None

    def wrap(self, argv: list[str]) -> list[str]:
        # `--network=none` by construction. A box that reaches is a different component (Phase 3:
        # `reaches = network or not contained`), declared as such rather than this one with a flag.
        return [self.binary, "--network=none", "do", *argv]

    def declares(self) -> str | None:
        """What gVisor says about itself — a claim, never the proof (D36)."""
        if not self.present():
            return None
        out = _run_quietly(self.wrap(["dmesg"]))
        if out is None:
            return None
        announced = next((line for line in out.splitlines() if "gVisor" in line), None)
        return announced.strip() if announced else None


class Firecracker:
    """A microVM, reached through a launcher the deployment supplies.

    There is no `firecracker do`. Booting a guest needs a kernel, a rootfs and an API socket, and
    executing inside it needs a channel — so the deployment provides the command that does all of
    that and runs argv inside, and this backend prefixes it. Pretending a single binary could do it
    would be a fake, and this phase does not fake a backend.
    """

    name = "firecracker"

    def __init__(self, *, launch: list[str]) -> None:
        if not launch:
            raise ValueError(
                "Firecracker needs a `launch` command that boots the guest and executes argv "
                "inside it; there is no built-in way to run one command in a microVM"
            )
        self.launch = list(launch)

    @property
    def binary(self) -> str:
        return self.launch[0]

    def present(self) -> bool:
        return shutil.which(self.binary) is not None

    def wrap(self, argv: list[str]) -> list[str]:
        return [*self.launch, *argv]

    def declares(self) -> str | None:
        """What the guest says about itself — a claim, never the proof (D36)."""
        if not self.present():
            return None
        out = _run_quietly(self.wrap(["cat", "/sys/devices/virtual/dmi/id/product_name"]))
        if out is not None and "Firecracker" in out:
            return f"DMI product name: {out.strip()}"
        out = _run_quietly(self.wrap(["dmesg"]))
        if out is None:
            return None
        announced = next((line for line in out.splitlines() if "Firecracker" in line), None)
        return announced.strip() if announced else None


__all__ = ["Firecracker", "GVisor", "PROBE_TIMEOUT_S"]
