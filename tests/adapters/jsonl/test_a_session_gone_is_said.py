"""A CLI asked to resume a session it no longer has says so, and the turn says *session gone*
(ENH-024, D139) — from the provider's file, never a code path.

Measured 2026-09-20. Claude Code 2.1.278 with `--resume <unknown>`: one line on stderr, then a
`result` with `subtype: "error_during_execution"`, `is_error: true` and
`errors: ["No conversation found with session ID: <id>"]`, exit 0. Codex 0.154.0 with
`exec resume <unknown> --json`: nothing on stdout at all; on stderr
`Error: thread/resume: thread/resume failed: no rollout found for thread id <id> (code -32600)`.

Which is how BUG-059 was found: the session opened the CLI's stderr as a pipe and never read it —
Codex's *gone* was on that pipe, and a CLI that writes more than the pipe holds blocks forever.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.jsonl.session import JsonlSession
from shadow_hdk.kernel import Dialect, Provider
from shadow_hdk.providers.library import shipped as shipped_providers

pytestmark = pytest.mark.anyio

UNKNOWN = "00000000-0000-0000-0000-000000000000"

CLAUDE_GONE_STDERR = f"No conversation found with session ID: {UNKNOWN}"
CLAUDE_GONE_RESULT: dict[str, Any] = {
    "type": "result",
    "subtype": "error_during_execution",
    "duration_ms": 0,
    "is_error": True,
    "num_turns": 0,
    "stop_reason": None,
    "session_id": UNKNOWN,
    "total_cost_usd": 0,
    "usage": {
        "input_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "output_tokens": 0,
    },
    "errors": [CLAUDE_GONE_STDERR],
}
CODEX_GONE_STDERR = (
    f"Error: thread/resume: thread/resume failed: no rollout found for thread id {UNKNOWN} "
    "(code -32600)"
)
CODEX_LIMIT_FAILED: dict[str, Any] = {
    "type": "turn.failed",
    "error": {"message": "You've hit your usage limit. Try again later."},
}


def shipped(id: str) -> Provider:
    return shipped_providers()[id]


def dialect_of(provider: Provider) -> Dialect:
    assert provider.dialect is not None
    return provider.dialect


def a_fake_cli(
    where: Path,
    *,
    stdout: list[dict[str, Any]],
    stderr: str = "",
    resident: bool,
) -> Path:
    """A CLI that reads its prompt, writes `stderr` (once, whatever its size), then the lines."""
    body = "\n".join(f"print({json.dumps(json.dumps(line))}, flush=True)" for line in stdout)
    read = "sys.stdin.readline()" if resident else "sys.stdin.read()"
    made = where / "fake-cli"
    made.write_text(
        "#!/usr/bin/env python3\nimport sys\n"
        f"{read}\n"
        f"sys.stderr.write({json.dumps(stderr)}); sys.stderr.flush()\n"
        f"{body}\n",
        encoding="utf-8",
    )
    made.chmod(0o755)
    return made


async def a_turn(where: Path, provider: Provider, cli: Path, *, resume: str | None = None) -> Any:
    session = JsonlSession(
        provider,
        binary=cli,
        env={"PATH": "/usr/bin:/bin"},
        workspace=where,
        timeout_s=20,
        resume=resume,
    )
    try:
        turn = await session.turn("?")
    finally:
        await session.close()
    return turn, session


async def test_claude_code_says_the_session_is_gone(tmp_path: Path) -> None:
    cli = a_fake_cli(
        tmp_path, stdout=[CLAUDE_GONE_RESULT], stderr=CLAUDE_GONE_STDERR + "\n", resident=True
    )
    turn, _ = await a_turn(tmp_path, shipped("claude-code"), cli, resume=UNKNOWN)

    assert turn.failed is True
    assert turn.session_gone is True
    assert UNKNOWN in turn.text, "the CLI's own sentence is what the person reads"


async def test_codex_says_the_session_is_gone_on_stderr_alone(tmp_path: Path) -> None:
    cli = a_fake_cli(tmp_path, stdout=[], stderr=CODEX_GONE_STDERR + "\n", resident=False)
    turn, session = await a_turn(tmp_path, shipped("codex"), cli, resume=UNKNOWN)

    assert turn.failed is True
    assert turn.session_gone is True
    assert "no rollout found" in session.stderr, "stderr is read, not just opened (BUG-059)"


async def test_another_failure_is_a_failure_and_not_a_gone_session(tmp_path: Path) -> None:
    cli = a_fake_cli(tmp_path, stdout=[CODEX_LIMIT_FAILED], resident=False)
    turn, _ = await a_turn(tmp_path, shipped("codex"), cli)

    assert turn.failed is True
    assert turn.session_gone is False
    assert "usage limit" in turn.text


async def test_a_cli_that_floods_stderr_still_ends_its_turn(tmp_path: Path) -> None:
    """BUG-059: a megabyte on stderr — a progress bar, a stack of warnings — must not wedge the
    turn on a full pipe. The tail is kept; the rest is let go."""
    flood = ("x" * 1023 + "\n") * 1024  # 1 MiB
    done = {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}}
    said = {"type": "item.completed", "item": {"id": "i", "type": "agent_message", "text": "ok"}}
    cli = a_fake_cli(tmp_path, stdout=[said, done], stderr=flood, resident=False)

    turn, session = await a_turn(tmp_path, shipped("codex"), cli)

    assert turn.failed is False and turn.text == "ok"
    assert 0 < len(session.stderr) <= 64 * 1024, "the tail, bounded"


async def test_the_matches_are_the_files_and_a_dialect_without_them_never_says_gone(
    tmp_path: Path,
) -> None:
    codex = shipped("codex")
    assert dialect_of(codex).session_gone_matches == ("no rollout found for thread id",)
    assert dialect_of(shipped("claude-code")).session_gone_matches == (
        "No conversation found with session ID",
    )
    assert dialect_of(shipped("claude-code")).failed_text_at == "errors"

    silent = replace(codex, dialect=replace(dialect_of(codex), session_gone_matches=()))
    cli = a_fake_cli(tmp_path, stdout=[], stderr=CODEX_GONE_STDERR + "\n", resident=False)
    turn, _ = await a_turn(tmp_path, silent, cli, resume=UNKNOWN)

    assert turn.failed is True and turn.session_gone is False
