"""The host's handles and the store cross the wire (D67): a host in any language sees and answers
approval and input requests, cancels, and reads and writes the store — live.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import anyio
import pytest

from shadow_hdk.kernel import ActRule, EffectProfile, ScopeSet
from shadow_hdk.kernel.ports import Ask, Context, Judgement
from shadow_hdk.wire.sides import loopback
from tests.wire.test_a_thread_crosses_the_wire import ScriptedThreads, _keeper

pytestmark = pytest.mark.anyio


class AsksAboutLook:
    """A policy that asks before `look` — so a turn over the wire raises an approval request."""

    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        from shadow_hdk.kernel.ports import Allow

        if context.attributes.get("component") == "look":
            return Ask("may it look?")
        return Allow()


class AskingThreads(ScriptedThreads):
    def _ports(self, observer: Any) -> Any:
        from dataclasses import replace

        from shadow_hdk.adapters.modes import ActRules

        self.rules = getattr(self, "rules", None) or ActRules()
        base = super()._ports(observer)
        return replace(base, governance=AsksAboutLook())

    async def open(self, **kw: Any) -> Any:
        thread = await super().open(**kw)
        thread._rules = self.rules  # noqa: SLF001 — the double's registry, as serve would wire it
        return thread


async def test_an_approval_request_is_seen_and_answered_over_the_wire(tmp_path: Path) -> None:
    heard: list[tuple[str, dict[str, Any]]] = []
    threads = AskingThreads(tmp_path)
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        host.peer.hears("approval_request", _keeper(heard, "approval_request"))
        started = await host.peer.call(
            "thread/start", {"root": str(tmp_path), "mode": "workspace-write"}
        )
        tid = started["thread_id"]

        async def answer_when_asked() -> None:
            for _ in range(200):
                pending = await host.peer.call("approvals/pending", {})
                if pending["requests"]:
                    request = pending["requests"][0]
                    assert request["component"] == "look" and request["kind"] == "approval"
                    await host.peer.call(
                        "approvals/answer",
                        {"handle": request["handle"], "answer": {"kind": "approve"}},
                    )
                    return
                await asyncio.sleep(0.02)
            raise AssertionError("nothing was ever pending")

        answering = asyncio.create_task(answer_when_asked())
        with anyio.fail_after(30):
            done = await host.peer.call("turn/start", {"thread_id": tid, "text": "look"})
        await answering

    assert done["turn"]["outcome"] == "completed"
    notified = [p for k, p in heard if k == "approval_request"]
    assert notified and notified[0]["request"]["question"] == "may it look?"
    assert notified[0]["thread_id"] == tid


async def test_approve_and_add_rule_over_the_wire_keeps_the_rule(tmp_path: Path) -> None:
    threads = AskingThreads(tmp_path)
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        started = await host.peer.call(
            "thread/start", {"root": str(tmp_path), "mode": "workspace-write"}
        )
        tid = started["thread_id"]

        async def answer_with_a_rule() -> None:
            for _ in range(200):
                pending = await host.peer.call("approvals/pending", {})
                if pending["requests"]:
                    await host.peer.call(
                        "approvals/answer",
                        {
                            "handle": pending["requests"][0]["handle"],
                            "answer": {
                                "kind": "approve_and_add_rule",
                                "rule": {"component": "look", "inputs": {}},
                            },
                        },
                    )
                    return
                await asyncio.sleep(0.02)

        task = asyncio.create_task(answer_with_a_rule())
        with anyio.fail_after(30):
            await host.peer.call("turn/start", {"thread_id": tid, "text": "look"})
        await task
        rules = await host.peer.call("rules/list", {})

    assert rules["rules"] == [
        {
            "component": "look",
            "inputs": {},
            "decision": "allow",
            "mode": "",
            "note": "",
            "scope": "",
        }
    ]
    assert threads.rules is not None
    assert threads.rules.all() == (ActRule(component="look"),)


async def test_a_deny_over_the_wire_refuses_and_says_why(tmp_path: Path) -> None:
    heard: list[tuple[str, dict[str, Any]]] = []
    threads = AskingThreads(tmp_path)
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        host.peer.hears("event", _keeper(heard, "event"))
        started = await host.peer.call(
            "thread/start", {"root": str(tmp_path), "mode": "workspace-write"}
        )
        tid = started["thread_id"]

        async def deny() -> None:
            for _ in range(200):
                pending = await host.peer.call("approvals/pending", {})
                if pending["requests"]:
                    await host.peer.call(
                        "approvals/answer",
                        {
                            "handle": pending["requests"][0]["handle"],
                            "answer": {"kind": "deny", "reason": "not today"},
                        },
                    )
                    return
                await asyncio.sleep(0.02)

        task = asyncio.create_task(deny())
        with anyio.fail_after(30):
            await host.peer.call("turn/start", {"thread_id": tid, "text": "look"})
        await task

    # A denial that came back to a parked child on resume is the step's *observation* (D38); a
    # policy's own refusal at judgement time is the `refused` event. Either way the reason is
    # the person's words.
    reasons = [
        p["event"].get("reason") or (p["event"].get("observation") or {}).get("reason", "")
        for k, p in heard
        if k == "event"
        and (
            p["event"]["kind"] == "refused"
            or (p["event"].get("observation") or {}).get("kind") == "refused"
        )
    ]
    assert any("not today" in r for r in reasons), reasons


class AskingPersonThreads(ScriptedThreads):
    """A provider that asks the person through `ask_person` before it answers."""

    def _ports(self, observer: Any) -> Any:
        from dataclasses import replace

        from shadow_hdk.runtime.person import person_components

        base = super()._ports(observer)
        return replace(base, components=(*base.components, person_components()))

    def __init__(self, tmp_path: Path) -> None:
        super().__init__(tmp_path)
        agent = self.agent

        async def open(*, tools: Any = (), workspace: Any = None, behaviour: Any = None) -> Any:
            from shadow_hdk.kernel import Turn

            class _Session:
                async def turn(self, prompt: str) -> Turn:
                    answered = await agent.reach("ask_person", {"question": "which colour?"})
                    colour = answered.output["answer"] if hasattr(answered, "output") else "?"
                    return Turn(text="painted it " + colour)

                async def close(self) -> None:
                    pass

            return _Session()

        agent.open = open  # type: ignore[method-assign]


async def test_an_input_request_is_pushed_as_its_own_kind_and_answered_with_text(
    tmp_path: Path,
) -> None:
    heard: list[tuple[str, dict[str, Any]]] = []
    threads = AskingPersonThreads(tmp_path)
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        host.peer.hears("input_request", _keeper(heard, "input_request"))
        host.peer.hears("approval_request", _keeper(heard, "approval_request"))
        started = await host.peer.call(
            "thread/start", {"root": str(tmp_path), "mode": "workspace-write"}
        )
        tid = started["thread_id"]

        async def answer_in_words() -> None:
            for _ in range(200):
                pending = await host.peer.call("approvals/pending", {})
                if pending["requests"]:
                    request = pending["requests"][0]
                    assert request["kind"] == "input"
                    await host.peer.call(
                        "approvals/answer",
                        {"handle": request["handle"], "answer": {"text": "teal"}},
                    )
                    return
                await asyncio.sleep(0.02)

        task = asyncio.create_task(answer_in_words())
        with anyio.fail_after(30):
            done = await host.peer.call("turn/start", {"thread_id": tid, "text": "paint"})
        await task

    assert done["turn"]["text"] == "painted it teal"
    assert [k for k, _ in heard] == ["input_request"], "pushed as an input request, not an approval"
    assert heard[0][1]["request"]["question"] == "which colour?"


async def test_the_store_crosses_and_a_crossed_row_is_live(tmp_path: Path) -> None:
    from shadow_hdk.adapters.modes import ModeRegistry, shipped_modes, store_modes

    threads = ScriptedThreads(tmp_path)
    threads.modes = ModeRegistry(shipped_modes(), sources=(store_modes(threads.store),))
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        assert await host.peer.call("store/version", {"collection": "modes"}) == {"version": 0}
        await host.peer.call(
            "store/put",
            {
                "collection": "modes",
                "key": "calm",
                "row": {"id": "calm", "name": "Calm", "policy": "read-only"},
            },
        )
        assert await host.peer.call("store/version", {"collection": "modes"}) == {"version": 1}
        got = await host.peer.call("store/get", {"collection": "modes", "key": "calm"})
        assert got["row"]["name"] == "Calm"
        listed = await host.peer.call("store/list", {"collection": "modes"})
        assert [k for k, _ in listed["rows"]] == ["calm"]

        modes = await host.peer.call("modes/list", {})
        assert "calm" in [m["id"] for m in modes["modes"]], (
            "a crossed row is a mode at the next read"
        )

        await host.peer.call("store/delete", {"collection": "modes", "key": "calm"})
        assert (await host.peer.call("store/list", {"collection": "modes"}))["rows"] == []


async def test_without_a_store_the_methods_say_so(tmp_path: Path) -> None:
    threads = ScriptedThreads(tmp_path)
    threads.store = None
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        with pytest.raises(Exception, match="no store"):
            await host.peer.call("store/list", {"collection": "modes"})


async def test_cancel_over_the_wire_stops_the_thread(tmp_path: Path) -> None:
    threads = ScriptedThreads(tmp_path)
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        started = await host.peer.call(
            "thread/start", {"root": str(tmp_path), "mode": "workspace-write"}
        )
        stopped = await host.peer.call("run/cancel", {"thread_id": started["thread_id"]})
        assert stopped["cancelled"] is False, "nothing was running"


def test_the_scope_set_is_serialisable_for_the_rule_row() -> None:
    assert ScopeSet.of("workspace").names == frozenset({"workspace"})
