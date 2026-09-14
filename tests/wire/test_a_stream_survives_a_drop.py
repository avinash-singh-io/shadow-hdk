"""A stream that survives a drop (Phase 30 group 6, D94).

A page on a train, a phone in a lift: the SSE stream ends and the session used to end with it —
its threads closed, the turn in flight lost. Now every frame carries an `id`, a session
outlives its stream for a grace period keeping what it could not deliver, and `GET /rpc` with
the session header and `Last-Event-ID` reattaches and replays what the reconnect missed — the
turn that ran on while nobody listened arrives whole. LangGraph Server's `join`, Codex's
WebSocket reconnect; ours over plain SSE.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest

from shadow_hdk.adapters.environment import local_sandbox
from shadow_hdk.runtime.environment import Mode
from shadow_hdk.serve import ServeHost, Settings
from shadow_hdk.wire import served_over_http
from shadow_hdk.wire.protocol import PROTOCOL_VERSION
from shadow_hdk.wire.serve import SESSION_HEADER
from tests.serve.test_serve_answers_a_host_in_any_language import ScriptedProvider

pytestmark = pytest.mark.anyio

ENFORCEABLE: Mode = "workspace-write" if local_sandbox() is not None else "full"


class Stream:
    """One SSE connection, read frame by frame with its ids."""

    def __init__(self, http: httpx.AsyncClient, address: str, headers: dict[str, str]) -> None:
        self._context = http.stream("GET", f"{address}/rpc", headers=headers)
        self.response: httpx.Response | None = None
        self.session: str = ""
        self.frames: list[tuple[int | None, dict[str, Any]]] = []
        self._lines: Any = None

    async def __aenter__(self) -> Stream:
        self.response = await self._context.__aenter__()
        self.session = self.response.headers.get(SESSION_HEADER, "")
        self._lines = self.response.aiter_lines()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self._context.__aexit__(*exc)

    async def next_frame(self) -> tuple[int | None, dict[str, Any]]:
        """The next `data:` frame and the `id:` that came with it."""
        last_id: int | None = None
        async for line in self._lines:
            if line.startswith("id: "):
                last_id = int(line[4:])
            elif line.startswith("data: "):
                frame = (last_id, json.loads(line[6:]))
                self.frames.append(frame)
                return frame
        raise EOFError("the stream ended")


async def _call(
    http: httpx.AsyncClient,
    address: str,
    session: str,
    id_: int,
    method: str,
    params: dict[str, Any],
) -> None:
    posted = await http.post(
        f"{address}/rpc",
        headers={SESSION_HEADER: session, "content-type": "application/json"},
        json={"jsonrpc": "2.0", "id": id_, "method": method, "params": params},
    )
    assert posted.status_code == 202, posted.text


async def _reply(stream: Stream, id_: int) -> dict[str, Any]:
    while True:
        _fid, frame = await stream.next_frame()
        if frame.get("id") == id_:
            assert "error" not in frame, frame
            return dict(frame["result"])


async def test_frames_carry_ids_and_a_reconnect_replays_what_it_missed(tmp_path: Path) -> None:
    host = ServeHost(Settings(root=tmp_path, mode=ENFORCEABLE), agent=ScriptedProvider())
    try:
        with anyio.fail_after(60):
            async with served_over_http(threads=host, grace_seconds=5) as address:
                async with httpx.AsyncClient(timeout=30) as http:
                    async with Stream(http, address, {}) as first:
                        session = first.session
                        await _call(
                            http,
                            address,
                            session,
                            1,
                            "initialize",
                            {"protocol_version": PROTOCOL_VERSION},
                        )
                        await _reply(first, 1)
                        await _call(
                            http,
                            address,
                            session,
                            2,
                            "thread/start",
                            {"root": "", "mode": "", "name": ""},
                        )
                        started = await _reply(first, 2)
                        tid = started["thread_id"]
                        assert all(fid is not None for fid, _ in first.frames), (
                            "every frame has an id"
                        )
                        last_seen = first.frames[-1][0]
                        assert last_seen is not None
                    # The stream is gone; the session is not. A turn runs while nobody listens.
                    await _call(
                        http, address, session, 3, "turn/start", {"thread_id": tid, "text": "hello"}
                    )
                    await asyncio.sleep(0.5)
                    async with Stream(
                        http, address, {SESSION_HEADER: session, "Last-Event-ID": str(last_seen)}
                    ) as again:
                        assert again.session == session, "the same session, reattached"
                        result = await _reply(again, 3)
                        assert result["turn"]["text"] == "scripted: hello"
                        ids = [fid for fid, _ in again.frames if fid is not None]
                        assert len(ids) == len(again.frames), "every frame has an id"
                        assert ids and ids[0] == last_seen + 1, (
                            "replayed from the frame after the last seen"
                        )
                        assert ids == sorted(ids) and len(set(ids)) == len(ids), (
                            "in order, once each"
                        )
                        kinds = [
                            f.get("params", {}).get("event", {}).get("kind")
                            for _, f in again.frames
                        ]
                        assert "started" in kinds and "ended" in kinds, (
                            "the whole turn, missed and replayed"
                        )
    finally:
        await host.aclose()


async def test_a_session_past_its_grace_is_gone_and_its_threads_closed(tmp_path: Path) -> None:
    host = ServeHost(Settings(root=tmp_path, mode=ENFORCEABLE), agent=ScriptedProvider())
    try:
        with anyio.fail_after(60):
            async with served_over_http(threads=host, grace_seconds=0.3) as address:
                async with httpx.AsyncClient(timeout=30) as http:
                    async with Stream(http, address, {}) as first:
                        session = first.session
                        await _call(
                            http,
                            address,
                            session,
                            1,
                            "initialize",
                            {"protocol_version": PROTOCOL_VERSION},
                        )
                        await _reply(first, 1)
                        await _call(
                            http,
                            address,
                            session,
                            2,
                            "thread/start",
                            {"root": "", "mode": "", "name": ""},
                        )
                        started = await _reply(first, 2)
                    health = (await http.get(f"{address}/healthz")).json()
                    assert health["sessions"] == 1 and health["threads"] == 1, (
                        "kept through the grace"
                    )
                    await asyncio.sleep(0.8)
                    health = (await http.get(f"{address}/healthz")).json()
                    assert health["sessions"] == 0 and health["threads"] == 0, (
                        "gone, and its threads closed"
                    )
                    late = await http.get(f"{address}/rpc", headers={SESSION_HEADER: session})
                    assert late.status_code == 404
                    assert await host.threads.held_by(started["thread_id"]) is None, "let go"
    finally:
        await host.aclose()


async def test_a_second_stream_on_an_attached_session_is_refused(tmp_path: Path) -> None:
    host = ServeHost(Settings(root=tmp_path, mode=ENFORCEABLE), agent=ScriptedProvider())
    try:
        with anyio.fail_after(60):
            async with served_over_http(threads=host) as address:
                async with httpx.AsyncClient(timeout=30) as http:
                    async with Stream(http, address, {}) as first:
                        second = await http.get(
                            f"{address}/rpc", headers={SESSION_HEADER: first.session}
                        )
                        assert second.status_code == 409
    finally:
        await host.aclose()


async def test_an_idle_http_stream_gets_an_ephemeral_heartbeat(tmp_path: Path) -> None:
    host = ServeHost(Settings(root=tmp_path, mode=ENFORCEABLE), agent=ScriptedProvider())
    try:
        with anyio.fail_after(10):
            async with served_over_http(threads=host, heartbeat_seconds=0.02) as address:
                async with httpx.AsyncClient(timeout=5) as http:
                    async with http.stream("GET", f"{address}/rpc") as response:
                        lines = response.aiter_lines()
                        assert await anext(lines) == ": session open"
                        assert await anext(lines) == ""
                        assert await anext(lines) == ": heartbeat"
                        assert await anext(lines) == ""
    finally:
        await host.aclose()


async def test_a_reload_takes_its_thread_over_but_a_live_page_is_not_robbed(tmp_path: Path) -> None:
    """Two sessions of one process on one thread (D94): the thread of a session whose stream is
    gone is taken over by a `thread/resume` from another — a page reloaded; the thread of a
    session whose stream is attached is refused, naming the session — two pages cannot drive one
    thread."""
    host = ServeHost(Settings(root=tmp_path, mode=ENFORCEABLE), agent=ScriptedProvider())
    try:
        with anyio.fail_after(60):
            async with served_over_http(threads=host, grace_seconds=5) as address:
                async with httpx.AsyncClient(timeout=30) as http:
                    async with Stream(http, address, {}) as first:
                        await _call(
                            http,
                            address,
                            first.session,
                            1,
                            "initialize",
                            {"protocol_version": PROTOCOL_VERSION},
                        )
                        await _reply(first, 1)
                        await _call(
                            http,
                            address,
                            first.session,
                            2,
                            "thread/start",
                            {"root": "", "mode": "", "name": ""},
                        )
                        tid = (await _reply(first, 2))["thread_id"]
                        async with Stream(http, address, {}) as second:
                            await _call(
                                http,
                                address,
                                second.session,
                                1,
                                "initialize",
                                {"protocol_version": PROTOCOL_VERSION},
                            )
                            await _reply(second, 1)
                            await _call(
                                http,
                                address,
                                second.session,
                                2,
                                "thread/resume",
                                {"thread_id": tid},
                            )
                            while True:
                                _fid, frame = await second.next_frame()
                                if frame.get("id") == 2:
                                    break
                            assert frame["error"]["data"]["kind"] == "thread_held", frame
                            assert frame["error"]["data"]["holder"] == f"session {first.session}"
                    # The first page is gone; a reload resumes the thread and takes it over.
                    async with Stream(http, address, {}) as reload:
                        await _call(
                            http,
                            address,
                            reload.session,
                            1,
                            "initialize",
                            {"protocol_version": PROTOCOL_VERSION},
                        )
                        await _reply(reload, 1)
                        await _call(
                            http, address, reload.session, 2, "thread/resume", {"thread_id": tid}
                        )
                        resumed = await _reply(reload, 2)
                        assert resumed["thread_id"] == tid
                        sessions = (await http.get(f"{address}/healthz")).json()
                        assert sessions["threads"] == 1, "one thread open, in one session"
    finally:
        await host.aclose()
