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
from dataclasses import dataclass
from pathlib import Path

from shadow_hdk.kernel.observations import Completed, Failed, Observation
from shadow_hdk.runtime.processes import end_the_group, hold

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
    stream: asyncio.StreamReader | None,
    limit: int,
    when_full: Callable[[], None],
    on_chunk: Callable[[str], None] | None = None,
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
            if on_chunk is not None:
                # What is happening (D63): the chunk as it printed, to whoever is listening.
                on_chunk(chunk.decode(errors="replace"))
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


async def run_leashed(
    argv: list[str],
    *,
    cwd: Path,
    timeout_s: float,
    output_limit: int,
    memory_mb: int | None = None,
    on_output: Callable[[str], None] | None = None,
) -> Observation:
    """Run `argv` under the rules. A failure to start, or a timeout, is a `Failed`.

    `on_output` hears each chunk of stdout or stderr as it arrives (D63) — the result is still the
    whole, capped as before; this is the live half beside it."""
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
        hold(process)  # and it dies with us, whatever ends us (D53)
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
                full = functools.partial(end_the_group, process)
                (stdout, cut_out), (stderr, cut_err) = await asyncio.gather(
                    _read_capped(process.stdout, output_limit, full, on_output),
                    _read_capped(process.stderr, output_limit, full, on_output),
                )
                await process.wait()
        except TimeoutError:
            return Failed(f"timed out after {timeout_s:g}s")
    finally:
        # Whatever happened — finished, timed out, or capped — nothing this step started is left
        # running (D35).
        end_the_group(process)
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

# ------------------------------------------------------------------ held open


@dataclass(frozen=True)
class ExitStatus:
    """How a held process ended. `None` for both is impossible — one of them always says."""

    exit_code: int | None = None
    signal: str | None = None


class HeldProcess:
    """A leashed process the caller keeps a handle on (D42).

    `run_leashed` is the shape for *run this and tell me what happened*. This is the shape a
    **terminal** needs: an agent starts something, reads what it has printed so far, waits, kills,
    and lets go. Everything the one-shot leash promises still holds — its own process group, a cap
    on output, a timeout, and a kill that takes the group rather than the leader (D35).

    The timeout runs whether or not anybody is waiting. A terminal the agent opened and wandered
    off from must not outlive the run that opened it.
    """

    def __init__(
        self, process: asyncio.subprocess.Process, *, timeout_s: float, limit: int
    ) -> None:
        self._process = process
        self._limit = limit
        self._out = bytearray()
        self._truncated = False
        self._status: ExitStatus | None = None
        self.timed_out = False
        self._readers = asyncio.gather(
            self._drain(process.stdout), self._drain(process.stderr), return_exceptions=True
        )
        self._clock = asyncio.create_task(self._stop_when_it_overruns(timeout_s))

    async def _drain(self, stream: asyncio.StreamReader | None) -> None:
        """Keep reading past the cap and throw the rest away — a child blocked on a full pipe is a
        child that never exits, which is the deadlock the one-shot leash argues about too."""
        if stream is None:
            return
        while chunk := await stream.read(4096):
            room = self._limit - len(self._out)
            if room > 0:
                self._out += chunk[:room]
            if len(chunk) > max(room, 0):
                self._truncated = True

    async def _stop_when_it_overruns(self, timeout_s: float) -> None:
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.sleep(timeout_s)
            if self._process.returncode is None:
                self.timed_out = True
                end_the_group(self._process)

    def captured(self) -> tuple[str, bool]:
        """What it has printed so far, and whether anything was cut."""
        return self._out.decode(errors="replace"), self._truncated

    @property
    def exit_status(self) -> ExitStatus | None:
        """How it ended, or `None` while it is still running."""
        return self._status

    async def output_when(self, ready: Callable[[str], bool], *, within_s: float = 10.0) -> str:
        """What it has printed, once `ready` is satisfied — for a caller that must not race the
        child's first line. A claim about the output rather than a sleep of a guessed length."""
        async with asyncio.timeout(within_s):
            while True:
                text, _ = self.captured()
                if ready(text) or self._process.returncode is not None:
                    return text
                await asyncio.sleep(0.01)

    async def wait(self) -> ExitStatus:
        """Wait for it to end, and say how."""
        if self._status is not None:
            return self._status
        code = await self._process.wait()
        self._clock.cancel()
        with contextlib.suppress(BaseException):
            await self._readers
        self._status = (
            ExitStatus(signal=signal_name(-code)) if code < 0 else ExitStatus(exit_code=code)
        )
        return self._status

    async def kill(self) -> ExitStatus:
        """End the whole group, not the leader (D35)."""
        if self._process.returncode is None:
            end_the_group(self._process)
        return await self.wait()

    async def release(self) -> None:
        """The caller is finished with the handle. A process still running is **ended**, never left
        behind: a step owns the process tree it starts (D35), and a released terminal whose program
        outlived the run is exactly the orphan that rule exists to forbid."""
        await self.kill()


def signal_name(number: int) -> str:
    with contextlib.suppress(ValueError):
        return signal.Signals(number).name
    return f"signal {number}"


async def start_leashed(
    argv: list[str],
    *,
    cwd: Path,
    timeout_s: float,
    output_limit: int,
    memory_mb: int | None = None,
) -> HeldProcess:
    """Start `argv` under the same rules as `run_leashed`, and hand back the handle."""
    environment = {name: os.environ[name] for name in KEPT_ENV if name in os.environ}
    environment["TMPDIR"] = str(cwd)
    process = await asyncio.create_subprocess_exec(
        *argv,
        cwd=cwd,
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )
    hold(process)  # dies with us, whatever ends us (D53)
    if memory_mb is not None and process.pid is not None:
        _limit_memory(process.pid, memory_mb)
    return HeldProcess(process, timeout_s=timeout_s, limit=output_limit)
