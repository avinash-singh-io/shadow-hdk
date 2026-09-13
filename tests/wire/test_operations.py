"""Operations (Phase 29 group 7, D86): what a hosted process owes whoever runs it.

`GET /healthz` answers without a bearer — a load balancer's question, not a person's: ok, the
kit's version, how many sessions and threads are open. `initialize` says the kit's version
beside the protocol's. `admin/sessions` and `admin/threads` list what the process holds, for the
operator behind the bearer. And the per-run token the wire owed since BUG-006 is closed as a
decision, not built: one app server behind every surface authenticates its people itself.
"""

from __future__ import annotations

from pathlib import Path

import anyio
import httpx
import pytest

from shadow_hdk import __version__
from shadow_hdk.adapters.environment import local_sandbox
from shadow_hdk.runtime.environment import Mode
from shadow_hdk.serve import ServeHost, Settings
from shadow_hdk.wire import connect_to, served_over_http
from shadow_hdk.wire.protocol import PROTOCOL_VERSION
from shadow_hdk.wire.sides import loopback
from tests.serve.test_serve_answers_a_host_in_any_language import ScriptedProvider, _ports

pytestmark = pytest.mark.anyio

ENFORCEABLE: Mode = "workspace-write" if local_sandbox() is not None else "full"


async def test_healthz_answers_without_a_bearer_and_counts_what_is_open(tmp_path: Path) -> None:
    host = ServeHost(Settings(root=tmp_path, mode=ENFORCEABLE), agent=ScriptedProvider())
    try:
        with anyio.fail_after(60):
            async with served_over_http(threads=host, token="a-test-token") as address:
                async with httpx.AsyncClient() as http:
                    health = await http.get(f"{address}/healthz")
                    assert health.status_code == 200
                    body = health.json()
                    assert body["ok"] is True and body["version"] == __version__
                    assert body["sessions"] == 0 and body["threads"] == 0
                    assert (await http.get(f"{address}/rpc")).status_code == 401, (
                        "the rest needs it"
                    )
    finally:
        await host.aclose()


async def test_initialize_says_the_kits_version_beside_the_protocols() -> None:
    async with loopback() as (client, _runtime):
        answered = await client.peer.call("initialize", {"protocol_version": PROTOCOL_VERSION})
    assert answered == {"protocol_version": PROTOCOL_VERSION, "version": __version__}


async def test_admin_lists_the_sessions_and_the_threads_the_process_holds(tmp_path: Path) -> None:
    host = ServeHost(Settings(root=tmp_path, mode=ENFORCEABLE), agent=ScriptedProvider())
    try:
        with anyio.fail_after(60):
            async with served_over_http(threads=host) as address:
                async with (
                    connect_to(address, _ports()) as one,
                    connect_to(address, _ports()) as two,
                ):
                    await one.initialize()
                    await two.initialize()
                    started = await one.peer.call(
                        "thread/start", {"root": "", "mode": "", "name": "", "principal": "alice"}
                    )
                    tid = started["thread_id"]

                    sessions = await two.peer.call("admin/sessions", {})
                    assert len(sessions["sessions"]) == 2
                    (holding,) = [s for s in sessions["sessions"] if s["threads"]]
                    assert holding["id"] == one.session_id and holding["threads"] == [tid]
                    assert all(s["opened_at"] for s in sessions["sessions"])

                    threads = await two.peer.call("admin/threads", {})
                    (row,) = [t for t in threads["threads"] if t["id"] == tid]
                    assert row["held_by"] == host.holder
                    assert row["session"] == one.session_id
                    assert row["principal"] == "alice"
                    assert row["turns"] == 0

                    async with httpx.AsyncClient() as http:
                        body = (await http.get(f"{address}/healthz")).json()
                        assert body["sessions"] == 2 and body["threads"] == 1

                    await one.peer.call("thread/close", {"thread_id": tid})
                    threads = await two.peer.call("admin/threads", {})
                    (row,) = [t for t in threads["threads"] if t["id"] == tid]
                    assert row["held_by"] is None and row["session"] is None
    finally:
        await host.aclose()


async def test_admin_over_a_loopback_without_an_app_answers_its_one_session() -> None:
    """`--stdio` has one session and no app around it: admin still answers, with that one."""
    async with loopback() as (client, _runtime):
        await client.initialize()
        sessions = await client.peer.call("admin/sessions", {})
        assert len(sessions["sessions"]) == 1
        threads = await client.peer.call("admin/threads", {})
        assert threads["threads"] == []
