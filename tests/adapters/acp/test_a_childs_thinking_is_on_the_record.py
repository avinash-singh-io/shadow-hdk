"""A child agent's thinking reaches the record (D45).

ACP carries it as `agent_thought_chunk` session updates, beside `agent_message_chunk` for what it
said. Read the same way, kept separately, and — inside a run — put on the record as each chunk
arrives, because the tool calls it led to are already landing there through the bridge's doors.
"""

from __future__ import annotations

from types import SimpleNamespace

from shadow_hdk.adapters.acp import BridgeClient


def a_chunk(kind: str, text: str) -> SimpleNamespace:
    return SimpleNamespace(session_update=kind, content=SimpleNamespace(text=text))


async def test_a_thought_chunk_is_kept_apart_from_what_was_said() -> None:
    client = BridgeClient()

    await client.session_update("s", a_chunk("agent_thought_chunk", "the handbook, then"))
    await client.session_update("s", a_chunk("agent_message_chunk", "12kg"))

    assert client.thought == ["the handbook, then"]
    assert client.said == ["12kg"], "a thought was reported as speech"


async def test_thoughts_are_taken_per_turn() -> None:
    """`take_thought()` hands back what this turn thought and clears it — the same shape the purse
    has, for the same reason: a session is cumulative and a turn is not."""
    client = BridgeClient()
    await client.session_update("s", a_chunk("agent_thought_chunk", "one"))

    first = client.take_thought()
    await client.session_update("s", a_chunk("agent_thought_chunk", "two"))

    assert first == "one"
    assert client.take_thought() == "two"
    assert client.take_thought() == ""
