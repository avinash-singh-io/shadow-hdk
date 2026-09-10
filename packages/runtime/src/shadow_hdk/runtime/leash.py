"""A leash: run a program with a timeout, a capped output, and a scrubbed environment.

Extracted from the subprocess sandbox in Phase 11, when a second sandbox needed exactly the same
three rules and the invariant that **no adapter imports another** said it could not have them by
inheritance. That invariant exists so a host can install any subset of adapters; the price is that
what two of them share has to live below both. This does.

A leash is not a boundary. It stops a runaway; it does not stop a determined program. Which sandbox
wraps it decides whether there is a box around the program at all.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from shadow_hdk.kernel.observations import Completed, Failed, Observation

KEPT_ENV = ("PATH", "LANG", "LC_ALL", "TMPDIR", "HOME")
"""The environment a leashed program sees. Everything else — every secret the host process holds —
is withheld, because a model-written script must not be able to read the operator's keys."""


def cap(raw: bytes, limit: int) -> tuple[str, bool]:
    """Decode and truncate. The flag says whether anything was cut, because an agent reasoning
    from half an answer while believing it whole is a worse failure than one told it got half."""
    text = raw.decode("utf-8", errors="replace")
    if len(text) <= limit:
        return text, False
    return text[:limit], True


async def run_leashed(
    argv: list[str], *, cwd: Path, timeout_s: float, output_limit: int
) -> Observation:
    """Run `argv` under the three rules. A failure to start, or a timeout, is a `Failed`."""
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=cwd,
            env={name: os.environ[name] for name in KEPT_ENV if name in os.environ},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as broken:
        return Failed(f"{type(broken).__name__}: {broken}")
    try:
        out, err = await asyncio.wait_for(process.communicate(), timeout_s)
    except TimeoutError:
        process.kill()
        await process.wait()
        return Failed(f"timed out after {timeout_s:g}s")
    stdout, cut_out = cap(out, output_limit)
    stderr, cut_err = cap(err, output_limit)
    return Completed(
        {
            "exit_code": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "truncated": cut_out or cut_err,
        }
    )


__all__ = ["KEPT_ENV", "cap", "run_leashed"]
