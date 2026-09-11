"""The studio is a reader of the record: its stream carries the run's events and the folded
steps, its `/say` takes a turn, `/answer` settles a live question, `/files` shows the workspace.

Driven with a stand-in conversation, so nothing here costs a turn; the page's JavaScript is
exercised by a person, and the endpoints it calls are exercised here.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from examples.studio.app import Studio, build_app

from shadow_hdk.kernel import Invoked, Observed, Started
from shadow_hdk.kernel.observations import Completed
from shadow_hdk.runtime.questions import Pending

pytestmark = pytest.mark.anyio


class Scripted:
    """A conversation that writes one file through 'its tools' and answers."""

    def __init__(self, studio: Studio) -> None:
        self.studio = studio
        self.provider = "scripted 0.0"

    async def turn(self, prompt: str) -> Any:
        s = self.studio
        s.on_event(Started(run_id="r", seq=1, at="t1", lease=None))  # type: ignore[arg-type]
        s.on_event(
            Invoked(run_id="r", seq=2, at="t2", step="w1", component="write_file", inputs={})
        )
        (s.root / "hello.txt").write_text("hello")
        s.on_event(
            Observed(
                run_id="r", seq=3, at="t3", step="w1", observation=Completed({"path": "hello.txt"})
            )
        )

        class Done:
            text = f"done: {prompt}"
            failed = False
            reasoning = ""

        return Done()


async def test_the_stream_carries_events_and_steps_and_the_turn_lands(tmp_path: Path) -> None:
    studio = Studio(root=tmp_path)
    studio.talk = Scripted(studio)
    app = build_app(studio)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://s") as c:
        assert (await c.post("/say", json={"text": "make hello"})).status_code == 200
        for _ in range(50):
            if any(line.get("kind") == "agent" for line in studio.record):
                break
            await asyncio.sleep(0.02)
        kinds = [line["kind"] for line in studio.record]
        assert kinds[0] == "you" and kinds[-1] == "agent"
        assert "event" in kinds, "the run's events are on the record the page reads"
        steps = [line for line in studio.record if line["kind"] == "step"]
        assert steps == [] or steps[0]["step"]["component"] == "write_file"
        files = (await c.get("/files")).json()["files"]
        assert [f["path"] for f in files] == ["hello.txt"]
        assert (await c.get("/file", params={"path": "hello.txt"})).json()["content"] == "hello"
        assert (await c.get("/file", params={"path": "../etc/passwd"})).status_code == 404


async def test_a_pending_question_reaches_the_page_and_the_answer_settles_it(
    tmp_path: Path,
) -> None:
    studio = Studio(root=tmp_path)
    app = build_app(studio)
    relay = asyncio.create_task(studio._relay_questions())  # noqa: SLF001 — the task `open()` starts
    try:
        asking = asyncio.create_task(
            studio.questions.ask(Pending(handle="h1", run_id="r", step="w1", question="write?"))
        )
        for _ in range(50):
            if any(line.get("kind") == "question" for line in studio.record):
                break
            await asyncio.sleep(0.02)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://s"
        ) as c:
            pending = (await c.get("/status")).json()["pending"]
            assert [p["handle"] for p in pending] == ["h1"]
            assert (await c.post("/answer", json={"handle": "h1", "allow": False})).json()["ok"]
            assert (await c.post("/answer", json={"handle": "h1", "allow": True})).json()[
                "ok"
            ] is False
        answer = await asyncio.wait_for(asking, 5)
        assert answer.kind == "refuse"
    finally:
        relay.cancel()


async def test_the_stream_replays_the_record_then_follows(tmp_path: Path) -> None:
    """httpx's ASGI transport buffers a whole response, so the SSE body is read as the iterator
    it is: the record first, then what arrives while watching."""
    from starlette.requests import Request

    studio = Studio(root=tmp_path)
    studio.note("you", text="earlier")
    app = build_app(studio)
    endpoint = next(r for r in app.routes if getattr(r, "path", "") == "/stream").endpoint  # type: ignore[attr-defined]
    response = await endpoint(
        Request({"type": "http", "method": "GET", "headers": [], "path": "/stream"})
    )
    body = response.body_iterator

    first = await anext(body)
    replayed = json.loads(first.decode().removeprefix("data: "))
    assert (replayed["kind"], replayed["text"]) == ("you", "earlier")
    studio.note("you", text="later")
    second = await asyncio.wait_for(anext(body), 5)
    live = json.loads(second.decode().removeprefix("data: "))
    assert (live["kind"], live["text"]) == ("you", "later")
    await body.aclose()
