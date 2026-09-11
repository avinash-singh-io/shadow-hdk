"""A provider's child does not outlive the process that opened it, whatever ended it (BUG-019, D53).

Two `claude -p` children were found alive ten hours after their sessions ended, each holding a
subscription seat. `close()` ends the group — when it is reached. A person leaving a REPL with
Ctrl-C, a `sys.exit`, a `SIGTERM` from a supervisor: none of those promise to reach it. So the
runtime keeps every session leader it starts in one place and ends them all when the interpreter
goes, by whichever door. Proven in a subprocess, because the claim is about a process ending.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time

import pytest

ENDINGS: dict[str, tuple[str, int | None]] = {
    # how the host ends, and the exit status the thing that ran it must still see
    "keyboard-interrupt": ("raise KeyboardInterrupt", None),
    "sys-exit": ("sys.exit(0)", 0),
    "sigterm": ("os.kill(os.getpid(), signal.SIGTERM); time.sleep(5)", -15),
    "unhandled-error": ("raise RuntimeError('the host blew up')", 1),
    # A host with its own SIGTERM handler keeps it: ours is installed only over the default. The
    # host's handler exits 7 and that is the status seen — and `atexit` still ends the child.
    "sigterm-with-the-hosts-own-handler": (
        "os.kill(os.getpid(), signal.SIGTERM); time.sleep(5)",
        7,
    ),
}

HOSTS_OWN_HANDLER = "signal.signal(signal.SIGTERM, lambda *_: sys.exit(7))"

HOST = textwrap.dedent(
    """
    import asyncio, os, signal, sys, time
    from shadow_hdk.runtime.processes import hold

    async def main():
        {before}
        # No pipes: a child holding the host's captured stdout would keep the test's
        # `subprocess.run` waiting for EOF, which is a stopwatch and not the claim.
        null = asyncio.subprocess.DEVNULL
        child = await asyncio.create_subprocess_exec(
            "sleep", "300", start_new_session=True, stdin=null, stdout=null, stderr=null
        )
        hold(child)
        print(child.pid, flush=True)
        {ending}

    asyncio.run(main())
    """
)


def still_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # A zombie answers kill(0); a reaped or never-there pid does not. `sleep` is in its own session
    # and nobody waits for it, so a killed sleep is an actual absence within a moment.
    return True


def gone_within(pid: int, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not still_alive(pid):
            return True
        time.sleep(0.05)
    return not still_alive(pid)


@pytest.mark.parametrize("ending", sorted(ENDINGS))
def test_the_child_is_gone_however_the_host_ended(ending: str) -> None:
    line, status = ENDINGS[ending]
    before = HOSTS_OWN_HANDLER if "hosts-own" in ending else ""
    finished = subprocess.run(
        [sys.executable, "-c", HOST.format(ending=line, before=before)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    pid = int(finished.stdout.strip().splitlines()[0])
    try:
        assert gone_within(pid, 3.0), f"sleep {pid} outlived a host that ended by {ending}"
    finally:
        if still_alive(pid):
            os.kill(pid, 9)
    # Ending the children must not change how the host is seen to have ended: a supervisor that
    # sent SIGTERM sees death by SIGTERM, not a clean exit that swallowed its signal.
    if status is None:
        assert finished.returncode != 0
    else:
        assert finished.returncode == status, finished.stderr[-400:]


def test_a_child_let_go_of_is_not_ended() -> None:
    """`end_the_group` is the ordinary ending and lets go; a child the caller has already ended and
    reaped must not have its pid killed again — by then the pid may be somebody else's."""
    from shadow_hdk.runtime.processes import held_now, hold, let_go

    class Fake:
        pid = 4242

    hold(Fake())  # type: ignore[arg-type]
    assert 4242 in held_now()
    let_go(Fake())  # type: ignore[arg-type]
    assert 4242 not in held_now()


@pytest.mark.anyio
async def test_what_the_leash_starts_is_held_until_it_ends(tmp_path: object) -> None:
    """The registry only helps if every spawn site uses it. The leash is the runtime's own site;
    the adapters' sites are covered by their honesty tests importing the same `hold`."""
    from pathlib import Path

    from shadow_hdk.runtime.leash import start_leashed
    from shadow_hdk.runtime.processes import held_now

    held = await start_leashed(
        ["sleep", "30"], cwd=Path(str(tmp_path)), timeout_s=10, output_limit=1024
    )
    pid = held._process.pid  # noqa: SLF001 — the pid is the claim
    assert pid in held_now()
    await held.kill()
    assert pid not in held_now(), "a pid ended by the leash stayed held; at exit it could be reused"
