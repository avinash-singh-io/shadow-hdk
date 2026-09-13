"""The budget on the record, over the wire (Phase 29 group 5, D84; ENH-013).

`thread/start {budget: {steps, seconds, cents}}` opens a thread on its own budget; a thread's
row says what it was given and what it spent; `thread/remaining` is the difference, and stays
so after `thread/close` and `thread/resume` — the page reload that used to reset it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.adapters.environment import local_sandbox
from shadow_hdk.runtime.environment import Mode
from shadow_hdk.serve import ServeHost, Settings
from shadow_hdk.wire.peer import RemoteError
from shadow_hdk.wire.sides import loopback
from tests.serve.test_serve_answers_a_host_in_any_language import ScriptedProvider

pytestmark = pytest.mark.anyio

ENFORCEABLE: Mode = "workspace-write" if local_sandbox() is not None else "full"


async def test_a_thread_on_its_own_budget_keeps_what_it_spent_across_a_resume(
    tmp_path: Path,
) -> None:
    host = ServeHost(
        Settings(root=tmp_path, mode=ENFORCEABLE, store=f"sqlite:///{tmp_path}/live.sqlite"),
        agent=ScriptedProvider(),
    )
    try:
        async with loopback(threads=host) as (client, _runtime):
            await client.initialize()
            started = await client.peer.call(
                "thread/start",
                {"root": "", "mode": "", "name": "", "budget": {"steps": 5, "cents": 50}},
            )
            tid = started["thread_id"]
            remaining = await client.peer.call("thread/remaining", {"thread_id": tid})
            assert remaining["lease"]["ceiling"]["max_steps"] == 5
            assert remaining["lease"]["ceiling"]["max_cost_cents"] == 50
            # The clock runs from the open: the file's hour, less the moments since.
            assert 3590 < remaining["lease"]["ceiling"]["max_wall_seconds"] <= 3600

            await client.peer.call("turn/start", {"thread_id": tid, "text": "hello"})
            after = await client.peer.call("thread/remaining", {"thread_id": tid})
            left = after["lease"]["ceiling"]["max_steps"]
            assert left < 5
            listed = await client.peer.call("thread/list", {})
            (row,) = [t for t in listed["threads"] if t["id"] == tid]
            assert row["budget"] == {"max_steps": 5, "max_wall_seconds": 3600, "max_cost_cents": 50}
            assert row["spent"]["steps"] == 5 - left

            await client.peer.call("thread/close", {"thread_id": tid})
            await client.peer.call("thread/resume", {"thread_id": tid})
            again = await client.peer.call("thread/remaining", {"thread_id": tid})
            assert again["lease"]["ceiling"]["max_steps"] == left, "not a fresh meter (ENH-013)"

            with pytest.raises(RemoteError, match="whole number"):
                await client.peer.call(
                    "thread/start",
                    {"root": "", "mode": "", "name": "", "budget": {"steps": "many"}},
                )
            plain = await client.peer.call("thread/start", {"root": "", "mode": "", "name": ""})
            listed = await client.peer.call("thread/list", {})
            (row,) = [t for t in listed["threads"] if t["id"] == plain["thread_id"]]
            assert row["budget"] is None, "the host's default is not repeated on the record"
    finally:
        await host.aclose()
