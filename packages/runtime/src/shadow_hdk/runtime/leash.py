"""A leash: run a program in its own process group, with a timeout, a capped output, and a
scrubbed environment.

Extracted from the subprocess sandbox in Phase 11, when a second sandbox needed exactly the same
rules and the invariant that **no adapter imports another** said it could not have them by
inheritance. That invariant exists so a host can install any subset of adapters; the price is that
what two of them share has to live below both. This does.

A leash is not a boundary. It stops a runaway; it does not stop a determined program. Which sandbox
wraps it decides whether there is a box around the program at all.
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import os
import resource
import signal
import sys
from collections.abc import Callable
from pathlib import Path

from shadow_hdk.kernel.observations import Completed, Failed, Observation

KEPT_ENV = ("PATH", "LANG", "LC_ALL")
"""The environment a leashed program sees. Everything else — every secret the host process holds —
is withheld, because a model-written script must not be able to read the operator's keys.

**`HOME` is not kept** (BUG-009). A script whose profile declared `writes: {workspace}` could read
`~/.ssh` or empty the operator's home directory, and nothing in its effects said so. `TMPDIR` is
not inherited either: it is set to the workspace, so a program that writes a temporary file writes
it where the profile already permits.
"""

MEMORY_LIMIT_ENFORCED = hasattr(resource, "prlimit") and sys.platform.startswith("linux")
"""Whether `memory_mb` is a limit or a wish on this platform.

Linux has `prlimit` and enforces `RLIMIT_AS`; **macOS has neither** — `setrlimit` there answers
*current limit exceeds maximum limit* for any finite value. This is a plain platform statement
rather than a measurement, because measuring it means setting a limit on the process doing the
asking, and macOS would not let it be put back. `adapters.md` says the same, instead of
documenting a knob that silently does nothing.
"""


def cap(raw: bytes, limit: int) -> tuple[str, bool]:
    """Decode and truncate. The flag says whether anything was cut, because an agent reasoning
    from half an answer while believing it whole is a worse failure than one told it got half."""
    text = raw.decode("utf-8", errors="replace")
    if len(text) <= limit:
        return text, False
    return text[:limit], True


async def _read_capped(
    stream: asyncio.StreamReader | None, limit: int, when_full: Callable[[], None]
) -> tuple[str, bool]:
    """Collect up to the cap, then **keep reading and throw the rest away**.

    `communicate()` buffered everything before the cap, so `output_limit` bounded what the agent
    saw and not what the host held: forty megabytes of output was forty megabytes of memory.
    Collecting only up to the cap fixes that — but *stopping* reading does not, because a paused
    pipe never reports EOF and the process can then never be reaped, which is a deadlock with the
    child already dead (measured: the step hung until the test runner gave up). So the tap stays
    open and the rest goes down the drain, while `when_full` ends the tree so there is little of it.
    """
    if stream is None:
        return "", False
    collected = bytearray()
    truncated = False
    while True:
        chunk = await stream.read(64 * 1024)
        if not chunk:
            break
        if len(collected) < limit:
            collected.extend(chunk)
        elif not truncated:
            truncated = True
            when_full()
    text, cut = cap(bytes(collected), limit)
    return text, truncated or cut


def _limit_memory(pid: int, megabytes: int) -> None:
    """Cap the child's address space, from **this** side of the fork.

    Not `preexec_fn`: that runs between fork and exec in a process that has threads, where it is
    unsafe, and where any failure surfaces as an opaque *Exception occurred in preexec_fn* that
    takes the whole step with it — measured, on the very platform that refuses the limit.
    `prlimit` sets another process's limit from here, and exists only where the limit does.
    """
    limit = megabytes * 1024 * 1024
    with contextlib.suppress(ValueError, OSError, AttributeError, ProcessLookupError):
        resource.prlimit(pid, resource.RLIMIT_AS, (limit, limit))  # type: ignore[attr-defined]


def _end_the_group(process: asyncio.subprocess.Process) -> None:
    """Kill the process group, whatever is left of it (D35).

    A step owns the tree it starts. `kill()` reached the direct child only, so a program that
    backgrounded something and exited cleanly left it running after the step returned — an effect
    with no step to attribute it to, outliving the lease that permitted it.

    The group id is the child's own pid, because `start_new_session` made it a session leader.
    Asking `getpgid` instead fails once the child has been reaped — which is exactly the moment
    its children are still alive and this matters most.
    """
    if process.pid is None:  # pragma: no cover — a process that never started
        return
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        os.killpg(process.pid, signal.SIGKILL)


async def run_leashed(
    argv: list[str],
    *,
    cwd: Path,
    timeout_s: float,
    output_limit: int,
    memory_mb: int | None = None,
) -> Observation:
    """Run `argv` under the rules. A failure to start, or a timeout, is a `Failed`."""
    environment = {name: os.environ[name] for name in KEPT_ENV if name in os.environ}
    environment["TMPDIR"] = str(cwd)
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=cwd,
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,  # its own group, so the whole tree can be ended at once (D35)
        )
    except OSError as broken:
        return Failed(f"{type(broken).__name__}: {broken}")
    if memory_mb is not None and process.pid is not None:
        # A moment after exec rather than before it: the window is microseconds, and the
        # alternative is a fork-time hook that is unsafe in a process with threads.
        _limit_memory(process.pid, memory_mb)
    try:
        try:
            async with asyncio.timeout(timeout_s):
                # **Both streams at once.** Reading one to its end while the other fills its pipe
                # is a deadlock the child cannot escape: it blocks writing to stderr while nothing
                # drains it. And the tree ends the moment either cap is reached, rather than after
                # the program has finished saying what this step will not keep.
                full = functools.partial(_end_the_group, process)
                (stdout, cut_out), (stderr, cut_err) = await asyncio.gather(
                    _read_capped(process.stdout, output_limit, full),
                    _read_capped(process.stderr, output_limit, full),
                )
                await process.wait()
        except TimeoutError:
            return Failed(f"timed out after {timeout_s:g}s")
    finally:
        # Whatever happened — finished, timed out, or capped — nothing this step started is left
        # running (D35).
        _end_the_group(process)
        with contextlib.suppress(ProcessLookupError):
            await process.wait()
    return Completed(
        {
            "exit_code": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "truncated": cut_out or cut_err,
        }
    )


__all__ = ["KEPT_ENV", "MEMORY_LIMIT_ENFORCED", "cap", "run_leashed"]
