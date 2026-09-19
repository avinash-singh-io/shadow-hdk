"""`turn/start {attributes}` and `thread/resume {attributes}` (ENH-037, D140) over the wire: a
turn's words reach that turn's judgements and not the next's; a resume's words replace the
record's and the result says so; a reserved name is `invalid`, as at `thread/start`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.kernel import EffectProfile
from shadow_hdk.kernel.ports import Allow, Context, Judgement
from shadow_hdk.serve import ServeHost, Settings
from shadow_hdk.wire.peer import RemoteError
from shadow_hdk.wire.sides import loopback
from tests.serve.test_serve_answers_a_host_in_any_language import ScriptedProvider

pytestmark = pytest.mark.anyio


class Seen:
    def __init__(self) -> None:
        self.contexts: list[Context] = []

    async def judge(self, _effects: EffectProfile, context: Context) -> Judgement:
        self.contexts.append(context)
        return Allow()

    def turn_words(self, turn_step: str) -> dict[str, Any]:
        found = [c for c in self.contexts if c.step == turn_step]
        assert found, f"no judgement at {turn_step}: {[c.step for c in self.contexts]}"
        return dict(found[-1].attributes)


async def test_a_turns_words_and_a_resumes_words(tmp_path: Path) -> None:
    seen = Seen()
    host = ServeHost(
        Settings(root=tmp_path, mode="full", store=f"sqlite:///{tmp_path}/t.sqlite"),
        agent=ScriptedProvider(),
        governance=seen,
    )
    try:
        async with loopback(threads=host) as (client, _runtime):
            await client.initialize()
            started = await client.peer.call(
                "thread/start",
                {"root": "", "mode": "", "name": "", "attributes": {"tenant": "acme"}},
            )
            tid = started["thread_id"]

            await client.peer.call(
                "turn/start", {"thread_id": tid, "text": "one", "attributes": {"workspace": "w-1"}}
            )
            assert seen.turn_words("turn-1") == {
                **seen.turn_words("turn-1"),
                "tenant": "acme",
                "workspace": "w-1",
            }

            await client.peer.call("turn/start", {"thread_id": tid, "text": "two"})
            assert "workspace" not in seen.turn_words("turn-2"), "the turn's words were the turn's"

            with pytest.raises(RemoteError) as bad:
                await client.peer.call(
                    "turn/start", {"thread_id": tid, "text": "x", "attributes": {"mode": "full"}}
                )
            assert bad.value.data == {"kind": "invalid"}

            await client.peer.call("thread/close", {"thread_id": tid})
            resumed = await client.peer.call(
                "thread/resume",
                {"thread_id": tid, "attributes": {"tenant": "acme", "workspace": "w-2"}},
            )
            assert resumed["attributes"] == {"tenant": "acme", "workspace": "w-2"}
            await client.peer.call("turn/start", {"thread_id": tid, "text": "three"})
            assert seen.turn_words("turn-3").get("workspace") == "w-2"
    finally:
        await host.aclose()
