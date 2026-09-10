"""A step owns the process tree it starts (D35, BUG-009).

`run_leashed` killed the direct child on timeout and nothing else, so a backgrounded process
outlived the step that made it — an effect with no step to attribute it to, still running after its
lease ended. **Reproduced before the fix:** a marker file appeared two seconds after the step
returned `Completed`. And `HOME` was in `KEPT_ENV`, so a script that declared `writes: {workspace}`
could read the operator's `~/.ssh` or empty their home directory.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, cast

import anyio
import pytest

from shadow_hdk.kernel import Completed, Failed, Observation
from shadow_hdk.runtime.leash import KEPT_ENV, run_leashed


def said(done: Observation) -> dict[str, Any]:
    """What a completed leashed run reported, narrowed once so every test can read it."""
    assert isinstance(done, Completed), done
    return cast(dict[str, Any], done.output)


def _backgrounds(marker: Path, after: float = 0.6) -> list[str]:
    """A program that starts something and exits at once — the ordinary shape of a runaway.

    The child's own output is redirected, because a grandchild holding the pipe open would keep
    the leash reading until it finished, and then the test would be proving that the leash waits
    rather than that it kills.
    """
    detached = f'sh -c "sleep {after}; echo alive > {marker}" >/dev/null 2>&1 &'
    return ["sh", "-c", f"{detached} echo started"]


async def test_a_backgrounded_process_does_not_outlive_the_step(tmp_path: Path) -> None:
    marker = tmp_path / "marker.txt"
    done = await run_leashed(_backgrounds(marker), cwd=tmp_path, timeout_s=5, output_limit=1000)
    assert isinstance(done, Completed), done
    await anyio.sleep(1.5)
    assert not marker.exists(), "a process the step started was still running after it returned"


async def test_a_timeout_takes_the_whole_tree_with_it(tmp_path: Path) -> None:
    marker = tmp_path / "marker.txt"
    detached = f'sh -c "sleep 0.6; echo alive > {marker}" >/dev/null 2>&1 &'
    hangs = ["sh", "-c", f"{detached} sleep 30"]
    done = await run_leashed(hangs, cwd=tmp_path, timeout_s=0.3, output_limit=1000)
    assert isinstance(done, Failed) and "timed out" in done.error
    await anyio.sleep(1.5)
    assert not marker.exists(), "the timeout killed the child and left its children running"


def test_the_operators_home_is_not_in_what_a_leashed_program_sees() -> None:
    assert "HOME" not in KEPT_ENV


async def test_a_leashed_program_cannot_read_the_operators_home(tmp_path: Path) -> None:
    done = await run_leashed(
        ["sh", "-c", "echo HOME=[$HOME]"], cwd=tmp_path, timeout_s=5, output_limit=200
    )
    output = said(done)
    assert output["stdout"].strip() == "HOME=[]", output


async def test_temporary_files_land_in_the_workspace(tmp_path: Path) -> None:
    """`TMPDIR` is kept, so it must point somewhere the profile already allows."""
    done = await run_leashed(
        ["sh", "-c", "echo TMPDIR=$TMPDIR"], cwd=tmp_path, timeout_s=5, output_limit=200
    )
    output = said(done)
    assert output["stdout"].strip() == f"TMPDIR={tmp_path}", output


async def test_a_memory_limit_is_set_where_the_platform_allows_one(tmp_path: Path) -> None:
    """`adapters.md` documented a `memory_mb` that did not exist at all. What exists now is honest
    about its reach: Linux enforces `RLIMIT_AS` and macOS refuses to set it, so this skips there
    and the spec says which is which — rather than a knob that silently does nothing."""
    import sys

    from shadow_hdk.runtime.leash import MEMORY_LIMIT_ENFORCED

    if not MEMORY_LIMIT_ENFORCED:
        pytest.skip(
            f"{sys.platform} refuses RLIMIT_AS; adapters.md says which platforms enforce it"
        )
    program = "import resource; print(resource.getrlimit(resource.RLIMIT_AS)[0])"
    done = await run_leashed(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        timeout_s=20,
        output_limit=200,
        memory_mb=64,
    )
    output = said(done)
    assert output["stdout"].strip() == str(64 * 1024 * 1024), output


async def test_asking_for_a_memory_limit_never_breaks_the_run(tmp_path: Path) -> None:
    """Where the platform refuses the limit, the program still runs — a best-effort knob that
    turned a step into a `Failed` on macOS would be worse than the missing knob it replaced."""
    done = await run_leashed(
        ["sh", "-c", "echo ran"], cwd=tmp_path, timeout_s=10, output_limit=200, memory_mb=64
    )
    output = said(done)
    assert output["stdout"].strip() == "ran"


async def test_output_is_capped_as_it_arrives(tmp_path: Path) -> None:
    """`communicate()` buffered everything before the cap, so `output_limit` bounded the
    observation and not the memory. A program that writes far more than the limit must still
    return promptly and small."""
    import sys

    flood = "import sys\nfor _ in range(200000): sys.stdout.write('x' * 200)\n"
    began = time.monotonic()
    done = await run_leashed(
        [sys.executable, "-c", flood], cwd=tmp_path, timeout_s=30, output_limit=100
    )
    took = time.monotonic() - began
    output = said(done)
    assert len(output["stdout"]) == 100
    assert output["truncated"] is True
    assert took < 20, f"40MB of output took {took:.1f}s to cap"


async def test_a_full_stderr_does_not_deadlock_the_step(tmp_path: Path) -> None:
    """The other half of reading in chunks: one stream read to its end while the other fills its
    pipe leaves the child blocked on a write nobody drains. Both are read at once and both are
    capped; how much of the second arrives before the tree ends is the program's business."""
    import sys

    both = (
        "import sys\n"
        "sys.stdout.write('o' * 400000); sys.stdout.flush()\n"
        "sys.stderr.write('e' * 400000); sys.stderr.flush()\n"
    )
    began = time.monotonic()
    done = await run_leashed(
        [sys.executable, "-c", both], cwd=tmp_path, timeout_s=20, output_limit=50
    )
    output = said(done)
    assert len(output["stdout"]) <= 50 and len(output["stderr"]) <= 50
    assert output["truncated"] is True
    assert time.monotonic() - began < 15, "the step waited on a pipe nobody was draining"


async def test_a_program_that_cannot_start_is_data(tmp_path: Path) -> None:
    done = await run_leashed(["no-such-program-here"], cwd=tmp_path, timeout_s=5, output_limit=10)
    assert isinstance(done, Failed) and "FileNotFoundError" in done.error
