"""Sessions that idle out (Phase 30 group 6, D94).

One app server, many people: every open thread held a resident provider session — a CLI
subprocess — until the session closed. Codex unloads a thread after thirty idle minutes and
reloads it on demand; ours does the same: after `idle_seconds` without a turn the provider's
session is closed, the thread stays open and held, and the next turn reopens the provider on
its own session id (D76), memory kept.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.runtime.conversation import Conversation
from shadow_hdk.runtime.threads import InMemoryThreads, Thread
from shadow_hdk.testing import ScriptedAgent
from tests.runtime.test_a_conversation_without_a_record import Seen, _lease, _ports

pytestmark = pytest.mark.anyio


async def test_the_provider_is_closed_when_idle_and_reopened_on_its_session_at_the_next_turn(
    tmp_path: Path,
) -> None:
    agent = ScriptedAgent([([], "one"), ([], "two")])
    conversation = await Conversation.open(
        agent=cast(Any, agent),
        ports=_ports(Seen()),
        root=tmp_path,
        lease=_lease(),
        idle_seconds=0.15,
    )
    try:
        [e async for e in conversation.turn("first")]
        assert agent.opened == 1 and agent.closed == 0
        await asyncio.sleep(0.4)
        assert agent.closed == 1, "idle: the provider was closed"
        assert not conversation.closed, "the conversation is open; only the provider went"
        [e async for e in conversation.turn("second")]
        assert agent.opened == 2 and agent.resumed[-1] == "scripted-session", "reopened, resumed"
        assert conversation.last is not None and conversation.last.text == "two"
    finally:
        await conversation.close()
    assert agent.closed == 2


async def test_a_turn_within_the_idle_time_keeps_the_provider(tmp_path: Path) -> None:
    agent = ScriptedAgent([([], "one"), ([], "two"), ([], "three")])
    conversation = await Conversation.open(
        agent=cast(Any, agent),
        ports=_ports(Seen()),
        root=tmp_path,
        lease=_lease(),
        idle_seconds=0.3,
    )
    try:
        for prompt in ("a", "b", "c"):
            [e async for e in conversation.turn(prompt)]
            await asyncio.sleep(0.1)
        assert agent.opened == 1 and agent.closed == 0
    finally:
        await conversation.close()


async def test_without_idle_seconds_the_provider_stays(tmp_path: Path) -> None:
    agent = ScriptedAgent([([], "one")])
    conversation = await Conversation.open(
        agent=cast(Any, agent), ports=_ports(Seen()), root=tmp_path, lease=_lease()
    )
    try:
        [e async for e in conversation.turn("first")]
        await asyncio.sleep(0.2)
        assert agent.closed == 0
    finally:
        await conversation.close()


async def test_a_thread_idles_out_and_stays_held(tmp_path: Path) -> None:
    store = InMemoryThreads()
    agent = ScriptedAgent([([], "one"), ([], "two")])
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=_ports(Seen()),
        store=store,
        root=tmp_path,
        lease=_lease(),
        holder="host-a",
        idle_seconds=0.15,
    )
    try:
        [e async for e in thread.turn("first")]
        await asyncio.sleep(0.4)
        assert agent.closed == 1
        assert await store.held_by(thread.id) == "host-a", "idle is not closed: still held"
        [e async for e in thread.turn("second")]
        assert thread.record.turns[-1].text == "two" and agent.opened == 2
    finally:
        await thread.close()
