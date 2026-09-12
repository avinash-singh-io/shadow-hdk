"""A CLI's streamed pieces are activity beside the record, never on it (D63).

Measured 2026-09-12: Claude Code with `--include-partial-messages` emits `stream_event` lines whose
`event.delta.type` is `thinking_delta` or `text_delta`, before the whole `assistant` message. The
dialect names them as data (`deltas`); the session hands each piece to `RunContext.activity` as
it arrives; the record gets exactly what it got before — the whole thought, the whole text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from shadow_hdk.adapters.basic import AllowAll

from shadow_hdk.adapters.jsonl import JsonlSession
from shadow_hdk.kernel import (
    Activity,
    Binding,
    Ceiling,
    Completed,
    Composition,
    Delta,
    Dialect,
    EffectProfile,
    Event,
    Floor,
    Invoke,
    Lease,
    Provider,
    Reasoning,
)
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)
from tests.adapters.jsonl.test_a_turn import CLAUDE_DIALECT, a_fake_cli

pytestmark = pytest.mark.anyio

STREAMING_DIALECT = Dialect(
    **{
        **CLAUDE_DIALECT.__dict__,
        "think_on": ("assistant",),
        "think_at": "message.content[].thinking",
        "delta_on": ("stream_event",),
        "delta_kind_at": "event.delta.type",
        "deltas": (
            Delta(on="thinking_delta", kind="thinking", at="event.delta.thinking"),
            Delta(on="text_delta", kind="text", at="event.delta.text"),
        ),
    }
)

LINES: list[dict[str, Any]] = [
    {
        "type": "stream_event",
        "event": {"type": "content_block_start", "content_block": {"type": "thinking"}},
    },
    {
        "type": "stream_event",
        "event": {
            "type": "content_block_delta",
            "delta": {"type": "thinking_delta", "thinking": "the handbook "},
        },
    },
    {
        "type": "stream_event",
        "event": {
            "type": "content_block_delta",
            "delta": {"type": "thinking_delta", "thinking": "lists it"},
        },
    },
    {
        "type": "stream_event",
        "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "12"}},
    },
    {
        "type": "stream_event",
        "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "kg"}},
    },
    {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "thinking", "thinking": "the handbook lists it"},
                {"type": "text", "text": "12kg"},
            ]
        },
    },
    {"type": "result", "subtype": "success", "result": "12kg", "is_error": False},
]


class Watching:
    def __init__(self) -> None:
        self.events: list[Event] = []
        self.activity: list[Activity] = []

    async def on(self, event: Event) -> None:
        self.events.append(event)

    async def on_activity(self, activity: Activity) -> None:
        self.activity.append(activity)


def a_provider(dialect: Dialect) -> Provider:
    return Provider(id="fake", kind="agent", bin="fake-cli", transport="jsonl", dialect=dialect)


async def _one_turn(tmp_path: Path, dialect: Dialect) -> tuple[Watching, list[Event]]:
    cli = a_fake_cli(tmp_path, LINES)
    session = JsonlSession(a_provider(dialect), binary=cli, env={}, workspace=tmp_path)
    talk_registration = make_registration("talk", effects=EffectProfile(costs=True))

    async def talk(_inputs: Any) -> Any:
        done = await session.turn("how heavy?")
        return Completed({"said": done.text})

    watching = Watching()
    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(talk_registration, talk)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
        observer=watching,
    )
    plan = Composition((Invoke("chat", "talk", (Binding("brief", value="go"),)),))
    try:
        events = [
            e
            async for e in run(
                plan, ports, options=RunOptions(lease=Lease(Ceiling(10, 60, 100), Floor(0)))
            )
        ]
    finally:
        await session.close()
    return watching, events


async def test_each_delta_is_activity_as_it_arrives_and_the_record_is_unchanged(
    tmp_path: Path,
) -> None:
    watching, events = await _one_turn(tmp_path, STREAMING_DIALECT)

    assert [(a.kind, a.text) for a in watching.activity] == [
        ("thinking", "the handbook "),
        ("thinking", "lists it"),
        ("text", "12"),
        ("text", "kg"),
    ]
    assert all(a.step == "chat" for a in watching.activity)
    assert [e.text for e in events if isinstance(e, Reasoning)] == ["the handbook lists it"]
    assert not [e for e in events if isinstance(e, Activity)]


async def test_a_dialect_that_names_no_deltas_streams_nothing(tmp_path: Path) -> None:
    watching, events = await _one_turn(tmp_path, CLAUDE_DIALECT)

    assert watching.activity == []
    assert [e.kind for e in events if e.kind == "reasoning"] == []


def test_the_shipped_claude_code_file_names_the_measured_deltas() -> None:
    from shadow_hdk.providers import shipped

    claude = shipped()["claude-code"]
    assert "--include-partial-messages" in claude.launch_args
    assert claude.dialect is not None
    assert claude.dialect.delta_on == ("stream_event",)
    assert claude.dialect.delta_kind_at == "event.delta.type"
    assert {(d.on, d.kind, d.at) for d in claude.dialect.deltas} == {
        ("thinking_delta", "thinking", "event.delta.thinking"),
        ("text_delta", "text", "event.delta.text"),
    }


REPEATED: list[dict[str, Any]] = [
    {
        "type": "assistant",
        "message": {"content": [{"type": "thinking", "thinking": "one thought"}]},
    },
    {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "thinking", "thinking": "one thought"},
                {"type": "text", "text": "12kg"},
            ]
        },
    },
    {"type": "result", "subtype": "success", "result": "12kg", "is_error": False},
]


async def test_a_thought_repeated_across_assistant_lines_is_one_thought(tmp_path: Path) -> None:
    """Measured live: with partial messages on, Claude Code emits an `assistant` line per content
    block, each carrying the whole message so far — the same thinking block twice."""
    from shadow_hdk.adapters.jsonl import JsonlSession as Session

    cli = a_fake_cli(tmp_path, REPEATED)
    session = Session(a_provider(STREAMING_DIALECT), binary=cli, env={}, workspace=tmp_path)
    try:
        done = await session.turn("how heavy?")
    finally:
        await session.close()
    assert done.reasoning == "one thought"
