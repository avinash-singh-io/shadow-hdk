"""A process held open across calls, and still on the leash (D42).

`run_leashed` runs a program to completion and hands back an observation. A **terminal** is the
other shape: an agent starts something, reads what it has printed so far, waits for it, kills it,
lets it go. The ACP client contract has exactly those five doors, and until one of them is answered
an agent asked to run code either cannot, or runs it somewhere nothing can see.

It lives here rather than in the adapter that needs it for the reason Phase 11 moved the leash here
and Phase 16 moved the device contract: **the second protocol adapter must not have to import the
first**. A held process is a runtime facility, and rule 4 stays green because of where it sits.

Everything the one-shot leash promises still holds — its own process group, a cap on what it can
print, a timeout, and a kill that takes the group rather than the leader.
"""

from __future__ import annotations

import sys
from pathlib import Path

from shadow_hdk.runtime.leash import start_leashed

PRINTS_THEN_WAITS = "import sys, time; print('hello', flush=True); time.sleep(30)"


async def test_a_held_process_prints_and_stays_up(tmp_path: Path) -> None:
    held = await start_leashed(
        [sys.executable, "-c", PRINTS_THEN_WAITS], cwd=tmp_path, timeout_s=30, output_limit=64_000
    )
    try:
        assert "hello" in await held.output_when(lambda text: "hello" in text)
        assert held.exit_status is None, "it reported an exit while it was still running"
    finally:
        await held.kill()


async def test_waiting_gives_the_exit_code(tmp_path: Path) -> None:
    held = await start_leashed(
        [sys.executable, "-c", "raise SystemExit(3)"],
        cwd=tmp_path,
        timeout_s=30,
        output_limit=64_000,
    )

    status = await held.wait()

    assert status.exit_code == 3
    assert status.signal is None


async def test_killing_ends_it(tmp_path: Path) -> None:
    held = await start_leashed(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        cwd=tmp_path,
        timeout_s=60,
        output_limit=64_000,
    )

    await held.kill()
    status = await held.wait()

    assert status.exit_code != 0 or status.signal is not None


async def test_what_it_printed_is_capped_and_says_so(tmp_path: Path) -> None:
    """An agent reasoning from half an answer while believing it whole is the worse failure — the
    same argument the one-shot leash makes, and the flag is why."""
    held = await start_leashed(
        [sys.executable, "-c", "print('x' * 50_000)"], cwd=tmp_path, timeout_s=30, output_limit=200
    )
    await held.wait()

    text, truncated = held.captured()

    assert len(text) <= 200
    assert truncated is True


async def test_a_held_process_that_overruns_is_ended_by_its_timeout(tmp_path: Path) -> None:
    """The leash is a leash whether the caller waits or wanders off. A terminal an agent forgot
    about must not outlive the run that opened it."""
    held = await start_leashed(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        cwd=tmp_path,
        timeout_s=0.5,
        output_limit=64_000,
    )

    status = await held.wait()

    assert status.exit_code != 0 or status.signal is not None
    assert held.timed_out is True


async def test_releasing_lets_it_go(tmp_path: Path) -> None:
    """Release is the caller saying it is finished with the handle. A process still running at that
    point is ended rather than left behind — D35: a step owns the process tree it starts."""
    held = await start_leashed(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        cwd=tmp_path,
        timeout_s=60,
        output_limit=64_000,
    )

    await held.release()

    assert held.exit_status is not None, "release left a process running"
