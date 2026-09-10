"""One turn of a CLI that answers in line-delimited JSON, read by its dialect (D39, D40).

Driven against a **fake CLI the test writes** — a short script that prints the event shapes a real
one prints. That is not a double standing in for the protocol: the protocol *is* lines of JSON on a
pipe, and this speaks it over a real pipe from a real process. What the fake stands in for is the
model, which costs money and cannot be made to say the same thing twice.

The shapes it prints were measured from claude 2.1.235 on 2026-09-11, and the live test next door
runs the same assertions against the real thing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.jsonl.session import JsonlSession
from shadow_hdk.kernel import Dialect, Provider

CLAUDE_DIALECT = Dialect(
    resident=True,
    prompt_shape="stream-json-user",
    say_on=("assistant",),
    say_at="message.content[].text",
    done_on=("result",),
    done_at="result",
    failed_at="is_error",
    stop_reason_at="stop_reason",
    cost_usd_at="total_cost_usd",
    input_tokens_at="usage.input_tokens",
    output_tokens_at="usage.output_tokens",
)

LINES: list[dict[str, Any]] = [
    {"type": "system", "subtype": "init", "tools": []},
    {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "text", "text": "the lathe "},
                {"type": "text", "text": "weighs 12kg"},
            ]
        },
    },
    {
        "type": "result",
        "subtype": "success",
        "result": "the lathe weighs 12kg",
        "is_error": False,
        "stop_reason": "end_turn",
        "total_cost_usd": 0.0031,
        "usage": {"input_tokens": 120, "output_tokens": 30},
    },
]


def a_fake_cli(where: Path, lines: list[dict[str, Any]]) -> Path:
    """A CLI that reads one line and answers with the shapes a real one answers with."""
    body = "\n".join(f"print({json.dumps(json.dumps(line))}, flush=True)" for line in lines)
    made = where / "fake-cli"
    made.write_text(
        "#!/usr/bin/env python3\nimport sys\nsys.stdin.readline()\n" + body + "\n", encoding="utf-8"
    )
    made.chmod(0o755)
    return made


def a_provider(dialect: Dialect = CLAUDE_DIALECT) -> Provider:
    return Provider(id="fake", kind="agent", bin="fake-cli", transport="jsonl", dialect=dialect)


async def test_a_turn_comes_back_with_what_it_said(tmp_path: Path) -> None:
    cli = a_fake_cli(tmp_path, LINES)
    session = JsonlSession(
        a_provider(), binary=cli, env={"PATH": "/usr/bin:/bin"}, workspace=tmp_path
    )

    try:
        done = await session.turn("how heavy is the lathe?")
    finally:
        await session.close()

    assert done.text == "the lathe weighs 12kg"
    assert done.stop_reason == "end_turn"


async def test_what_it_spent_is_read_from_the_stream(tmp_path: Path) -> None:
    """The purse the parent's meter charges. Dollars in, cents out — a provider reports what it
    reports and the kernel counts in cents."""
    cli = a_fake_cli(tmp_path, LINES)
    session = JsonlSession(
        a_provider(), binary=cli, env={"PATH": "/usr/bin:/bin"}, workspace=tmp_path
    )

    try:
        done = await session.turn("go")
    finally:
        await session.close()

    assert done.usage is not None
    assert done.usage.input_tokens == 120
    assert done.usage.output_tokens == 30
    assert done.usage.cost_cents == 1, "0.0031 USD rounds up to a cent, never down to nothing"


async def test_a_failed_turn_says_so_rather_than_looking_finished(tmp_path: Path) -> None:
    """Read from the stream's own flag, not from the exit code: these CLIs exit non-zero for
    reasons that are not failures, and zero for failures that are. Measured — an expired session
    answers `is_error: true` inside a `result` whose subtype is still `success`."""
    failed: list[dict[str, Any]] = [
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "Failed to authenticate"}]},
        },
        {
            "type": "result",
            "subtype": "success",
            "result": "Failed to authenticate",
            "is_error": True,
            "stop_reason": "stop_sequence",
        },
    ]
    cli = a_fake_cli(tmp_path, failed)
    session = JsonlSession(
        a_provider(), binary=cli, env={"PATH": "/usr/bin:/bin"}, workspace=tmp_path
    )

    try:
        done = await session.turn("go")
    finally:
        await session.close()

    assert done.failed is True
    assert "Failed to authenticate" in done.text


async def test_an_unreadable_line_does_not_end_the_turn(tmp_path: Path) -> None:
    """A CLI printing a warning, a banner or a progress bar on stdout is ordinary. Untrusted input:
    one line nobody can parse must not lose the turn around it."""
    noisy: list[dict[str, Any]] = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "fine"}]}}
    ]
    cli = tmp_path / "fake-cli"
    cli.write_text(
        "#!/usr/bin/env python3\nimport sys\nsys.stdin.readline()\n"
        "print('warning: something', flush=True)\n"
        f"print({json.dumps(json.dumps(noisy[0]))}, flush=True)\n"
        f"print({json.dumps(json.dumps(LINES[2]))}, flush=True)\n",
        encoding="utf-8",
    )
    cli.chmod(0o755)
    session = JsonlSession(
        a_provider(), binary=cli, env={"PATH": "/usr/bin:/bin"}, workspace=tmp_path
    )

    try:
        done = await session.turn("go")
    finally:
        await session.close()

    assert done.text == "the lathe weighs 12kg"


async def test_a_dialect_that_names_nothing_reads_nothing_rather_than_inventing(
    tmp_path: Path,
) -> None:
    """The conservative default reaching the transport: a provider file that described no events
    gets an empty turn, not a guessed one."""
    cli = a_fake_cli(tmp_path, LINES)
    session = JsonlSession(
        a_provider(Dialect(resident=True, prompt_shape="stream-json-user")),
        binary=cli,
        env={"PATH": "/usr/bin:/bin"},
        workspace=tmp_path,
    )

    try:
        done = await session.turn("go")
    finally:
        await session.close()

    assert done.text == ""
