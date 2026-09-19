"""`session_gone` on the wire (ENH-024, D139): `turn/start` on a thread whose CLI no longer has
the session answers an error of kind `session_gone` with `thread_id` and `session_id`, after the
turn's events were pushed and the turn record written `failed` with `failure = "session_gone"`.
The kind is in the published vocabulary and in the TypeScript client's union."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.kernel import Turn
from shadow_hdk.kernel.ports import AgentSession
from shadow_hdk.serve import ServeHost, Settings
from shadow_hdk.wire.peer import RemoteError
from shadow_hdk.wire.protocol import ERROR_KINDS
from shadow_hdk.wire.sides import loopback

pytestmark = pytest.mark.anyio

ROOT = Path(__file__).resolve().parents[2]


class GoneAfterOne:
    """Answers once; from the second turn on, the session says it is gone — a CLI whose session
    vanished between two turns of the same conversation."""

    def __init__(self) -> None:
        self.turns = 0

    async def open(self, *, resume: str | None = None, **_: Any) -> AgentSession:
        provider = self

        class _Session:
            session_id = "s-1"

            async def turn(self, prompt: str) -> Turn:
                provider.turns += 1
                if provider.turns > 1:
                    return Turn(
                        text="no rollout found for thread id s-1", failed=True, session_gone=True
                    )
                return Turn(text="said " + prompt)

            async def interrupt(self) -> bool:
                return False

            async def steer(self, text: str) -> bool:
                return False

            async def close(self) -> None:
                pass

        return cast(AgentSession, _Session())


def test_the_kind_is_published_and_typed_in_the_client() -> None:
    assert "session_gone" in ERROR_KINDS
    client = (ROOT / "clients" / "typescript" / "src" / "client.ts").read_text()
    union = re.search(r"export type ErrorKind =\n((?:\s*\|\s*\"[a-z_]+\"\n?)+)", client)
    assert union is not None
    typed = set(re.findall(r'"([a-z_]+)"', union.group(1)))
    assert set(ERROR_KINDS) <= typed, (
        f"kinds the TypeScript client cannot switch on: {set(ERROR_KINDS) - typed}"
    )


async def test_a_gone_session_answers_its_kind_with_both_ids(tmp_path: Path) -> None:
    host = ServeHost(
        Settings(root=tmp_path, mode="full", store=f"sqlite:///{tmp_path}/t.sqlite"),
        agent=GoneAfterOne(),
    )
    try:
        async with loopback(threads=host) as (client, _runtime):
            await client.initialize()
            started = await client.peer.call("thread/start", {"root": "", "mode": "", "name": ""})
            tid = started["thread_id"]
            first = await client.peer.call("turn/start", {"thread_id": tid, "text": "one"})
            assert first["turn"]["outcome"] == "completed" and first["turn"]["failure"] == ""

            with pytest.raises(RemoteError) as gone:
                await client.peer.call("turn/start", {"thread_id": tid, "text": "two"})
            assert gone.value.data == {
                "kind": "session_gone",
                "thread_id": tid,
                "session_id": "s-1",
            }

            resumed = await client.peer.call("thread/resume", {"thread_id": tid})
            last = resumed["turns"][-1]
            assert last["outcome"] == "failed" and last["failure"] == "session_gone"
    finally:
        await host.aclose()
