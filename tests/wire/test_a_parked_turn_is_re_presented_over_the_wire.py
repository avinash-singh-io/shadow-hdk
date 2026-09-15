"""A question the last host left is offered again over the wire (Phase 29 group 1, D80).

The runtime proved a parked turn survives the host; this is the same across the wire, the way a
page sees it: `thread/resume` answers with `pending` and pushes each question as an
`approval_request`, `approvals/pending` lists it beside any live one, and `approvals/answer`
settles it — the parked act runs from its checkpoint and its events go down the stream.
"""

from __future__ import annotations

import asyncio
import contextlib
import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import anyio
import pytest

from shadow_hdk.kernel import Ceiling, Completed, EffectProfile, Floor, Lease, ScopeSet, Turn
from shadow_hdk.kernel.ports import AgentSession, Allow, Ask, Context, Judgement, ToolSource
from shadow_hdk.runtime import Approvals, Ports
from shadow_hdk.runtime.testing import (
    AllowAuthorizer,
    FixedAuthority,
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)
from shadow_hdk.runtime.threads import Thread
from shadow_hdk.serve.stores import Stores, stores_for
from shadow_hdk.wire.sides import loopback

pytestmark = pytest.mark.anyio

WRITE = make_registration(
    "write_file", effects=EffectProfile(writes=ScopeSet.of("workspace"), reversible=False)
)


class AsksAboutWrites:
    async def judge(self, _effects: EffectProfile, context: Context) -> Judgement:
        if context.attributes.get("component") == "write_file":
            return Ask("may it write?")
        return Allow()


class Writes:
    def __init__(self) -> None:
        self.wrote: list[Any] = []

    async def __call__(self, inputs: Any) -> Any:
        self.wrote.append(inputs)
        return Completed({"wrote": True})


class Agent:
    def __init__(self, turns: list[tuple[list[tuple[str, dict[str, Any]]], str]]) -> None:
        self.turns = list(turns)
        self.prompts: list[str] = []
        self.reach: Any = None

    async def open(self, *, tools: tuple[ToolSource, ...] = (), **_: Any) -> AgentSession:
        agent = self

        class _Session:
            async def turn(self, prompt: str) -> Turn:
                agent.prompts.append(prompt)
                calls, line = agent.turns.pop(0)
                for name, arguments in calls:
                    await agent.reach(name, arguments)
                return Turn(text=line)

            async def close(self) -> None:
                pass

            async def stream(self, prompt: str) -> AsyncIterator[Any]:  # pragma: no cover
                raise NotImplementedError
                yield

        return cast(AgentSession, _Session())


class Host:
    """A `ThreadHost` over a sqlite url: what `ServeHost` is, without the shipped adapters."""

    def __init__(self, where: Path, agent: Agent, writes: Writes) -> None:
        self.stores: Stores = stores_for(f"sqlite:///{where}/live.sqlite")
        self.approvals = Approvals()
        self.store: Any = self.stores.store
        self.threads = self.stores.threads
        self.rules: Any = None
        self.modes: Any = None
        self.skills: Any = None
        self.agent = agent
        self.writes = writes
        self.where = where

    def _ports(self, observer: Any) -> Ports:
        return Ports(
            model=None,
            components=(InMemoryComponents([(WRITE, self.writes)]),),
            governance=AsksAboutWrites(),
            sink=ListSink(),
            clock=FixedClock(),
            observer=observer,
            authority=FixedAuthority(),
            authorizer=AllowAuthorizer(),
            effect_journal=self.stores.effects,
        )

    async def checkpointer(self) -> Any:
        return await self.stores.checkpointer()

    async def open(
        self, *, root: str, mode: str, want: Any, name: str, observer: Any, roots: Any = None
    ) -> Thread:
        thread = await Thread.open(
            agent=cast(Any, self.agent),
            ports=self._ports(observer),
            store=self.threads,
            root=root or str(self.where / "work"),
            lease=Lease(Ceiling(20, 600, None), Floor(0)),
            name=name,
            approvals=self.approvals,
            checkpointer=await self.checkpointer(),
            mode=mode,
            provider="scripted",
        )
        self.agent.reach = thread.registry.call
        return thread

    async def resume(self, thread_id: str, *, observer: Any) -> Thread:
        thread = await Thread.resume(
            thread_id,
            agent=cast(Any, self.agent),
            ports=self._ports(observer),
            store=self.threads,
            lease=Lease(Ceiling(20, 600, None), Floor(0)),
            approvals=self.approvals,
            checkpointer=await self.checkpointer(),
        )
        self.agent.reach = thread.registry.call
        return thread

    async def list(self) -> Any:
        return await self.threads.list()

    async def aclose(self) -> None:
        await self.stores.aclose()


