"""What a turn really cost includes what the cache did (ENH-023, D141).

Claude Code reports the bulk of a subscription turn's input as a cache read — a turn whose
standing prompt alone was 391 tokens came back `input_tokens: 10` — and Codex reports
`cached_input_tokens` and `cache_write_input_tokens` beside `input_tokens`. A `Usage` that
could not say so made a product's *cached* figure a zero, and zero means "the cache did no work",
which is a claim. The fields are the kit's; each dialect names where its own are, in its file;
where a stream does not carry them the field is `None` — unknown, never zero.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.jsonl.session import JsonlSession
from shadow_hdk.kernel import Dialect, Provider
from shadow_hdk.providers.library import shipped as shipped_providers


def shipped(id: str) -> Provider:
    return shipped_providers()[id]


def dialect_of(provider: Provider) -> Dialect:
    assert provider.dialect is not None
    return provider.dialect


pytestmark = pytest.mark.anyio

# Verbatim from `codex.toml`'s measured stream (2026-09-11), text shortened.
CODEX_LINES: list[dict[str, Any]] = [
    {"type": "thread.started", "thread_id": "01a091b9-6be9-71e0-9802-d3834284ecf7"},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": "done"}},
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

# Verbatim shape of Claude Code 2.1.278's `result` usage (measured 2026-09-20), numbers made up.
CLAUDE_LINES: list[dict[str, Any]] = [
    {"type": "system", "subtype": "init", "tools": []},
    {"type": "assistant", "message": {"content": [{"type": "text", "text": "done"}]}},
    {
        "type": "result",
        "subtype": "success",
        "result": "done",
        "is_error": False,
        "stop_reason": "end_turn",
        "total_cost_usd": 0.0031,
        "usage": {
            "input_tokens": 10,
            "cache_creation_input_tokens": 391,
            "cache_read_input_tokens": 12044,
            "output_tokens": 1195,
        },
    },
]


def a_fake_cli(where: Path, lines: list[dict[str, Any]], *, resident: bool) -> Path:
    body = "\n".join(f"print({json.dumps(json.dumps(line))}, flush=True)" for line in lines)
    read = "sys.stdin.readline()" if resident else "sys.stdin.read()"
    made = where / "fake-cli"
    made.write_text(f"#!/usr/bin/env python3\nimport sys\n{read}\n{body}\n", encoding="utf-8")
    made.chmod(0o755)
    return made


def with_dialect(provider: Provider, dialect: Dialect) -> Provider:
    from dataclasses import replace

    return replace(provider, dialect=dialect)


async def a_turn(where: Path, provider: Provider, lines: list[dict[str, Any]]) -> Any:
    cli = a_fake_cli(where, lines, resident=dialect_of(provider).resident)
    session = JsonlSession(
        provider, binary=cli, env={"PATH": "/usr/bin:/bin"}, workspace=where, timeout_s=20
    )
    try:
        return await session.turn("?")
    finally:
        await session.close()


async def test_codexs_cache_tokens_are_read_from_its_shipped_file(tmp_path: Path) -> None:
    turn = await a_turn(tmp_path, shipped("codex"), CODEX_LINES)

    assert turn.usage is not None
    assert turn.usage.input_tokens == 32154 and turn.usage.output_tokens == 182
    assert turn.usage.cache_read_tokens == 26112
    assert turn.usage.cache_write_tokens == 0


async def test_claude_codes_cache_tokens_are_read_from_its_shipped_file(tmp_path: Path) -> None:
    turn = await a_turn(tmp_path, shipped("claude-code"), CLAUDE_LINES)

    assert turn.usage is not None
    assert turn.usage.input_tokens == 10 and turn.usage.output_tokens == 1195
    assert turn.usage.cache_read_tokens == 12044
    assert turn.usage.cache_write_tokens == 391


async def test_a_stream_without_cache_fields_leaves_them_unknown(tmp_path: Path) -> None:
    """Unknown, never zero (D141): the fields are `None` when the stream does not carry them."""
    lines = [dict(line) for line in CODEX_LINES]
    lines[-1] = {"type": "turn.completed", "usage": {"input_tokens": 5, "output_tokens": 1}}
    turn = await a_turn(tmp_path, shipped("codex"), lines)

    assert turn.usage is not None
    assert turn.usage.input_tokens == 5
    assert turn.usage.cache_read_tokens is None and turn.usage.cache_write_tokens is None


async def test_a_dialect_that_names_no_cache_field_reports_none(tmp_path: Path) -> None:
    """A provider file that does not know where cache tokens are says so by leaving the two
    `*_at` paths empty — the shipped OpenCode file, or a third CLI's first draft."""
    codex = shipped("codex")
    from dataclasses import replace

    dialect = replace(dialect_of(codex), cache_read_tokens_at="", cache_write_tokens_at="")
    turn = await a_turn(tmp_path, with_dialect(codex, dialect), CODEX_LINES)

    assert turn.usage is not None and turn.usage.input_tokens == 32154
    assert turn.usage.cache_read_tokens is None and turn.usage.cache_write_tokens is None


def test_the_shipped_files_name_the_measured_fields() -> None:
    """The names are in the files beside the measurement, not in a code path."""
    codex, claude = dialect_of(shipped("codex")), dialect_of(shipped("claude-code"))
    assert codex.cache_read_tokens_at == "usage.cached_input_tokens"
    assert codex.cache_write_tokens_at == "usage.cache_write_input_tokens"
    assert claude.cache_read_tokens_at == "usage.cache_read_input_tokens"
    assert claude.cache_write_tokens_at == "usage.cache_creation_input_tokens"
    assert shipped("opencode").dialect is None, "OpenCode speaks ACP, not a JSONL dialect"
