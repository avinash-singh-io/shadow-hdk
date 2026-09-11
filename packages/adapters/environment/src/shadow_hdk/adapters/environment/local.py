"""A local environment, confined by the operating system's own sandbox (D49).

Codex's model, taken whole: the OS sandbox around the *process* — `sandbox-exec` on macOS,
bubblewrap on Linux — so the file tools and the shell tool are ordinary and the environment is what
is confined. Nothing here re-implements a sandbox; principle 5 says consume, and the operating
system already ships one.

**Proven at construction, by what is denied (D36).** Before an environment in a confined mode
exists, it tries to write outside its root and must fail, tries to open a socket and must fail, and
writes inside and must succeed. The `Isolation` it then declares is what the proof found — never
what the profile text says. A wrapper that claims to confine and was never watched denying
anything is a claim, and `requires` does not accept a claim.

**Where no sandbox exists, a confined mode is refused** naming what would fix it. `full` always
constructs and declares everything, because on an ordinary host that is the truth.

Measured 2026-09-11 on macOS 26 with `sandbox-exec`: a write outside the root is *Operation not
permitted*; a socket connect is denied; `python3` starts and writes inside. Apple deprecated the
tool years ago and it still works; the day it stops, the proof fails and this refuses rather than
lies.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shadow_hdk.kernel.observations import Observation
from shadow_hdk.runtime.environment import Environment, Isolation, Mode, requires
from shadow_hdk.runtime.leash import run_leashed

PROBE_TIMEOUT_S = 20.0


@dataclass(frozen=True)
class LocalSandbox:
    """One way this operating system can put a process in a box."""

    name: str
    binary: str

    def wrap(self, argv: list[str], *, root: Path, mode: Mode) -> list[str]:
        if mode == "full":
            return argv
        if self.name == "seatbelt":
            return [self.binary, "-p", _seatbelt_profile(root, mode), *argv]
        if self.name == "bubblewrap":
            return [*_bubblewrap_args(self.binary, root, mode), *argv]
        raise AssertionError(self.name)  # pragma: no cover


def local_sandbox() -> LocalSandbox | None:
    """Which sandbox this machine has, reported rather than guessed."""
    if sys.platform == "darwin" and (found := shutil.which("sandbox-exec")):
        return LocalSandbox("seatbelt", found)
    if (found := shutil.which("bwrap")) is not None:
        return LocalSandbox("bubblewrap", found)
    return None


def _seatbelt_profile(root: Path, mode: Mode) -> str:
    """Deny writes and the network; allow writes back under the root for `workspace-write`.

    Reads are left open on purpose: the interpreter has to read its own installation, and the
    derived profile says `reads: everything` for exactly that reason. `/private/var/folders` and
    `/private/tmp` are *not* allowed — a temp file a command wants goes under the root, which is
    where the leash already points `TMPDIR`.
    """
    lines = ["(version 1)", "(allow default)", "(deny network*)", "(deny file-write*)"]
    if mode == "workspace-write":
        lines.append(f'(allow file-write* (subpath "{root}"))')
    return "\n".join(lines)


def _bubblewrap_args(binary: str, root: Path, mode: Mode) -> list[str]:
    args = [binary, "--ro-bind", "/", "/", "--unshare-net", "--die-with-parent"]
    if mode == "workspace-write":
        args += ["--bind", str(root), str(root)]
    return args


def _prove(box: LocalSandbox, root: Path, mode: Mode) -> Isolation:
    """Watch three denials and one allowance, and report what was seen (D36).

    Synchronous on purpose: it runs at construction, once, and it is the thing that decides whether
    construction happens at all.
    """
    outside = root.parent / f".shadow-hdk-probe-{root.name}"
    inside = root / ".shadow-hdk-probe"

    def attempt(script: str) -> tuple[int, str]:
        argv = box.wrap([sys.executable, "-c", script], root=root, mode=mode)
        done = subprocess.run(
            argv, capture_output=True, text=True, timeout=PROBE_TIMEOUT_S, cwd=root, check=False
        )
        return done.returncode, done.stdout + done.stderr

    try:
        _, wrote_outside = attempt(f"open({str(outside)!r}, 'w').write('x'); print('WROTE')")
        writes_confined = "WROTE" not in wrote_outside and not outside.exists()
        _, reached = attempt(
            "import socket; s=socket.socket(); s.settimeout(2); "
            "print('REACHED' if s.connect_ex(('127.0.0.1', 22)) == 0 else 'DENIED')"
        )
        network_denied = "REACHED" not in reached
        _, wrote_inside = attempt(f"open({str(inside)!r}, 'w').write('x'); print('WROTE')")
        inside_ok = ("WROTE" in wrote_inside) if mode == "workspace-write" else True
    finally:
        outside.unlink(missing_ok=True)
        inside.unlink(missing_ok=True)
    return Isolation(
        writes_confined=writes_confined,
        reads_confined=False,
        network_denied=network_denied,
        proven=writes_confined and network_denied and inside_ok,
    )


class LocalEnvironment(Environment):
    """This machine, with a mode. Files by path under the root; commands inside the OS sandbox."""

    def __init__(
        self,
        root: Path | None,
        *,
        mode: Mode,
        isolation: Isolation,
        box: LocalSandbox | None,
        timeout_s: float = 60.0,
        output_limit: int = 64_000,
        at: str = "",
    ) -> None:
        super().__init__(root, mode=mode, isolation=isolation, source="local", at=at)
        self._box = box
        self._timeout_s = timeout_s
        self._output_limit = output_limit

    @classmethod
    async def open(
        cls,
        root: Path | None = None,
        *,
        mode: Mode = "workspace-write",
        timeout_s: float = 60.0,
        output_limit: int = 64_000,
        at: str = "",
    ) -> LocalEnvironment:
        """Construct, proving first. Refuses a confined mode nothing here can enforce."""
        where = (root or Path.cwd()).resolve()
        box = local_sandbox()
        isolation = Isolation.none() if mode == "full" or box is None else _prove(box, where, mode)
        try:
            requires(isolation, mode)
        except Exception as cannot:
            hint = (
                "this machine has no OS sandbox (sandbox-exec on macOS, bwrap on Linux)"
                if box is None
                else f"{box.name} was found but the proof did not see the denials"
            )
            raise type(cannot)(f"{cannot} — {hint}") from None
        return cls(
            where,
            mode=mode,
            isolation=isolation,
            box=box,
            timeout_s=timeout_s,
            output_limit=output_limit,
            at=at,
        )

    # ------------------------------------------------------------------ the mechanism

    async def _read(self, path: str) -> str:
        return self.inside(path).read_text(encoding="utf-8")

    async def _write(self, path: str, content: str) -> int:
        target = self.inside(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode("utf-8")
        target.write_bytes(data)
        return len(data)

    async def _list(self, path: str) -> list[str]:
        where = self.inside(path)
        return sorted(f"{p.name}/" if p.is_dir() else p.name for p in where.iterdir())

    async def _run(self, argv: list[str]) -> Observation:
        wrapped = self._box.wrap(argv, root=self.root, mode=self.mode) if self._box else argv
        return await run_leashed(
            wrapped, cwd=self.root, timeout_s=self._timeout_s, output_limit=self._output_limit
        )


def _any(value: Any) -> Any:  # pragma: no cover — typing helper
    return value


__all__ = ["LocalEnvironment", "LocalSandbox", "local_sandbox"]
