"""An isolated environment sits behind a box somebody else built, and is proven by what the box
denies (D50, D36).

Principle 5: a sandbox is a thing this runtime governs, not a thing it builds. `SandboxEnvironment`
takes an `IsolationBackend` that can `open` a `Box` — run a command in it, read and write a file in
it, close it — and everything about *governance* is the same as for the local environment: one
mode, one derivation, one proof.

**The proof grows a second denial.** `contained` proved a box by watching it refuse a socket. That
was the boundary Phase 11 cared about; the boundary BUG-018 was about is a *write outside the
root*, so the proof watches both now. A box that keeps the network out and lets a write escape the
mount is not contained in the sense the mode claims.

The real backend is OpenSandbox. It needs a server and Docker, neither of which is here, so its live
proof **skips** and says why; a fake box proves the translation and — more to the point — proves
the proof.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.environment import SandboxEnvironment
from shadow_hdk.adapters.environment.backends import Box, prove_box
from shadow_hdk.kernel import Completed, ScopeSet
from shadow_hdk.kernel.observations import Observation
from shadow_hdk.runtime.environment import CannotEnforce, Mode


class FakeBox:
    """A box that behaves the way a real one is supposed to: files under a mount, commands that
    can be told to escape or to reach out, and a switch for each so the proof can be watched
    failing as well as passing."""

    def __init__(self, *, confines_writes: bool = True, denies_network: bool = True) -> None:
        self.files: dict[str, str] = {}
        self.ran: list[list[str]] = []
        self.closed = False
        self._confines = confines_writes
        self._denies = denies_network

    async def run(self, argv: list[str], *, timeout_s: float, output_limit: int) -> Observation:
        self.ran.append(argv)
        script = " ".join(argv)
        if "escape" in script:
            return Completed(
                {
                    "exit_code": 0 if not self._confines else 1,
                    "stdout": "" if self._confines else "WROTE",
                }
            )
        if "socket" in script:
            return Completed({"exit_code": 0, "stdout": "DENIED" if self._denies else "REACHED"})
        if "inside" in script:
            return Completed({"exit_code": 0, "stdout": "WROTE"})
        return Completed({"exit_code": 0, "stdout": f"ran: {script}"})

    async def read(self, path: str) -> str:
        return self.files[path]

    async def write(self, path: str, content: str) -> int:
        self.files[path] = content
        return len(content.encode())

    async def list(self, path: str) -> list[str]:
        return sorted(self.files)

    async def close(self) -> None:
        self.closed = True


class FakeBackend:
    name = "fake"

    def __init__(self, **flags: Any) -> None:
        self.flags = flags
        self.opened: list[tuple[Path, Mode]] = []
        self.box: FakeBox | None = None

    def present(self) -> str | None:
        return None

    async def open(self, root: Path, mode: Mode) -> Box:
        self.opened.append((root, mode))
        self.box = FakeBox(**self.flags)
        return self.box


# ------------------------------------------------------------------ the seam holds


async def test_an_isolated_environment_is_opened_with_the_root_and_the_mode(tmp_path: Path) -> None:
    backend = FakeBackend()

    env = await SandboxEnvironment.open(backend, tmp_path, mode="workspace-write")

    assert backend.opened == [(tmp_path.resolve(), "workspace-write")]
    assert env.isolation.proven is True
    by_id = {r.id: r.component.effects for r in await env.registrations()}
    assert by_id["run_shell"].writes == ScopeSet.of("workspace")
    assert by_id["run_shell"].contained is True
    assert by_id["read_file"].reads == ScopeSet.of("workspace"), "a box confines reads too"


async def test_operations_go_to_the_box(tmp_path: Path) -> None:
    backend = FakeBackend()
    env = await SandboxEnvironment.open(backend, tmp_path, mode="workspace-write")
    assert backend.box is not None

    await env.invoke("write_file", {"path": "a.txt", "content": "hi"})
    read = await env.invoke("read_file", {"path": "a.txt"})
    ran = await env.invoke("run_shell", {"command": "echo x"})

    assert backend.box.files == {"a.txt": "hi"}
    assert read == Completed("hi")
    assert isinstance(ran, Completed) and "echo x" in str(ran.output)


async def test_closing_the_environment_closes_the_box(tmp_path: Path) -> None:
    backend = FakeBackend()
    env = await SandboxEnvironment.open(backend, tmp_path, mode="full")
    assert backend.box is not None

    await env.close()

    assert backend.box.closed


# ------------------------------------------------------------------ the proof, both denials


async def test_a_box_that_lets_a_write_escape_is_refused(tmp_path: Path) -> None:
    """The second denial (D50). The old proof watched only a socket; a box passing that and letting
    a write out of the mount is the BUG-018 shape one level up."""
    with pytest.raises(CannotEnforce, match="writes confined"):
        await SandboxEnvironment.open(
            FakeBackend(confines_writes=False), tmp_path, mode="workspace-write"
        )


async def test_a_box_that_reaches_the_network_is_refused(tmp_path: Path) -> None:
    with pytest.raises(CannotEnforce, match="network"):
        await SandboxEnvironment.open(
            FakeBackend(denies_network=False), tmp_path, mode="workspace-write"
        )


async def test_full_mode_still_uses_the_box_and_still_reports_what_it_found(tmp_path: Path) -> None:
    """`full` asks nothing of the proof, but a box that does confine is still reported as
    contained — the mode is what is wanted; `Isolation` is what is true."""
    env = await SandboxEnvironment.open(FakeBackend(), tmp_path, mode="full")

    assert env.isolation.proven is True
    by_id = {r.id: r.component.effects for r in await env.registrations()}
    assert by_id["run_shell"].contained is True


async def test_the_proof_watches_both_denials_and_the_allowance() -> None:
    """Directly, so a mutation that dropped one attempt is seen: three commands run, in order."""
    box = FakeBox()

    found = await prove_box(box, mode="workspace-write")

    assert found.writes_confined and found.network_denied and found.proven
    scripts = [" ".join(a) for a in box.ran]
    assert any("escape" in s for s in scripts), "the write-outside attempt was never made"
    assert any("socket" in s for s in scripts), "the socket attempt was never made"
    assert any("inside" in s for s in scripts), "the write-inside attempt was never made"


# ------------------------------------------------------------------ the real backend


async def test_opensandbox_reports_absent_with_the_fix_where_there_is_no_server() -> None:
    """Never installed, never assumed (D41): an absent backend says so and says how."""
    from shadow_hdk.adapters.environment.opensandbox import OpenSandboxBackend

    backend = OpenSandboxBackend(domain=None, api_key=None)

    why = backend.present()

    assert why is not None
    # Three honest answers, each naming the fix: the extra is not installed, or no server is
    # configured. What is refused is a fourth — a guess.
    assert "OPENSANDBOX" in why or "server" in why or "not installed" in why


@pytest.mark.live
async def test_opensandbox_for_real(tmp_path: Path) -> None:
    """Needs a running OpenSandbox server and Docker. Skips, saying so, everywhere else."""
    from shadow_hdk.adapters.environment.opensandbox import OpenSandboxBackend

    backend = OpenSandboxBackend.from_environment()
    if (why := backend.present()) is not None:
        pytest.skip(why)
    env = await SandboxEnvironment.open(backend, tmp_path, mode="workspace-write")
    try:
        assert env.isolation.proven
    finally:
        await env.close()
