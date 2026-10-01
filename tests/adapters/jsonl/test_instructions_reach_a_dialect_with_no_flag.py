"""A CLI with no system-prompt flag is still told who to be (Epic 0011 Q1, lane P's ask 4).

`codex exec` maps no `--system-prompt`. Until now that meant a product's instructions reached
Claude Code and **not** Codex: `Behaviour.system` was named on `thread.unmapped_behaviour` — honest,
never silent — and then dropped. A product whose Build agent has a role therefore had no role on
Codex, and the kit told it so in a field nobody was reading.

The other half of D64: a dialect that maps no flag can still take instructions **in the turn**, so
the fold is a fact about that CLI and lives in its record. Framed rather than prefixed unmarked, so
the model can tell a mode's instructions from a person's words; first turn only, because a session
carries them after that — a resident CLI in its own memory, a non-resident one through its resume.

The framing is a named, attributable `<context>` fragment (D166, phase 62) — Q1 shipped a bare
`<instructions>` block and phase 62 generalised it, which was the plan recorded at the time.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.adapters.jsonl.session import JsonlSession
from shadow_hdk.adapters.jsonl.transport import JsonlProvider
from shadow_hdk.kernel import Dialect, Provider
from shadow_hdk.kernel.providers import Behaviour, BehaviourArg, Fragment, unmapped_behaviour
from shadow_hdk.providers import shipped

pytestmark = pytest.mark.anyio


HEARD = "heard-stdin.txt"

# A dialect shaped like Codex's: no behaviour flag for `system`, and it takes them in the turn.
FOLDS = Dialect(
    resident=False,
    prompt_shape="text",
    instructions_in_prompt=True,
    done_on=("turn.completed",),
    say_on=("agent_message",),
    say_at="text",
)

# The same CLI that has not said it can take them: the conservative default.
DOES_NOT_FOLD = Dialect(
    resident=False,
    prompt_shape="text",
    done_on=("turn.completed",),
    say_on=("agent_message",),
    say_at="text",
)


def a_cli_that_records_what_it_heard(where: Path) -> Path:
    """A fake CLI that writes its stdin beside itself, then completes a turn."""
    made = where / "fake-cli"
    made.write_text(
        "#!/usr/bin/env python3\n"
        "import sys, json, pathlib\n"
        f"pathlib.Path({str(where / HEARD)!r}).write_text(sys.stdin.read())\n"
        'print(json.dumps({"type": "agent_message", "text": "ok"}), flush=True)\n'
        'print(json.dumps({"type": "turn.completed"}), flush=True)\n',
        encoding="utf-8",
    )
    made.chmod(0o755)
    return made


def a_provider(dialect: Dialect) -> Provider:
    return Provider(id="fake-cli", kind="agent", bin="fake-cli", transport="jsonl", dialect=dialect)


def heard(where: Path) -> str:
    return (where / HEARD).read_text(encoding="utf-8")


async def _one_turn(
    where: Path, dialect: Dialect, behaviour: Behaviour | None, prompt: str
) -> None:
    session = JsonlSession(
        a_provider(dialect),
        binary=a_cli_that_records_what_it_heard(where),
        env={"PATH": "/usr/bin:/bin"},
        workspace=where,
        behaviour=behaviour,
    )
    try:
        await session.turn(prompt)
    finally:
        await session.close()


# ------------------------------------------------------------------ the fold happens


async def test_a_dialect_with_no_system_flag_is_handed_the_instructions_in_the_turn(
    tmp_path: Path,
) -> None:
    await _one_turn(tmp_path, FOLDS, Behaviour(system="be brief"), "how many lines?")

    told = heard(tmp_path)
    assert "be brief" in told, "the instructions reached the CLI at all"
    assert "how many lines?" in told, "and so did the person's words"


async def test_the_instructions_are_framed_rather_than_prefixed_unmarked(tmp_path: Path) -> None:
    """An unmarked prefix reads to a model as the person talking. The block says what it is."""
    await _one_turn(tmp_path, FOLDS, Behaviour(system="be brief"), "how many lines?")

    told = heard(tmp_path)
    # Phase 62 replaced Q1's bare `<instructions>` with a named, attributable fragment (D166) —
    # planned here from the start, and this is that replacement pinned.
    assert '<context name="instructions" source="the mode">\nbe brief\n</context>' in told
    assert told.index("</context>") < told.index("how many lines?"), "context first"


async def test_append_system_travels_too_and_in_the_behaviours_order(tmp_path: Path) -> None:
    await _one_turn(tmp_path, FOLDS, Behaviour(system="be brief", append_system="cite files"), "go")

    told = heard(tmp_path)
    assert "be brief" in told and "cite files" in told
    assert told.index("be brief") < told.index("cite files")


async def test_only_the_first_turn_carries_them(tmp_path: Path) -> None:
    """A session carries them after that — a resident CLI in its memory, a non-resident one
    through its resume. Repeating them every turn would be paid for on every turn."""
    session = JsonlSession(
        a_provider(FOLDS),
        binary=a_cli_that_records_what_it_heard(tmp_path),
        env={"PATH": "/usr/bin:/bin"},
        workspace=tmp_path,
        behaviour=Behaviour(system="be brief"),
    )
    try:
        await session.turn("first")
        assert "be brief" in heard(tmp_path), "the first turn was told"
        await session.turn("second")
        second = heard(tmp_path)
    finally:
        await session.close()

    assert "second" in second, "the second turn happened"
    assert "be brief" not in second, "and was not told again"


# ------------------------------------------------------------------ and does not, when it must not


async def test_a_dialect_that_has_not_said_so_folds_nothing(tmp_path: Path) -> None:
    """The conservative default this file's own rule demands: a CLI nobody measured is not
    handed a prompt shape somebody guessed at."""
    await _one_turn(tmp_path, DOES_NOT_FOLD, Behaviour(system="be brief"), "how many lines?")

    told = heard(tmp_path)
    assert "be brief" not in told
    assert "how many lines?" in told


async def test_a_behaviour_with_no_instructions_changes_the_prompt_not_at_all(
    tmp_path: Path,
) -> None:
    await _one_turn(tmp_path, FOLDS, Behaviour(model="o3"), "how many lines?")

    assert heard(tmp_path) == "how many lines?\n", "byte for byte the prompt it always was"


async def test_no_behaviour_at_all_changes_the_prompt_not_at_all(tmp_path: Path) -> None:
    await _one_turn(tmp_path, FOLDS, None, "how many lines?")

    assert heard(tmp_path) == "how many lines?\n"


async def test_a_cli_with_its_own_flag_is_not_told_twice(tmp_path: Path) -> None:
    """Claude Code takes `--system-prompt`. Folding as well would send the role twice and be
    paid for twice."""
    folds_and_flags = Dialect(
        resident=False,
        prompt_shape="text",
        instructions_in_prompt=True,
        behaviour_args=(BehaviourArg(field="system", flag="--system-prompt"),),
        done_on=("turn.completed",),
    )
    await _one_turn(tmp_path, folds_and_flags, Behaviour(system="be brief"), "go")

    assert "be brief" not in heard(tmp_path), "the flag delivered it; the prompt must not"


# ------------------------------------------------------------------ and stops being named unmapped


async def test_what_the_prompt_delivers_is_no_longer_named_unmapped(tmp_path: Path) -> None:
    """`unmapped_behaviour` is the host's word for *this CLI cannot do what your mode asked*.
    Once the instructions arrive, saying so would be a lie — and lane P hid controls on it."""
    provider = a_provider(FOLDS)

    named = unmapped_behaviour(provider, Behaviour(system="be brief", append_system="cite"))

    assert named == [], "delivered, so not named"


async def test_temperature_stays_unmapped_because_a_prompt_cannot_carry_it(tmp_path: Path) -> None:
    """The honest half. A sampling parameter is not something a turn's text can ask for, so a
    mode that set one on this CLI still gets told it was not honoured."""
    provider = a_provider(FOLDS)

    named = unmapped_behaviour(provider, Behaviour(system="be brief", temperature=0.2))

    assert named == ["temperature"]


async def test_a_dialect_that_folds_nothing_still_names_them(tmp_path: Path) -> None:
    provider = a_provider(DOES_NOT_FOLD)

    named = unmapped_behaviour(provider, Behaviour(system="be brief", append_system="cite"))

    assert named == ["system", "append_system"]


# ------------------------------------------------------------------ the shipped record


async def test_the_shipped_codex_record_now_delivers_a_system_prompt(tmp_path: Path) -> None:
    """The whole point of Q1: lane P's Build agent has a role on Codex."""
    provider = JsonlProvider(shipped()["codex"], binary=Path("/nonexistent/codex"), env={})

    session = await provider.open(
        workspace=str(tmp_path), behaviour=Behaviour(system="be brief", model="o3", effort="high")
    )

    assert session.unmapped == (), "nothing the mode asked for is dropped any more"


