"""Codex's line-delimited JSON, as measured signed-in on 2026-09-11 (`codex-cli 0.154.0`).

Two things its stream needs that Claude Code's did not. A **sub-type**: every item arrives as
`item.completed`, and only `item.type == "agent_message"` carries the assistant's words — a
`command_execution` item completing has a `command` and an `aggregated_output`, not text, and a
`reasoning` item (documented; not observed in three turns with reasoning enabled) would carry text
that is not what the agent *said*. And **tools as overrides**: Codex takes its MCP servers as
repeated `-c mcp_servers.<name>.<field>=<toml>` rather than one JSON blob.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.jsonl.session import JsonlSession
from shadow_hdk.adapters.jsonl.transport import argv_for
from shadow_hdk.kernel import Dialect, Provider
from shadow_hdk.kernel.ports import ToolSource
from shadow_hdk.providers import shipped

pytestmark = pytest.mark.anyio

CODEX_DIALECT = Dialect(
    resident=False,
    prompt_shape="text",
    subtype_key="item.type",
    say_on=("item.completed/agent_message",),
    say_at="item.text",
    think_on=("item.completed/reasoning",),
    think_at="item.text",
    done_on=("turn.completed", "turn.failed"),
    failed_at="error",
    failed_text_at="error.message",
    input_tokens_at="usage.input_tokens",
    output_tokens_at="usage.output_tokens",
    session_id_at="thread_id",
)

# Verbatim shapes from the measured stream, text shortened.
LINES: list[dict[str, Any]] = [
    {"type": "thread.started", "thread_id": "01a091b9-6be9-71e0-9802-d3834284ecf7"},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"id": "item_0", "type": "reasoning", "text": "count it"}},
    {
        "type": "item.completed",
        "item": {"id": "item_1", "type": "agent_message", "text": "I’ll check the line count."},
    },
    {
        "type": "item.started",
        "item": {
            "id": "item_2",
            "type": "command_execution",
            "command": "/bin/zsh -lc 'wc -l < names.txt'",
            "aggregated_output": "",
            "exit_code": None,
            "status": "in_progress",
        },
    },
    {
        "type": "item.completed",
        "item": {
            "id": "item_2",
            "type": "command_execution",
            "command": "/bin/zsh -lc 'wc -l < names.txt'",
            "aggregated_output": "       2\n",
            "exit_code": 0,
            "status": "completed",
        },
    },
    {"type": "item.completed", "item": {"id": "item_3", "type": "agent_message", "text": " 2"}},
    {
        "type": "turn.completed",
        "usage": {
            "input_tokens": 32154,
            "cached_input_tokens": 26112,
            "cache_write_input_tokens": 0,
            "output_tokens": 182,
            "reasoning_output_tokens": 51,
        },
    },
]


FAILS: list[dict[str, Any]] = [
    {"type": "thread.started", "thread_id": "01a091c4-589c-74a3-9958-7307babbdf09"},
    {"type": "turn.started"},
    {"type": "error", "message": "You've hit your usage limit. Upgrade to Plus…"},
    {"type": "turn.failed", "error": {"message": "You've hit your usage limit. Upgrade to Plus…"}},
]


def a_fake_codex(where: Path, lines: list[dict[str, Any]] = LINES) -> Path:
    body = "\n".join(f"print({json.dumps(json.dumps(line))}, flush=True)" for line in lines)
    made = where / "fake-codex"
    made.write_text(
        "#!/usr/bin/env python3\nimport sys\nsys.stdin.read()\n" + body + "\n", encoding="utf-8"
    )
    made.chmod(0o755)
    return made


def a_provider(dialect: Dialect = CODEX_DIALECT) -> Provider:
    return Provider(
        id="fake-codex", kind="agent", bin="fake-codex", transport="jsonl", dialect=dialect
    )


async def test_only_the_agents_message_items_are_what_it_said(tmp_path: Path) -> None:
    cli = a_fake_codex(tmp_path)
    session = JsonlSession(
        a_provider(), binary=cli, env={"PATH": "/usr/bin:/bin"}, workspace=tmp_path
    )
    try:
        done = await session.turn("how many lines?")
    finally:
        await session.close()

    assert done.text == "I’ll check the line count. 2"
    assert done.reasoning == "count it"
    assert "wc -l" not in done.text, "a command item's output is not what the agent said"
    assert done.usage is not None and done.usage.input_tokens == 32154
    assert done.usage.output_tokens == 182
    assert done.usage.cost_cents is None, "a subscription turn has no price; unknown is not zero"
    assert not done.failed


async def test_a_dialect_without_a_subtype_key_matches_on_type_alone(tmp_path: Path) -> None:
    """The old behaviour is the default: a `type/subtype` entry with no `subtype_key` cannot
    match, and a plain entry matches every item of that type."""
    plain = Dialect(say_on=("item.completed",), say_at="item.text", done_on=("turn.completed",))
    cli = a_fake_codex(tmp_path)
    session = JsonlSession(
        a_provider(plain), binary=cli, env={"PATH": "/usr/bin:/bin"}, workspace=tmp_path
    )
    try:
        done = await session.turn("go")
    finally:
        await session.close()
    assert done.text == "count itI’ll check the line count. 2", "every item's text, reasoning too"


async def test_a_failed_turn_says_why_where_the_person_reads(tmp_path: Path) -> None:
    """Measured on the owner's free tier: the limit, hit. The turn is failed, and the reason is
    the turn's text rather than a blank beside a flag."""
    cli = a_fake_codex(tmp_path, FAILS)
    session = JsonlSession(
        a_provider(), binary=cli, env={"PATH": "/usr/bin:/bin"}, workspace=tmp_path
    )
    try:
        done = await session.turn("go")
    finally:
        await session.close()

    assert done.failed
    assert done.text.startswith("You've hit your usage limit")


