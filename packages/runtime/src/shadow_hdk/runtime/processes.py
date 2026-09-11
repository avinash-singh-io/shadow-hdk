"""Ending what a step started (D35).

Two callers needed the same rule and had two answers, one of which was wrong. The leash killed the
process **group**, because a program that backgrounds something and exits cleanly leaves an effect
with no step to attribute it to. The ACP bridge sent `SIGTERM` and waited without a deadline, so a
child that ignores the signal wedged the caller forever (BUG-011).

It lives here rather than in either of them because an adapter may not import another adapter
(the stands-alone invariant), and a rule with two implementations is a rule with one bug.

**And the process that started them (D53, BUG-019).** `close()` ends a session's group — when it
is reached. A person leaving a REPL with Ctrl-C, a `sys.exit`, a `SIGTERM` from a supervisor, an
exception nobody caught: none of those promise to reach it, and two `claude -p` children were
found alive ten hours after their sessions had ended, each holding a subscription seat. So every
session leader the runtime starts is `hold`-ed here, and the interpreter's own ending — by
whichever door — ends them all. `atexit` covers the normal exits and every propagated exception,
`KeyboardInterrupt` included; a `SIGTERM` or `SIGHUP` with the default disposition would skip
`atexit`, so those get a handler **only when the host has installed none** — a host with its own
handler keeps it, and is expected to exit through it.
"""

from __future__ import annotations

import asyncio
import atexit
import contextlib
import os
import signal
import threading

__all__ = ["end_the_group", "end_everything_held", "held_now", "hold", "let_go", "stop_or_kill"]


class _Leader:
    """Anything with a `pid` that was started with `start_new_session`."""

    pid: int | None


_held: set[int] = set()
_installed = False
_lock = threading.Lock()


def hold(process: _Leader) -> None:
    """Keep this session leader's pid until it is let go, and make sure the interpreter's ending
    ends it. Idempotent; the finaliser is installed on the first call."""
    global _installed
    if process.pid is None:  # pragma: no cover — a process that never started
        return
    with _lock:
        _held.add(process.pid)
        if not _installed:
            _installed = True
            atexit.register(end_everything_held)
            for number in (signal.SIGTERM, signal.SIGHUP):
                _chain_if_default(number)


def let_go(process: _Leader) -> None:
    """The caller has ended it (or it ended). A pid let go of is never killed at exit — by then it
    may be somebody else's."""
    if process.pid is not None:
        with _lock:
            _held.discard(process.pid)


def held_now() -> frozenset[int]:
    with _lock:
        return frozenset(_held)


def end_everything_held() -> None:
    """Kill every held group. Called at exit; safe to call any time."""
    with _lock:
        pids = set(_held)
        _held.clear()
    for pid in pids:
        with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
            os.killpg(pid, signal.SIGKILL)


def _chain_if_default(number: signal.Signals) -> None:
    """Handle `number` only where nothing does: the default disposition ends the process without
    running `atexit`. The handler ends what is held, restores the default and re-raises the signal,
    so the exit status a supervisor sees is the one it sent."""
    if threading.current_thread() is not threading.main_thread():  # pragma: no cover
        return  # signal handlers may only be installed from the main thread; atexit still holds
    with contextlib.suppress(ValueError, OSError):
        if signal.getsignal(number) is not signal.SIG_DFL:
            return

        def then_go(received: int, _frame: object) -> None:
            end_everything_held()
            signal.signal(received, signal.SIG_DFL)
            os.kill(os.getpid(), received)

        signal.signal(number, then_go)


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
    let_go(process)


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
