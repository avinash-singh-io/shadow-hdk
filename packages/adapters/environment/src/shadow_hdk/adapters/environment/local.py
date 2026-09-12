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
from shadow_hdk.kernel.workspace import Workspace
from shadow_hdk.runtime.environment import (
    Environment,
    Isolation,
    Mode,
    output_activity,
    requires,
    resolved,
)
from shadow_hdk.runtime.leash import run_leashed

PROBE_TIMEOUT_S = 20.0


@dataclass(frozen=True)
class LocalSandbox:
    """One way this operating system can put a process in a box."""

    name: str
    binary: str

    def wrap(self, argv: list[str], *, root: Path | Workspace, mode: Mode) -> list[str]:
        workspace = root if isinstance(root, Workspace) else Workspace.of(root)
        if mode == "full":
            return argv
        if self.name == "seatbelt":
            return [self.binary, "-p", _seatbelt_profile(workspace, mode), *argv]
        if self.name == "bubblewrap":
            return [*_bubblewrap_args(self.binary, workspace, mode), *argv]
        raise AssertionError(self.name)  # pragma: no cover


def local_sandbox() -> LocalSandbox | None:
    """Which sandbox this machine has, reported rather than guessed."""
    if sys.platform == "darwin" and (found := shutil.which("sandbox-exec")):
        return LocalSandbox("seatbelt", found)
    if (found := shutil.which("bwrap")) is not None:
        return LocalSandbox("bubblewrap", found)
    return None


def _seatbelt_profile(workspace: Workspace, mode: Mode) -> str:
    """Deny writes and the network; allow writes back under the root for `workspace-write`.

    Reads are left open on purpose: the interpreter has to read its own installation, and the
    derived profile says `reads: everything` for exactly that reason. `/private/var/folders` and
    `/private/tmp` are *not* allowed — a temp file a command wants goes under the root, which is
    where the leash already points `TMPDIR`.

    **Devices are not files** (BUG-023). `git` opens `/dev/null` read-write at startup and died
    inside the profile with *could not open '/dev/null'*; so did `echo x > /dev/null`. A write to
    the null device, the zero and randomness devices, or the program's own terminal changes
    nothing in the world, so every mode allows them — including `read-only`, which exists so an
    agent can run `git status`. What is denied is what the proof checks: a write outside the root.
    """
    lines = [
        "(version 1)",
        "(allow default)",
        "(deny network*)",
        "(deny file-write*)",
        '(allow file-write* (literal "/dev/null") (literal "/dev/zero") (literal "/dev/random")'
        ' (literal "/dev/urandom") (literal "/dev/tty") (regex #"^/dev/ttys[0-9]+$")'
        ' (regex #"^/dev/fd/[0-9]+$"))',
    ]
    if mode == "workspace-write":
        # Every root (D76): a workspace of many directories is writable in all of them.
        lines.extend(
            f'(allow file-write* (subpath "{Path(r.path).resolve()}"))' for r in workspace.roots
        )
    return "\n".join(lines)


def _bubblewrap_args(binary: str, workspace: Workspace, mode: Mode) -> list[str]:
    # `--dev /dev`: a fresh devtmpfs with null, zero, random, tty and pts — devices are not files
    # (BUG-023), and a read-only bind of `/` would otherwise be the whole of `/dev` too.
    args = [binary, "--ro-bind", "/", "/", "--dev", "/dev", "--unshare-net", "--die-with-parent"]
    if mode == "workspace-write":
        for r in workspace.roots:
            args += ["--bind", str(Path(r.path).resolve()), str(Path(r.path).resolve())]
    return args


def _prove(box: LocalSandbox, root: Path | Workspace, mode: Mode) -> Isolation:
    """Watch three denials and one allowance, and report what was seen (D36).

    Synchronous on purpose: it runs at construction, once, and it is the thing that decides whether
    construction happens at all. Over many roots (D76) the allowance is watched in **each** and
    the denial outside **all** — a second root the profile did not cover would fail the proof.
    """
    workspace = root if isinstance(root, Workspace) else Workspace.of(root)
    primary = Path(workspace.primary.path).resolve()
    outside = primary.parent / f".shadow-hdk-probe-{primary.name}"
    insides = [Path(r.path).resolve() / ".shadow-hdk-probe" for r in workspace.roots]

    def attempt(script: str) -> tuple[int, str]:
        argv = box.wrap([sys.executable, "-c", script], root=workspace, mode=mode)
        done = subprocess.run(
            argv, capture_output=True, text=True, timeout=PROBE_TIMEOUT_S, cwd=primary, check=False
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
        inside_ok = True
        if mode == "workspace-write":
            for inside in insides:
                _, wrote_inside = attempt(f"open({str(inside)!r}, 'w').write('x'); print('WROTE')")
                inside_ok = inside_ok and "WROTE" in wrote_inside
    finally:
        outside.unlink(missing_ok=True)
        for inside in insides:
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
        workspace: Workspace | None = None,
    ) -> None:
        super().__init__(
            root, mode=mode, isolation=isolation, source="local", at=at, workspace=workspace
        )
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
        workspace: Workspace | None = None,
    ) -> LocalEnvironment:
        """Construct, proving first. Refuses a confined mode nothing here can enforce. `workspace`
        names one or many roots (D76); `root` alone is the one-root workspace."""
        # Resolved before the proof (D76): a relative root would reach the OS profile as written
        # and the sandbox would allow nothing — found by running the README's snippet for real.
        workspace = resolved(workspace or Workspace.of(root or Path.cwd()))
        where = Path(workspace.primary.path)
        box = local_sandbox()
        isolation = (
            Isolation.none() if mode == "full" or box is None else _prove(box, workspace, mode)
        )
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
            workspace=workspace,
        )

    def _prove_now(self, workspace: Workspace, mode: Mode) -> Isolation:
        if mode == "full" or self._box is None:
            return Isolation.none()
        return _prove(self._box, workspace, mode)

    # ------------------------------------------------------------------ the mechanism

    async def _read(self, path: str) -> str:
        return self.inside(path).read_text(encoding="utf-8")

    async def _write(self, path: str, content: str) -> int:
        target = self.inside(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode("utf-8")
        target.write_bytes(data)
        return len(data)

    async def _delete(self, path: str) -> None:
        self.inside(path).unlink()

    async def _list(self, path: str) -> list[str]:
        where = self.inside(path)
        return sorted(f"{p.name}/" if p.is_dir() else p.name for p in where.iterdir())

    async def _run(self, argv: list[str]) -> Observation:
        wrapped = self._box.wrap(argv, root=self.workspace, mode=self.mode) if self._box else argv
        return await run_leashed(
            wrapped,
            cwd=self.root,
            timeout_s=self._timeout_s,
            output_limit=self._output_limit,
            on_output=output_activity(),
        )


def _any(value: Any) -> Any:  # pragma: no cover — typing helper
    return value


__all__ = ["LocalEnvironment", "LocalSandbox", "local_sandbox"]
