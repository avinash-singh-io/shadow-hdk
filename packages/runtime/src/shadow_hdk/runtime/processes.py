"""Ending what a step started (D35).

Two callers needed the same rule and had two answers, one of which was wrong. The leash killed the
process **group**, because a program that backgrounds something and exits cleanly leaves an effect
with no step to attribute it to. The ACP bridge sent `SIGTERM` and waited without a deadline, so a
child that ignores the signal wedged the caller forever (BUG-011).

It lives here rather than in either of them because an adapter may not import another adapter
(the stands-alone invariant), and a rule with two implementations is a rule with one bug.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal

__all__ = ["end_the_group", "stop_or_kill"]


def end_the_group(process: asyncio.subprocess.Process) -> None:
    """Kill the process group, whatever is left of it.

    A step owns the tree it starts. `kill()` reaches the direct child only, so a program that
    backgrounded something and exited cleanly left it running after the step returned — an effect
    with no step to attribute it to, outliving the lease that permitted it.

    The group id is the child's own pid, because the caller starts it with `start_new_session`,
    which makes it a session leader. Asking `getpgid` instead fails once the child has been reaped
    — which is exactly the moment its children are still alive and this matters most.
    """
    if process.pid is None:  # pragma: no cover — a process that never started
        return
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        os.killpg(process.pid, signal.SIGKILL)


async def stop_or_kill(process: asyncio.subprocess.Process, *, grace_s: float) -> bool:
    """Ask the process to go, and make it go if it will not. `True` if it had to be made.

    The grace period is the point: a child agent asked politely gets to flush what it was writing
    and close what it had open, which is why this is not simply a kill. But *asking* is not the
    same as it going, so the deadline is enforced and the group is ended — the tree, not the one
    process, because by then it has proven it is not cooperating.
    """
    if process.returncode is not None:
        # It is already gone — but its children are not necessarily, and a leader that exited
        # cleanly the moment it had backgrounded something is the exact case D35 was written for.
        end_the_group(process)
        return False

    with contextlib.suppress(ProcessLookupError):
        process.terminate()
    try:
        await asyncio.wait_for(process.wait(), grace_s)
    except TimeoutError:
        end_the_group(process)
        await process.wait()
        return True
    else:
        # It answered. Its own children did not necessarily hear anything, so the tree still goes.
        end_the_group(process)
        return False
