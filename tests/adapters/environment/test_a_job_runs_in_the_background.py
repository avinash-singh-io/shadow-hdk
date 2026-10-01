"""A dev server, a watcher, a long test suite — started, watched, killed (ENH-042, D157/D160).

Lane P confirmed this costs them: a developer runs a long-lived process while working, and Claude
Code and Codex both have one. A governed CLI without it is weaker than the same CLI on its own,
which is the bar they set and the right one.

**D157 is the decision that made this hard.** D35 says a step owns the process tree it starts and
nothing survives the step — `run_leashed` ends the group in a `finally` for exactly that reason. A
background job outlives its step by definition, so D35 cannot apply to it unchanged. What carries
over is the principle *nothing outlives the thing that owns it*, one level up: the **environment**
owns a job, and `close()` ends every one. That is the same move BUG-019 made for provider sessions,
and BUG-019 is what happens without it — two children found alive ten hours after their session
ended, each holding a subscription seat.

**D160:** `job_output` carries `running` and `exit_code` beside the output, so learning one thing
costs one call.

No test here sleeps for a fixed number of seconds. TD-015 closed four flakes of exactly that shape
in this suite, and the fix was to wait for the condition rather than for the clock.
"""

from __future__ import annotations

import asyncio
import os
import signal
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.environment.local import LocalEnvironment, LocalSandbox
from shadow_hdk.kernel import Completed, Refused
from shadow_hdk.runtime.environment import Isolation

pytestmark = pytest.mark.anyio

PATIENCE_S = 10.0
"""Long enough that a loaded laptop does not fail this, short enough to notice a hang. Nothing
waits for it in the happy path — every wait below ends on its condition."""


async def until(what: Any, *, patience: float = PATIENCE_S) -> Any:
    """Poll `what()` until it answers truthily, or give up naming what never happened."""
    deadline = asyncio.get_running_loop().time() + patience
    while asyncio.get_running_loop().time() < deadline:
        answer = await what()
        if answer:
            return answer
        await asyncio.sleep(0.02)
    raise AssertionError(f"waited {patience:g}s and it never happened")


def told(observation: Any) -> dict[str, Any]:
    assert isinstance(observation, Completed), observation
    assert isinstance(observation.output, dict), observation.output
    return observation.output


# ------------------------------------------------------------------ it starts and reports


async def test_a_job_starts_and_says_it_is_running(tmp_path: Path) -> None:
    environment = await LocalEnvironment.open(tmp_path, mode="full")
    try:
        started = told(await environment.invoke("run_background", {"command": "sleep 30"}))
        assert started["job"], started

        status = told(await environment.invoke("job_output", {"job": started["job"]}))
        assert status["running"] is True, status
        assert status["exit_code"] is None, "unknown, not zero, while it runs"
    finally:
        await environment.close()


async def test_output_arrives_while_the_job_still_runs(tmp_path: Path) -> None:
    """The point of a background job: reading what it has said so far without waiting for it."""
    environment = await LocalEnvironment.open(tmp_path, mode="full")
    try:
        started = told(
            await environment.invoke("run_background", {"command": "echo first; sleep 30"})
        )
        job = started["job"]

        async def said() -> Any:
            status = told(await environment.invoke("job_output", {"job": job}))
            return status if "first" in str(status.get("output", "")) else None

        status = await until(said)
        assert status["running"] is True, "and it has not finished"
    finally:
        await environment.close()


async def test_a_finished_job_reports_its_exit_code(tmp_path: Path) -> None:
    environment = await LocalEnvironment.open(tmp_path, mode="full")
    try:
        started = told(await environment.invoke("run_background", {"command": "exit 3"}))
        job = started["job"]

        async def done() -> Any:
            status = told(await environment.invoke("job_output", {"job": job}))
            return status if status["running"] is False else None

        status = await until(done)
        assert status["exit_code"] == 3, status
    finally:
        await environment.close()


async def test_output_is_what_is_new_since_the_last_read(tmp_path: Path) -> None:
    """D160's other half. A poll that re-read the whole buffer would bill the product for the same
    bytes on every poll, which is the cost they would actually feel."""
    environment = await LocalEnvironment.open(tmp_path, mode="full")
    try:
        started = told(
            await environment.invoke("run_background", {"command": "echo once; sleep 30"})
        )
        job = started["job"]

        async def said() -> Any:
            status = told(await environment.invoke("job_output", {"job": job}))
            return status if "once" in str(status.get("output", "")) else None

        await until(said)
        again = told(await environment.invoke("job_output", {"job": job}))
        assert "once" not in str(again["output"]), "already read; not billed for twice"
    finally:
        await environment.close()


# ------------------------------------------------------------------ and it can be killed


async def test_a_job_is_killed_and_says_so(tmp_path: Path) -> None:
    environment = await LocalEnvironment.open(tmp_path, mode="full")
    try:
        started = told(await environment.invoke("run_background", {"command": "sleep 30"}))
        job = started["job"]

        killed = told(await environment.invoke("kill_job", {"job": job}))
        assert killed["killed"] is True, killed

        async def gone() -> Any:
            status = told(await environment.invoke("job_output", {"job": job}))
            return status if status["running"] is False else None

        await until(gone)
    finally:
        await environment.close()


async def test_a_job_nobody_started_is_refused_by_name(tmp_path: Path) -> None:
    environment = await LocalEnvironment.open(tmp_path, mode="full")
    try:
        for what in ("job_output", "kill_job"):
            answer = await environment.invoke(what, {"job": "not-a-job"})
            assert isinstance(answer, Refused), (what, answer)
            assert "not-a-job" in answer.reason, answer.reason
    finally:
        await environment.close()


