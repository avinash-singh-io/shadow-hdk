"""A turn is given up for the provider's **silence**, not for taking long (D182, phase 65, BUG-233).

`DEFAULT_TIMEOUT_S = 600.0` wrapped the whole wait in one `asyncio.timeout`, and on expiry the turn
came back `failed=True` saying *the provider did not finish within 600s*. Two things were wrong with
that, and lane P hit both.

**A ceiling on total turn time is the wrong cut.** The work products now hand these CLIs runs
past ten minutes, and a turn is not a failure for being long. What a ceiling is actually for is a
hung process, and a hang is *silence* — so the ceiling applies to the gap between frames. A CLI
that keeps streaming thinking, tool calls and text is working, however long it takes.

**And the clock counted time waiting for a human being.** When the CLI calls a tool, the kit
routes it through the run, and the policy may put it to the person and wait (D58). The CLI is silent
for all of that because it is waiting for *us*. Charging that to the provider's patience is both the
wrong cut and a wrong diagnosis — *the provider did not finish* about a person yet to answer.

Driven against a fake CLI over a real pipe, like its neighbours: the thing under test is a timeout
on a pipe, and a double for the pipe would test nothing.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.jsonl.session import DEFAULT_SILENCE_S, JsonlSession
from shadow_hdk.kernel import Dialect, Provider
from shadow_hdk.kernel.providers import Behaviour

pytestmark = pytest.mark.anyio

DIALECT = Dialect(
    resident=True,
    prompt_shape="stream-json-user",
    say_on=("assistant",),
    say_at="message.content[].text",
    done_on=("result",),
    done_at="result",
    failed_at="is_error",
)


def a_provider() -> Provider:
    return Provider(id="fake", kind="agent", bin="fake-cli", transport="jsonl", dialect=DIALECT)


def _said(text: str) -> dict[str, Any]:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _done(text: str) -> dict[str, Any]:
    return {"type": "result", "subtype": "success", "result": text, "is_error": False}


def a_cli_that(where: Path, script: list[tuple[float, dict[str, Any]]], name: str) -> Path:
    """A CLI that sleeps, prints, sleeps, prints — so the *gaps* are what the test controls."""
    body = "\n".join(
        f"time.sleep({pause})\nprint({json.dumps(json.dumps(line))}, flush=True)"
        for pause, line in script
    )
    made = where / name
    made.write_text(
        "#!/usr/bin/env python3\nimport sys, time\nsys.stdin.readline()\n" + body + "\n",
        encoding="utf-8",
    )
    made.chmod(0o755)
    return made


def a_session(cli: Path, root: Path | None, **kw: Any) -> JsonlSession:
    return JsonlSession(
        a_provider(), binary=cli, env={"PATH": "/usr/bin:/bin"}, workspace=root, **kw
    )


# ------------------------------------------------------------------ the ceiling is silence


async def test_a_turn_longer_than_the_ceiling_still_finishes_while_it_keeps_talking(
    tmp_path: Path,
) -> None:
    """The heart of BUG-233. Twenty-five gaps of 0.1s under a ceiling of 1.0s is a turn of ~2.5s —
    which the old total-time ceiling would have failed and a silence ceiling must not.

    **Many small gaps rather than a few large ones**, so the margin is one load cannot eat: failing
    needs a single `readline` to stall for 0.9s, where an earlier version needed only 0.5s and did
    stall that long in a full-suite run.

    **The first frame is printed with no sleep at all**, and that is load-bearing rather than
    tidiness: the first `readline` waits for a Python interpreter to boot as well as for the
    script's first sleep, and that boot is unbounded under load. An earlier version put a 0.3s
    sleep before the first frame with a 0.8s ceiling and **failed in a full-suite run** while
    passing alone — precisely the TD-015/TD-018 flake class, and in a test whose own docstring
    warned about it. Printing immediately lets the deadline rearm once startup is over, so every
    gap this test actually measures is a clean sleep.

    Fixed by removing the timing dependence, not by widening the margin and re-running until green
    — re-running until green is the behaviour that class rewards."""
    cli = a_cli_that(
        tmp_path,
        [(0.0, _said("ready"))]  # absorbs interpreter startup; see above
        + [(0.1, _said(f"still going {n}")) for n in range(24)]
        + [(0.1, _done("ok"))],
        "talkative",
    )
    session = a_session(cli, tmp_path, silence_s=1.0)
    try:
        done = await session.turn("go")
    finally:
        await session.close()

    assert not done.failed, (
        f"a turn of ~2.5s was given up on under a 1.0s *silence* ceiling, so the deadline is not "
        f"being rearmed per frame: {done.text!r}"
    )
    assert done.text == "ok", done.text


async def test_a_provider_that_goes_quiet_for_longer_than_the_ceiling_fails(tmp_path: Path) -> None:
    """Paired, so the test above cannot pass because nothing is enforced at all. A hang is what the
    ceiling is actually for, and it must still be caught."""
    cli = a_cli_that(tmp_path, [(0.2, _said("one")), (1.2, _done("never read"))], "hangs")
    session = a_session(cli, tmp_path, silence_s=0.4)
    try:
        done = await session.turn("go")
    finally:
        await session.close()

    assert done.failed, done.text


async def test_the_failure_says_it_was_silence_rather_than_slowness(tmp_path: Path) -> None:
    """*The provider did not finish within 600s* was a diagnosis a product acted on, and it named
    the wrong thing. The words have to say what was actually measured."""
    cli = a_cli_that(tmp_path, [(1.2, _done("never read"))], "mute")
    session = a_session(cli, tmp_path, silence_s=0.3)
    try:
        done = await session.turn("go")
    finally:
        await session.close()

    assert done.failed
    assert "said nothing" in done.text, done.text
    assert "0.3" in done.text, f"it must name the ceiling it applied: {done.text!r}"


# ------------------------------------------------------------------ and a mode may set it


async def test_a_mode_may_set_the_ceiling(tmp_path: Path) -> None:
    """Unconfigurable was half of BUG-233. It travels on the behaviour, like `tools_offered`: a
    field the kit honours itself rather than one the CLI is handed."""
    cli = a_cli_that(tmp_path, [(0.5, _done("patience paid off"))], "slow")
    session = a_session(cli, tmp_path, behaviour=Behaviour(silence_seconds=5.0), silence_s=0.1)
    try:
        done = await session.turn("go")
    finally:
        await session.close()

    assert not done.failed, done.text
    assert done.text == "patience paid off"


async def test_a_mode_setting_nothing_gets_the_default(tmp_path: Path) -> None:
    cli = a_cli_that(tmp_path, [(0.01, _done("fine"))], "quick")
    session = a_session(cli, tmp_path, behaviour=Behaviour())
    try:
        done = await session.turn("go")
    finally:
        await session.close()

    assert not done.failed
    assert session.silence_s == DEFAULT_SILENCE_S


def test_the_default_is_not_ten_minutes_and_says_what_it_measures() -> None:
    """600 seconds of *total turn time* was the cliff. 600 seconds of *silence* would be a
    different number meaning a different thing, and leaving it unchanged would invite the reader to
    assume nothing had."""
    assert DEFAULT_SILENCE_S > 600.0, DEFAULT_SILENCE_S


# ------------------------------------------------------------------ and a person is not counted


async def test_time_spent_answering_the_providers_own_call_is_given_back(tmp_path: Path) -> None:
    """The second half of BUG-233. While the kit answers a tool call — routing it through the run,
    and perhaps putting it to a person and waiting — the CLI is silent because it is waiting for
    *us*. That is not the provider's silence, and the ceiling gives it back.

    Asserted at the seam rather than through a whole governed turn: the property is arithmetic on a
    deadline, and a test that stood up an approving host would prove the plumbing rather than this.
    """
    cli = a_cli_that(tmp_path, [(1.0, _done("after the person answered"))], "waits")
    session = a_session(cli, tmp_path, silence_s=0.4)
    try:
        turn = asyncio.ensure_future(session.turn("go"))
        # The person took longer than the ceiling, while the CLI waited for the answer.
        await asyncio.sleep(0.1)
        session.waited_for_us(3.0)
        done = await turn
    finally:
        await session.close()

    assert not done.failed, done.text
    assert done.text == "after the person answered"


async def test_giving_back_time_before_a_turn_runs_is_harmless(tmp_path: Path) -> None:
    """A call answered between turns, or a host that reports one late, must not raise."""
    cli = a_cli_that(tmp_path, [(0.01, _done("fine"))], "quick2")
    session = a_session(cli, tmp_path)

    session.waited_for_us(1.0)  # no turn is running

    try:
        done = await session.turn("go")
    finally:
        await session.close()

    assert not done.failed


# ------------------------------------- and the mechanism itself, with no clock to race


async def test_the_deadline_moves_when_time_is_given_back() -> None:
    """The arithmetic, with no process and no sleeping — so it cannot flake.

    The tests above measure the *effect* through a real pipe, which is where a timeout on a pipe
    belongs. But their margins are wall-clock, and a wall-clock margin is something a loaded machine
    can eat: one of them did fail in a full-suite run while passing alone, which is the
    TD-015/TD-018 class. So the mechanism gets a proof with no clock in it at all, and the
    behavioural tests keep their job of showing it works end to end.
    """
    session = a_session(Path("/nonexistent"), None)

    async with asyncio.timeout(10.0) as deadline:
        session._deadline = deadline  # noqa: SLF001 — the deadline *is* the mechanism under test
        before = deadline.when()
        session.waited_for_us(100.0)
        after = deadline.when()

    assert before is not None and after is not None
    assert after > before + 50, f"the deadline did not move: {before} -> {after}"


async def test_giving_back_nothing_moves_nothing() -> None:
    """Zero and negative are no-ops rather than a deadline pulled *in*: a host reporting a call that
    took no measurable time must not shorten the provider's patience."""
    session = a_session(Path("/nonexistent"), None)

    async with asyncio.timeout(10.0) as deadline:
        session._deadline = deadline  # noqa: SLF001
        before = deadline.when()
        session.waited_for_us(0.0)
        session.waited_for_us(-5.0)
        after = deadline.when()

    assert before == after, f"{before} -> {after}"
