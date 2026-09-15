"""Refusals a client can switch on (Phase 30 group 4, D92).

A JSON-RPC error carried a code, a sentence, and — by accident of `peer.py` — the exception's
class name in `data`. A product switching on *what* was refused needs a vocabulary it can rely
on: `error.data.kind` is one of `ERROR_KINDS`, with the detail a client acts on beside it — a
held thread's holder, a running turn's id.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

from shadow_hdk.adapters.environment import local_sandbox
from shadow_hdk.runtime.environment import Mode
from shadow_hdk.serve import ServeHost, Settings
from shadow_hdk.wire.peer import RemoteError
from shadow_hdk.wire.protocol import ERROR_KINDS, PROTOCOL_VERSION
from shadow_hdk.wire.sides import loopback
from tests.wire.test_one_thread_one_holder_over_the_wire import SlowProvider, _host

pytestmark = pytest.mark.anyio

ENFORCEABLE: Mode = "workspace-write" if local_sandbox() is not None else "full"


def test_the_vocabulary_is_published() -> None:
    assert {
        "thread_held",
        "turn_running",
        "capability_mismatch",
        "not_found",
        "invalid",
        "version_mismatch",
        "unknown_method",
        "refused",
        "gone",
    } <= set(ERROR_KINDS)


async def test_a_held_thread_says_so_by_kind_with_the_holder(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path}/live.sqlite"
    one, two = _host(tmp_path, url), _host(tmp_path, url)
    try:
        async with loopback(threads=one) as (client, _r), loopback(threads=two) as (other, _s):
            await client.initialize()
            await other.initialize()
            started = await client.peer.call("thread/start", {"root": "", "mode": "", "name": ""})
            tid = started["thread_id"]
            with pytest.raises(RemoteError) as refused:
                await other.peer.call("thread/resume", {"thread_id": tid})
            assert refused.value.data == {
                "kind": "thread_held",
                "thread_id": tid,
                "holder": one.holder,
            }
    finally:
        await one.aclose()
        await two.aclose()


async def test_a_running_turn_an_unknown_thread_and_a_bad_word_each_have_their_kind(
    tmp_path: Path,
) -> None:
    host = ServeHost(Settings(root=tmp_path, mode=ENFORCEABLE), agent=SlowProvider())
    provider = cast(SlowProvider, host._agent)  # noqa: SLF001 — the double handed in
    try:
        async with loopback(threads=host) as (client, _runtime):
            await client.initialize()
            started = await client.peer.call("thread/start", {"root": "", "mode": "", "name": ""})
            tid = started["thread_id"]
            first = asyncio.create_task(
                client.peer.call("turn/start", {"thread_id": tid, "text": "one"})
            )
            await provider.running(1)
            with pytest.raises(RemoteError) as running:
                await client.peer.call(
                    "turn/start", {"thread_id": tid, "text": "two", "when": "reject"}
                )
            assert running.value.data == {
                "kind": "turn_running",
                "thread_id": tid,
                "turn_id": "turn-1",
            }
            with pytest.raises(RemoteError) as bad:
                await client.peer.call(
                    "turn/start", {"thread_id": tid, "text": "x", "when": "later"}
                )
            assert bad.value.data == {"kind": "invalid"}
            with pytest.raises(RemoteError) as missing:
                await client.peer.call("thread/resume", {"thread_id": "nobody"})
            assert missing.value.data == {"kind": "not_found"}
            with pytest.raises(RemoteError) as unknown:
                await client.peer.call("no/such", {})
            assert unknown.value.data == {"kind": "unknown_method"}
            assert provider.current is not None
            provider.current.set()
            await first
    finally:
        await host.aclose()


async def test_a_version_mismatch_and_a_plain_refusal_have_theirs() -> None:
    async with loopback() as (client, _runtime):
        with pytest.raises(RemoteError) as mismatch:
            await client.peer.call("initialize", {"protocol_version": "0"})
        assert mismatch.value.data == {"kind": "version_mismatch"}
        await client.peer.call("initialize", {"protocol_version": PROTOCOL_VERSION})
        with pytest.raises(RemoteError) as plain:
            await client.peer.call("thread/start", {"root": ""})  # no thread host here
        assert plain.value.data == {"kind": "refused"}