async def test_the_shipped_claude_code_record_still_uses_its_flag(tmp_path: Path) -> None:
    """It has a flag, so it must not also fold — and its `unmapped` was already empty."""
    record = shipped()["claude-code"]
    dialect = record.dialect or Dialect()

    assert dialect.instructions_in_prompt is False, "a CLI with the flag does not need the fold"
    assert "system" in {a.field for a in dialect.behaviour_args}


# ------------------------------------------------------ fragments are not instructions


async def test_a_cli_with_a_system_flag_still_receives_a_products_fragments(
    tmp_path: Path,
) -> None:
    """**Found by a live measurement, not by a unit test.** `instructions_in_prompt` and "carries
    fragments" were one gate, so Claude Code — which has `--system-prompt`, and therefore does not
    fold — received no fragments at all. Every unit test here passed, because every one used a
    dialect that folds.

    No CLI has a flag for a product's named context, so the turn is the only way in for a fragment,
    whatever the CLI does about instructions.
    """
    has_the_flag = Dialect(
        resident=False,
        prompt_shape="text",
        behaviour_args=(BehaviourArg(field="system", flag="--system-prompt"),),
        done_on=("turn.completed",),
    )
    await _one_turn(
        tmp_path,
        has_the_flag,
        Behaviour(
            system="be brief",
            fragments=(Fragment(name="house-style", text="tabs, never spaces", source="a plugin"),),
        ),
        "go",
    )

    told = heard(tmp_path)
    assert "tabs, never spaces" in told, "a fragment never reached a CLI that has its own flag"
    assert "house-style" in told, "and it must still be named"
    assert "be brief" not in told, "while the flag keeps delivering the instructions"
