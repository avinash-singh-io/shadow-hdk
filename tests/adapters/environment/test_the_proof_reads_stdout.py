"""BUG-057: the D36 proof decides from what the probe *printed*, never from a traceback.

Python 3.13+ echoes the `-c` source line in a traceback, so a **denied** write's stderr contains
the literal `WROTE` from the probe's own script. A proof that searched stdout+stderr read the
denial as a write, returned `writes_confined=False`, and every confined mode refused to open on
3.13 and 3.14. The rule that fixes it is mechanism-independent: markers are read from stdout with a
zero exit code, and nothing else — which is also what every future sandbox helper will be held to.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from shadow_hdk.adapters.environment.local import LocalSandbox, _prove, local_sandbox
from shadow_hdk.kernel import Workspace


class EchoingBox:
    """A sandbox double whose every attempt *denies*: it prints the probe's script to stderr —
    exactly what a 3.13+ traceback does — and exits non-zero without running it."""

    name = "echoing"
    binary = sys.executable

    def wrap(self, argv: list[str], *, root: Path | Workspace, mode: str) -> list[str]:
        script = argv[-1]
        return [
            sys.executable,
            "-c",
            "import sys; sys.stderr.write(sys.argv[1]); sys.exit(1)",
            script,
        ]


def test_a_denial_whose_traceback_echoes_the_marker_is_still_a_denial(tmp_path: Path) -> None:
    root = tmp_path / "work"
    root.mkdir()
    isolation = _prove(EchoingBox(), root, "workspace-write")  # type: ignore[arg-type]
    assert isolation.writes_confined is True, "stderr carrying WROTE is not a write"
    assert isolation.network_denied is True, "stderr carrying REACHED is not a reach"
    # The inside write was *denied* by this box too, so the proof must not be `proven`: a box
    # that denies everything cannot confine a workspace-write mode honestly.
    assert isolation.proven is False


@pytest.mark.skipif(local_sandbox() is None, reason="no OS sandbox on this machine")
def test_the_real_proof_holds_on_the_interpreter_running_the_suite(tmp_path: Path) -> None:
    """On the interpreter the suite runs under — 3.12 today, 3.14 in the matrix — the three legs
    hold: outside denied, network denied, inside allowed."""
    root = tmp_path / "work"
    root.mkdir()
    box = local_sandbox()
    assert box is not None
    isolation = _prove(box, root, "workspace-write")
    assert isolation.proven is True, isolation


def test_the_interpreter_echoes_source_in_a_traceback_on_313_and_later() -> None:
    """The fact the fix rests on, measured rather than remembered."""
    done = subprocess.run(
        [sys.executable, "-c", "open('/nonexistent-dir/x','w').write('x'); print('WROTE')"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode != 0 and "WROTE" not in done.stdout
    echoes = "WROTE" in done.stderr
    assert echoes == (sys.version_info >= (3, 13)), (sys.version_info, done.stderr)


def test_the_proof_names_stdout_as_its_only_marker_source() -> None:
    """A guard on the source itself, so the regression cannot creep back in a refactor."""
    import inspect

    source = inspect.getsource(_prove)
    assert "done.stdout + done.stderr" not in source, "markers are read from stdout alone"
    assert isinstance(LocalSandbox, type)