async def test_a_background_job_is_withheld_in_a_read_only_environment(tmp_path: Path) -> None:
    environment = await LocalEnvironment.open(tmp_path, mode="read-only")
    try:
        answer = await environment.invoke("run_background", {"command": "sleep 30"})
        assert isinstance(answer, Refused), answer
    finally:
        await environment.close()


# ------------------------------------------------------------------ and nothing outlives the owner


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


async def test_no_job_outlives_the_environment_that_owns_it(tmp_path: Path) -> None:
    """D157, measured against the operating system rather than against the kit's own bookkeeping.

    BUG-019 is why: two `claude -p` children were found alive **ten hours** after their sessions
    ended, and every existing test had been happy. A kit that only asks itself whether it cleaned
    up is the kit that found that bug in production.
    """
    environment = await LocalEnvironment.open(tmp_path, mode="full")
    started = told(await environment.invoke("run_background", {"command": "sleep 300"}))
    pid = started["pid"]
    assert isinstance(pid, int) and _alive(pid), started

    await environment.close()

    async def reaped() -> bool:
        return not _alive(pid)

    await until(reaped)


async def test_closing_ends_every_job_not_just_the_last(tmp_path: Path) -> None:
    environment = await LocalEnvironment.open(tmp_path, mode="full")
    pids = []
    for _ in range(3):
        started = told(await environment.invoke("run_background", {"command": "sleep 300"}))
        pids.append(started["pid"])
    assert all(_alive(pid) for pid in pids), pids

    await environment.close()

    async def all_reaped() -> bool:
        return not any(_alive(pid) for pid in pids)

    await until(all_reaped)


async def test_the_whole_tree_goes_not_only_the_shell(tmp_path: Path) -> None:
    """A shell that started a child is the ordinary case — `npm run dev` is a shell and a node.
    D35's session-leader hold is what makes the group end at once; this checks it still does."""
    marker = tmp_path / "child.pid"
    environment = await LocalEnvironment.open(tmp_path, mode="full")
    # `_background` already runs this through `/bin/sh -c`, so the backgrounding is the
    # command's own — a shell that starts a child and waits, which is what `npm run dev` is.
    started = told(
        await environment.invoke(
            "run_background", {"command": f"sleep 300 & echo $! > {marker}; wait"}
        )
    )
    assert started["job"]

    async def wrote_its_pid() -> Any:
        if not marker.exists():
            return None
        return marker.read_text().strip() or None

    child = int(await until(wrote_its_pid))
    assert _alive(child), "the grandchild is running"

    await environment.close()

    async def reaped() -> bool:
        return not _alive(child)

    await until(reaped)


async def test_signal_handling_is_not_left_to_chance(tmp_path: Path) -> None:
    """A sanity check on the helper this file leans on: `_alive` must actually be able to say no,
    or every assertion above passes for the wrong reason (BUG-007's shape)."""
    process = await asyncio.create_subprocess_exec("sleep", "30")
    assert process.pid is not None and _alive(process.pid)
    process.send_signal(signal.SIGKILL)
    await process.wait()

    async def reaped() -> bool:
        return not _alive(process.pid)

    await until(reaped)


# ------------------------------------------------------------------ and it is confined like any


async def test_a_background_job_goes_through_the_same_box_as_a_foreground_command(
    tmp_path: Path,
) -> None:
    """Found by a mutation, not by design: removing the sandbox wrap from `_start_job` broke no
    test, so the claim that a job is confined was a docstring and nothing more.

    A job that escaped confinement **by being long-lived** would be a hole opened by nothing but a
    lifetime — the widest kind of hole, because no mode ever admitted it and no rule names it.
    """
    wrapped: list[list[str]] = []

    class Recording(LocalSandbox):
        def wrap(self, argv: list[str], *, root: Any, mode: Any) -> list[str]:
            wrapped.append(list(argv))
            return argv

    # Constructed rather than opened: `open` proves and picks a box itself, and what this test is
    # about is whether `_start_job` *uses* the one it was given.
    box = Recording(name="seatbelt", binary="/usr/bin/sandbox-exec")
    environment = LocalEnvironment(
        tmp_path,
        mode="workspace-write",
        isolation=Isolation(
            writes_confined=True,
            reads_confined=True,
            network_denied=True,
            proven=True,
            secrets_denied=True,
            mechanism="recording",
        ),
        box=box,
    )
    try:
        wrapped.clear()
        await environment.invoke("run_background", {"command": "sleep 30"})

        assert wrapped, "the job was started without going through the box"
        assert any("sleep 30" in " ".join(argv) for argv in wrapped), wrapped
    finally:
        await environment.close()


async def test_a_background_job_is_given_no_wider_an_environment_than_a_command(
    tmp_path: Path,
) -> None:
    """The other half of the same hole: a job with the whole ambient environment while the
    foreground command beside it gets only `KEPT_ENV` would leak credentials by lifetime alone."""
    from shadow_hdk.runtime.leash import KEPT_ENV

    environment = await LocalEnvironment.open(tmp_path, mode="full")
    try:
        started = told(
            await environment.invoke("run_background", {"command": "env > seen.txt; sleep 30"})
        )
        assert started["job"]

        async def wrote() -> Any:
            seen = tmp_path / "seen.txt"
            return seen.read_text() if seen.exists() and seen.read_text() else None

        names = {line.split("=", 1)[0] for line in (await until(wrote)).splitlines() if "=" in line}
    finally:
        await environment.close()

    allowed = set(KEPT_ENV) | {"TMPDIR", "PWD", "SHLVL", "_"}
    assert names <= allowed, f"a job was handed more than a command is: {sorted(names - allowed)}"