def test_tools_go_in_as_toml_overrides_where_the_cli_takes_them_that_way() -> None:
    overrides = Dialect(
        mcp_config_arg="-c",
        mcp_config_shape="overrides",
        allow_override='mcp_servers.{name}.default_tools_approval_mode="approve"',
    )
    provider = Provider(
        id="c",
        kind="agent",
        bin="codex",
        transport="jsonl",
        launch_args=("exec", "--json"),
        dialect=overrides,
    )
    relay = ToolSource(
        kind="mcp",
        address="/x/shadow-hdk-registry",
        env=(("SHADOW_HDK_REGISTRY_PORT", "4242"), ("SHADOW_HDK_REGISTRY_TOKEN", "t0k")),
    )

    argv = argv_for(provider, (relay,))

    assert argv[:2] == ["exec", "--json"]
    flags = argv[2:]
    assert flags[0::2] == ["-c", "-c", "-c", "-c"], flags
    assert flags[1] == 'mcp_servers.shadow-hdk.command="/x/shadow-hdk-registry"'
    assert flags[3] == "mcp_servers.shadow-hdk.args=[]"
    assert flags[5] == (
        'mcp_servers.shadow-hdk.env={SHADOW_HDK_REGISTRY_PORT="4242",SHADOW_HDK_REGISTRY_TOKEN="t0k"}'
    )
    # Pre-permitted, or `exec` refuses every tool that is not read-only (measured).
    assert flags[7] == 'mcp_servers.shadow-hdk.default_tools_approval_mode="approve"'


def test_the_shipped_codex_record_is_the_measured_one() -> None:
    codex = shipped()["codex"]
    assert codex.dialect is not None
    assert codex.dialect.subtype_key == "item.type"
    assert codex.dialect.say_on == ("item.completed/agent_message",)
    assert codex.dialect.done_on == ("turn.completed", "turn.failed")
    assert codex.dialect.failed_text_at == "error.message"
    assert codex.dialect.mcp_config_shape == "overrides"
    assert "default_tools_approval_mode" in codex.dialect.allow_override
    assert codex.dialect.cost_usd_at == "", "a subscription turn carries no price"
