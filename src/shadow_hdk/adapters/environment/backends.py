"""The seam an isolation platform plugs into, and the proof every box has to pass (D50).

Principle 5: a sandbox is a thing this runtime *governs*, not a thing it builds. What it needs
from one is small and stated here: open a **box** for a root and a mode; in the box, run a
command, read and write a file, list a directory; close it. OpenSandbox, E2B, Daytona and the next
one each fit that in one adapter and no more.

**The proof grows a second denial.** Phase 11 proved a box by watching it refuse a socket (D36).
The boundary BUG-018 was about is a write *outside the root*, so a box is proven contained only if
it denies both — a box that keeps the network out and lets a write escape the mount is the
BUG-018 shape one level up, and the mode would be claiming something the box does not make true.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from shadow_hdk.kernel.observations import Completed, Observation
from shadow_hdk.runtime.environment import Isolation, Mode

PROBE_TIMEOUT_S = 30.0
MOUNT = "/workspace"
"""Where the root is mounted inside a box. Fixed rather than configurable: an agent's paths are
relative to the environment's root, and a box that mounted it elsewhere would have to translate
every one of them."""


@runtime_checkable
class Box(Protocol):
    """One open sandbox, with the root mounted at `MOUNT`."""

    async def run(self, argv: list[str], *, timeout_s: float, output_limit: int) -> Observation: ...

    async def read(self, path: str) -> str: ...

    async def write(self, path: str, content: str) -> int: ...

    async def delete(self, path: str) -> None: ...

    async def list(self, path: str) -> list[str]: ...

    async def close(self) -> None: ...


@runtime_checkable
class IsolationBackend(Protocol):
    """A platform that can open boxes. Says whether it is reachable, and how to fix it if not."""

    @property
    def name(self) -> str: ...

    def present(self) -> str | None:
        """`None` when a box can be opened; otherwise why not, and what would fix it."""
        ...

    async def open(self, root: Path, mode: Mode) -> Box: ...


def _said(observation: Observation) -> str:
    if isinstance(observation, Completed) and isinstance(observation.output, dict):
        return str(observation.output.get("stdout", ""))
    return ""


async def prove_box(box: Box, *, mode: Mode) -> Isolation:
    """Three attempts, watched: a write outside the mount, a socket, a write inside (D36, D50).

    Reads are taken as confined in a box — the process cannot see the host at all — which is the
    one thing a box gives that the OS sandbox around a local process does not.
    """
    escape = await box.run(
        ["python3", "-c", "open('/etc/shadow-hdk-escape', 'w').write('x'); print('WROTE')"],
        timeout_s=PROBE_TIMEOUT_S,
        output_limit=4_000,
    )
    writes_confined = "WROTE" not in _said(escape)
    reach = await box.run(
        [
            "python3",
            "-c",
            "import socket; s=socket.socket(); s.settimeout(3); "
            "print('REACHED' if s.connect_ex(('1.1.1.1', 53)) == 0 else 'DENIED')",
        ],
        timeout_s=PROBE_TIMEOUT_S,
        output_limit=4_000,
    )
    network_denied = "REACHED" not in _said(reach)
    inside_ok = True
    if mode == "workspace-write":
        inside = await box.run(
            [
                "python3",
                "-c",
                f"open('{MOUNT}/.shadow-hdk-inside', 'w').write('x'); print('WROTE')",
            ],
            timeout_s=PROBE_TIMEOUT_S,
            output_limit=4_000,
        )
        inside_ok = "WROTE" in _said(inside)
    return Isolation(
        writes_confined=writes_confined,
        reads_confined=True,
        network_denied=network_denied,
        proven=writes_confined and network_denied and inside_ok,
        secrets_denied=None,
    )


__all__ = ["MOUNT", "PROBE_TIMEOUT_S", "Box", "IsolationBackend", "prove_box"]