async def _park_then_die(where: Path, image: Path) -> str:
    """Host A, over the wire: a turn asks — the question reaches the client as a notification,
    the way a page hears it — the store is imaged, the session is torn down."""
    host = Host(
        where, Agent([([("write_file", {"path": "a.txt", "content": "x"})], "ok")]), Writes()
    )
    thread_id = ""
    try:
        async with loopback(threads=host) as (client, _runtime):
            await client.initialize()
            asked = asyncio.Event()

            async def hearing(_params: dict[str, Any]) -> None:
                asked.set()

            client.peer.hears("approval_request", hearing)
            started = await client.peer.call(
                "thread/start", {"root": "", "mode": "ask", "name": "tools"}
            )
            thread_id = str(started["thread_id"])
            turning = asyncio.create_task(
                client.peer.call("turn/start", {"thread_id": thread_id, "text": "write a.txt"})
            )
            try:
                await asyncio.wait_for(asked.wait(), 30)
                await asyncio.sleep(0.05)
                shutil.copytree(where, image)
            finally:
                turning.cancel()
                with contextlib.suppress(BaseException):
                    await turning
    finally:
        await host.aclose()
    return thread_id


async def test_resume_offers_the_question_again_and_the_answer_settles_it(tmp_path: Path) -> None:
    thread_id = await _park_then_die(tmp_path / "a", tmp_path / "image")
    writes = Writes()
    agent = Agent([([], "carrying on")])
    host = Host(tmp_path / "image", agent, writes)
    heard: list[tuple[str, dict[str, Any]]] = []
    try:
        async with loopback(threads=host) as (client, _runtime):
            await client.initialize()

            async def keep(kind: str) -> Any:
                async def hearing(params: dict[str, Any]) -> None:
                    heard.append((kind, params))

                return hearing

            client.peer.hears("approval_request", await keep("approval_request"))
            client.peer.hears("event", await keep("event"))
            with anyio.fail_after(30):
                resumed = await client.peer.call("thread/resume", {"thread_id": thread_id})
                assert resumed["turns"][-1]["outcome"] == "parked"
                (question,) = resumed["pending"]
                assert question["component"] == "write_file" and question["turn"] == "turn-1"
                assert question["inputs"] == {"path": "a.txt", "content": "x"}
                await asyncio.sleep(0)  # the notification is on its way
                pushed = [p for k, p in heard if k == "approval_request"]
                assert pushed and pushed[0]["request"]["handle"] == question["handle"]
                assert pushed[0]["thread_id"] == thread_id

                listed = await client.peer.call("approvals/pending", {})
                assert [r["handle"] for r in listed["requests"]] == [question["handle"]]

                answered = await client.peer.call(
                    "approvals/answer",
                    {"handle": question["handle"], "answer": {"kind": "approve"}},
                )
                assert answered["answered"] is True
                kinds = [e["kind"] for e in answered["events"]]
                assert "observed" in kinds, kinds
                assert writes.wrote == [{"path": "a.txt", "content": "x"}]
                streamed = [p for k, p in heard if k == "event" and p["thread_id"] == thread_id]
                assert [p["event"]["kind"] for p in streamed].count("observed") == 1

                assert (await client.peer.call("approvals/pending", {}))["requests"] == []
                again = await client.peer.call(
                    "approvals/answer",
                    {"handle": question["handle"], "answer": {"kind": "approve"}},
                )
                assert again["answered"] is False, "settled once"

                done = await client.peer.call(
                    "turn/start", {"thread_id": thread_id, "text": "next"}
                )
                assert done["turn"]["outcome"] == "completed"
                assert "approved" in agent.prompts[-1] and agent.prompts[-1].endswith("next")
    finally:
        await host.aclose()


