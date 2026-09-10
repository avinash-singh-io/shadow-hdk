"""Asking a process to go is not the same as it going (D35, BUG-011).

The leash already owned this: a step owns the process tree it starts, and it kills the group when it
returns. The ACP bridge's `stop()` did not — it sent `SIGTERM` and then `wait()`ed, with no deadline
and no second signal, so a child that ignores the signal wedges the caller **forever**. The two are
one rule, so they are one implementation, and it lives below both because an adapter may not import
another (the stands-alone invariant).

Everything here runs against real processes this test starts and reaps: a program that ignores
`SIGTERM`, one that answers it, and one that backgrounds a child and exits.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
import time

from shadow_hdk.runtime.processes import end_the_group, stop_or_kill

DEAF = """
import signal, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
print("up", flush=True)
time.sleep(300)
"""

POLITE = """
import sys, time
print("up", flush=True)
time.sleep(300)
"""

LEAVES_A_CHILD = """
import subprocess, sys
# The grandchild gets its own stdio: inheriting the pipe would hold it open after the parent exits,
# and `Process.wait()` does not complete until the transport's pipes close.
child = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(300)"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
)
print(child.pid, flush=True)
sys.exit(0)
"""

ANSWERS_AND_LEAVES_A_CHILD = """
import signal, subprocess, sys, time
child = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(300)"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
)
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
print(child.pid, flush=True)
time.sleep(300)
"""

GRACE = 1.0
"""Short, because the test's subject is that the deadline exists at all."""


async def _started(program: str) -> tuple[asyncio.subprocess.Process, str]:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        program,
        stdout=asyncio.subprocess.PIPE,
        start_new_session=True,
    )
    assert process.stdout is not None
    first = (await asyncio.wait_for(process.stdout.readline(), 10.0)).decode().strip()
    return process, first


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


async def test_a_deaf_process_is_killed_rather_than_waited_on() -> None:
    """The bug: `terminate()` then an unbounded `wait()` never returns for a child that ignores it.

    Bounded by the test's own deadline as well as the code's, because a hanging test is worse than
    a failing one — if the grace period is not enforced, this **fails** rather than wedging the run.
    """
    process, _ = await _started(DEAF)
    started = time.monotonic()

    killed = await asyncio.wait_for(stop_or_kill(process, grace_s=GRACE), 20.0)

    assert killed is True, "the process went quietly, which a program ignoring SIGTERM cannot"
    assert process.returncode is not None, "stop returned while the process was still running"
    assert time.monotonic() - started < 10.0


async def test_a_process_that_goes_quietly_is_not_killed() -> None:
    """The other half, and the reason for a grace period at all: a child that is asked politely
    gets to exit on its own terms — flushing, closing, saying goodbye — before anything harder."""
    process, _ = await _started(POLITE)

    killed = await asyncio.wait_for(stop_or_kill(process, grace_s=10.0), 20.0)

    assert killed is False, "a process that answered SIGTERM was killed anyway"
    assert process.returncode == -signal.SIGTERM


async def test_nothing_the_process_started_is_left_running() -> None:
    """D35 one layer up. The direct child exits cleanly and immediately, so `wait()` is satisfied
    and the polite path is taken — while the grandchild it backgrounded is still there."""
    process, said = await _started(LEAVES_A_CHILD)
    grandchild = int(said)
    await asyncio.wait_for(process.wait(), 10.0)
    assert _alive(grandchild), "the arrangement failed: the grandchild was never running"

    await asyncio.wait_for(stop_or_kill(process, grace_s=GRACE), 20.0)

    await asyncio.sleep(0.2)
    assert not _alive(grandchild), "the tree outlived the step that started it"


async def test_ending_a_group_twice_is_not_an_error() -> None:
    """`stop()` is called from `__aexit__` and from the timeout path, and a run that timed out and
    then closed its bridge would otherwise raise on the way out."""
    process, _ = await _started(POLITE)
    end_the_group(process)
    await asyncio.wait_for(process.wait(), 10.0)

    end_the_group(process)  # the second one is the claim

    assert process.returncode is not None


async def test_a_process_that_already_ended_reports_that_it_went_on_its_own() -> None:
    """Already gone is not *killed*, and the answer says so — a caller logging "had to be killed"
    on every clean exit teaches its reader to ignore the line.

    The group is still ended, because a leader that exits the instant it has backgrounded something
    is the case D35 exists for, and its exit status is untouched by that.
    """
    process, _ = await _started(POLITE)
    process.kill()
    await asyncio.wait_for(process.wait(), 10.0)
    ended_as = process.returncode

    killed = await asyncio.wait_for(stop_or_kill(process, grace_s=GRACE), 20.0)

    assert killed is False
    assert process.returncode == ended_as, "the exit status changed under a second signal"


async def test_a_child_that_answers_still_has_its_tree_ended() -> None:
    """Found by a mutation that survived: the polite path did not end the group, and every test
    passed — because the only test with a grandchild had a leader that had already exited by the
    time `stop_or_kill` was called, which takes the already-reaped branch instead.

    Cooperating is not the same as passing the signal on. This one is alive, answers `SIGTERM`, and
    the process it backgrounded heard nothing.
    """
    process, said = await _started(ANSWERS_AND_LEAVES_A_CHILD)
    grandchild = int(said)
    assert _alive(grandchild), "the arrangement failed: the grandchild was never running"

    killed = await asyncio.wait_for(stop_or_kill(process, grace_s=10.0), 20.0)

    assert killed is False, "the arrangement failed: this child does answer SIGTERM"
    await asyncio.sleep(0.2)
    assert not _alive(grandchild), "a polite child's tree was left running"
