"""A CLI's thinking reaches the record, and where it sits is a field on the dialect (D45, D40).

Claude Code's stream-json carries thinking as content blocks — `{"type": "thinking", "thinking":
…}` on an `assistant` event — beside the text blocks. Codex carries it elsewhere. The *shape* is the
one the dialect already describes for text: an event type to watch, a path to read. So reasoning is
two more fields on the record, `think_on` and `think_at`, and not a branch per provider.

Two things happen with what is read. It comes back on `Turn.reasoning`, for a caller holding the
turn. And **if the session is running inside a run**, each thought is put on the record as it
arrives — *why before what* — because the tool calls it led to are already landing there through
the socket, and a thought that arrived after all of them would read as an afterthought.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shadow_hdk.adapters.jsonl.session import JsonlSession
from shadow_hdk.kernel import Dialect, Provider
from tests.adapters.jsonl.test_a_turn import CLAUDE_DIALECT, a_fake_cli

THINKING_DIALECT = Dialect(
    **{
        **CLAUDE_DIALECT.__dict__,
        "think_on": ("assistant",),
        "think_at": "message.content[].thinking",
    }
)

LINES: list[dict[str, Any]] = [
    {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "thinking", "thinking": "the handbook lists it by line; "},
                {"type": "thinking", "thinking": "line 3 is the lathe"},
                {"type": "text", "text": "12kg"},
            ]
        },
    },
    {"type": "result", "subtype": "success", "result": "12kg", "is_error": False},
]


def a_provider(dialect: Dialect) -> Provider:
    return Provider(id="fake", kind="agent", bin="fake-cli", transport="jsonl", dialect=dialect)


async def test_thinking_comes_back_on_the_turn(tmp_path: Path) -> None:
    cli = a_fake_cli(tmp_path, LINES)
    session = JsonlSession(a_provider(THINKING_DIALECT), binary=cli, env={}, workspace=tmp_path)
    try:
        done = await session.turn("how heavy?")
    finally:
        await session.close()

    assert done.reasoning == "the handbook lists it by line; line 3 is the lathe"
    assert done.text == "12kg", "a thinking block leaked into the text"


async def test_a_dialect_that_names_no_thinking_reads_none(tmp_path: Path) -> None:
    """The conservative default: a provider file that did not say where thinking is, has none."""
    cli = a_fake_cli(tmp_path, LINES)
    session = JsonlSession(a_provider(CLAUDE_DIALECT), binary=cli, env={}, workspace=tmp_path)
    try:
        done = await session.turn("how heavy?")
    finally:
        await session.close()

    assert done.reasoning == ""


async def test_inside_a_run_each_thought_lands_on_the_record_as_it_arrives(tmp_path: Path) -> None:
    """Why before what. The tool calls a subscription-driven agent makes land on the record through
    the socket as they happen; its thinking has to land the same way or it reads as hindsight."""
    from shadow_hdk.adapters.basic import AllowAll
    from shadow_hdk.kernel import (
        Binding,
        Ceiling,
        Completed,
        Composition,
        EffectProfile,
        Floor,
        Invoke,
        Lease,
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

    cli = a_fake_cli(tmp_path, LINES)
    session = JsonlSession(a_provider(THINKING_DIALECT), binary=cli, env={}, workspace=tmp_path)
    TALK = make_registration("talk", effects=EffectProfile(costs=True))

    async def talk(_inputs: Any) -> Any:
        done = await session.turn("how heavy?")
        return Completed({"said": done.text})

    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(TALK, talk)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    plan = Composition((Invoke("chat", TALK.id, (Binding("brief", value="go"),)),))
    try:
        events = [
            e
            async for e in run(
                plan, ports, options=RunOptions(lease=Lease(Ceiling(10, 60, 100), Floor(0)))
            )
        ]
    finally:
        await session.close()

    thoughts = [e for e in events if isinstance(e, Reasoning)]
    assert [t.text for t in thoughts] == [
        "the handbook lists it by line; ",
        "line 3 is the lathe",
    ], "thoughts did not land on the record one by one"
    assert all(t.step == "chat" for t in thoughts)