async def test_a_turn_parked_on_purpose_over_the_wire_is_settled_on_a_later_call(
    tmp_path: Path,
) -> None:
    """D88 across the wire: `turn/start {on_question: "park"}` returns `parked` at once; the
    question is on `approvals/pending`; `approvals/answer` settles it — the act runs from its
    checkpoint — and the next turn is told."""
    writes = Writes()
    agent = Agent(
        [([("write_file", {"path": "a.txt", "content": "x"})], "kept; stopping"), ([], "on")]
    )
    host = Host(tmp_path / "a", agent, writes)
    try:
        async with loopback(threads=host) as (client, _runtime):
            await client.initialize()
            started = await client.peer.call(
                "thread/start", {"root": "", "mode": "ask", "name": "tools"}
            )
            tid = str(started["thread_id"])
            with anyio.fail_after(30):
                done = await client.peer.call(
                    "turn/start", {"thread_id": tid, "text": "write", "on_question": "park"}
                )
                assert done["turn"]["outcome"] == "parked"
                assert writes.wrote == []
                listed = await client.peer.call("approvals/pending", {})
                (request,) = listed["requests"]
                assert request["component"] == "write_file" and request["turn"] == "turn-1"
                answered = await client.peer.call(
                    "approvals/answer", {"handle": request["handle"], "answer": {"kind": "approve"}}
                )
                assert answered["answered"] is True and "observed" in [
                    e["kind"] for e in answered["events"]
                ]
                assert writes.wrote == [{"path": "a.txt", "content": "x"}]
                nxt = await client.peer.call("turn/start", {"thread_id": tid, "text": "next"})
                assert nxt["turn"]["outcome"] == "completed"
                assert "approved" in agent.prompts[-1]
    finally:
        await host.aclose()


async def test_a_host_answers_park_live_and_settles_later(tmp_path: Path) -> None:
    """`approvals/answer {kind: "park"}` from a host that is there but cannot decide now."""
    writes = Writes()
    agent = Agent([([("write_file", {"path": "a.txt", "content": "x"})], "kept"), ([], "on")])
    host = Host(tmp_path / "a", agent, writes)
    try:
        async with loopback(threads=host) as (client, _runtime):
            await client.initialize()
            started = await client.peer.call(
                "thread/start", {"root": "", "mode": "ask", "name": "tools"}
            )
            tid = str(started["thread_id"])
            asked: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()

            async def hearing(params: dict[str, Any]) -> None:
                if not asked.done():
                    asked.set_result(params["request"])

            client.peer.hears("approval_request", hearing)
            with anyio.fail_after(30):
                turning = asyncio.create_task(
                    client.peer.call("turn/start", {"thread_id": tid, "text": "write"})
                )
                request = await asked
                parked = await client.peer.call(
                    "approvals/answer", {"handle": request["handle"], "answer": {"kind": "park"}}
                )
                assert parked["answered"] is True
                done = await turning
                assert done["turn"]["outcome"] == "parked"
                listed = await client.peer.call("approvals/pending", {})
                assert [r["handle"] for r in listed["requests"]] == [request["handle"]]
                settled = await client.peer.call(
                    "approvals/answer", {"handle": request["handle"], "answer": {"kind": "approve"}}
                )
                assert settled["answered"] is True and writes.wrote == [
                    {"path": "a.txt", "content": "x"}
                ]
    finally:
        await host.aclose()
