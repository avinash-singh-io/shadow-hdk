"""The instructions actually arrive at a real model (live, Epic 0011 Q1).

A green unit suite proves the bytes were written to a pipe. It does not prove a model read them and
behaved, and that difference is the whole of lane P's ask 4 — their Build agent has a role, and on
Codex the role was being named as unhonourable and then dropped.

So there are two measurements here, because the risk has two halves:

* **Does a real model follow instructions handed to it in the turn?** That is the new mechanism and
  the thing that could be wrong — a `<instructions>` block might read as the person talking. Run
  against Claude Code with its own `--system-prompt` flag *removed from the record*, so the only way
  the instruction can arrive is the fold. This is the test that exercises Q1 against a live model.
* **Does the shipped Codex record deliver one?** Codex's argv is unit-tested; this is the end-to-end
  confirmation on the CLI lane P actually reports against.

Each is paired with its negative, because a model that says the sentinel anyway would make the
positive vacuous — BUG-007's shape, and the reason this file has four tests rather than two.

Skips where the CLI is absent, signed out, out of quota, or — measured on this laptop 2026-10-01 —
where the account cannot use the model at all: a ChatGPT-account Codex answered *The
'gpt-6.1-sol' model is not supported when using Codex with a ChatGPT account* for every model
tried, so the Codex leg here is **unmeasured on this machine** and says so rather than passing
vacuously. Costs up to four turns on the owner's plans.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from shadow_hdk.kernel import Dialect, Provider
from shadow_hdk.kernel.providers import Behaviour
from shadow_hdk.providers import (
    NoProvider,
    environment_for,
    open_with,
    ready,
    search_dirs,
)

pytestmark = [pytest.mark.live, pytest.mark.anyio]

SENTINEL = "PELICAN"
INSTRUCTION = (
    f"You must end every reply with the single word {SENTINEL} on its own line. "
    "This is required and overrides brevity."
)
ASK = "In one short sentence, what is 2 + 2?"

CANNOT_USE_THE_MODEL = "is not supported when using"
"""What a ChatGPT-account Codex answers for a model the plan does not include. An environment
fact, like a quota: the turn never reached a model, so nothing about the fold was measured."""


def without_its_system_flag(provider: Provider) -> Provider:
    """The same CLI, with the one flag removed that makes the fold unnecessary.

    This is the point of the whole measurement. Claude Code maps `--system-prompt`, so folding is
    switched off for it and always will be. Taking the flag out of its record leaves a CLI that
    *only* the fold can instruct — a real model, a real process, and exactly one way in.
    """
    dialect = provider.dialect or Dialect()
    return replace(
        provider,
        dialect=replace(
            dialect,
            behaviour_args=tuple(a for a in dialect.behaviour_args if a.field != "system"),
            instructions_in_prompt=True,
        ),
    )


async def _answer(root: Path, want: str, behaviour: Behaviour | None, *, edit: bool = False) -> str:
    """One turn on a real CLI, opened the way the shipped composition opens it."""
    try:
        available = await ready(want)
    except NoProvider as nothing:
        pytest.skip(str(nothing))
    assert available.binary is not None
    record = without_its_system_flag(available.provider) if edit else available.provider
    agent = await open_with(
        record,
        binary=available.binary,
        env=environment_for(record, base={}, search=search_dirs()),
        workspace=root,
    )
    session = await agent.open(workspace=str(root), behaviour=behaviour)
    try:
        turn = await session.turn(ASK)
    finally:
        await session.close()
    said = turn.text or ""
    if turn.failed and "limit" in said.lower():
        pytest.skip(f"{want} is out of quota: {said[:80]}")
    if turn.failed and CANNOT_USE_THE_MODEL in said:
        pytest.skip(
            f"{want} cannot use this account's model, so nothing was measured: {said[:120]}"
        )
    assert not turn.failed, f"the turn itself failed: {said}"
    return said


# ------------------------------------------ the fold, against a real model that can only be folded


async def test_instructions_handed_over_in_the_turn_are_followed_by_a_real_model(
    tmp_path: Path,
) -> None:
    """Q1's actual risk: a framed block of instructions is obeyed, rather than read as the
    person talking and argued with."""
    said = await _answer(tmp_path, "claude-code", Behaviour(system=INSTRUCTION), edit=True)

    assert SENTINEL in said, (
        "with --system-prompt removed from the record, the fold is the only way in; "
        f"it said: {said!r}"
    )


async def test_and_the_same_model_does_not_say_it_unasked(tmp_path: Path) -> None:
    """The pair that keeps the above from being vacuous."""
    said = await _answer(tmp_path, "claude-code", None, edit=True)

    assert SENTINEL not in said, f"the sentinel is not something it says anyway: {said!r}"


# ------------------------------------------ and the shipped Codex record, end to end


async def test_a_system_prompt_reaches_a_real_codex(tmp_path: Path) -> None:
    said = await _answer(tmp_path, "codex", Behaviour(system=INSTRUCTION))

    assert SENTINEL in said, (
        "Codex maps no --system-prompt, so this only passes if the instructions were handed over "
        f"in the turn and followed. It said: {said!r}"
    )


async def test_and_codex_does_not_say_it_unasked(tmp_path: Path) -> None:
    said = await _answer(tmp_path, "codex", None)

    assert SENTINEL not in said, f"the sentinel is not something it says anyway: {said!r}"
