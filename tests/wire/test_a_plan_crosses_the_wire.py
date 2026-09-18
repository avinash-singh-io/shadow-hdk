"""Phase 36 G7: the plan crosses the wire (D107–D116) for a host in any language.

`thread/start` takes `plan_limits`; `modes/list` says each mode's `plan`; `plan_admitted` and
`plan_refused` go down the stream like every other event; `thread/amend` hands the runtime a
different composition for a parked plan, admitted before it is taken.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import anyio
import pytest

from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec
from shadow_hdk.kernel import (
    Allow,
    Ask,
    Ceiling,
    Completed,
    Context,
    EffectProfile,
    Floor,
    Judgement,
    Lease,
    PlanLimits,
    ScopeSet,
)
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.checkpoints import InMemoryRunStore, saver_over
from shadow_hdk.runtime.planning import plan_components
from shadow_hdk.runtime.testing import InMemoryComponents, ListSink, make_registration
from shadow_hdk.runtime.threads import Thread
from shadow_hdk.testing import ScriptedAgent
from shadow_hdk.wire.sides import loopback

from .test_a_thread_crosses_the_wire import ScriptedThreads, _keeper, _OwnIds

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
LOOK = make_registration("look", effects=EffectProfile(reads=WORKSPACE))
WIPE = make_registration("wipe", effects=EffectProfile(writes=WORKSPACE))
wiped: list[Any] = []


async def look(_inputs: Any) -> Any:
    return Completed({"found": True})


async def wipe(inputs: Any) -> Any:
    wiped.append(inputs)
    return Completed({"wiped": True})


class AskBeforeWorkspaceWrites:
    async def judge(self, effects: EffectProfile, _context: Context) -> Judgement:
        if "workspace" in effects.writes.names or effects.writes.everything:
            return Ask("a write — a person decides")
        return Allow()


def invoke(step_id: str, component: str) -> dict[str, Any]:
    return {"kind": "invoke", "id": step_id, "component": component, "inputs": []}


class PlanningThreads(ScriptedThreads):
    """The scripted host with `compose` offered, a write the policy asks about, a checkpointer
    and a mode registry whose modes carry plan limits."""

    def __init__(self, tmp_path: Path) -> None:
        super().__init__(tmp_path)
        self.agent: Any = ScriptedAgent([])  # the kit's own: scripted calls, then a line
        self.modes = ModeRegistry(
            (
                ModeSpec.of("narrow", plan=PlanLimits(depth=2, fan_out=1, steps=8)),
                ModeSpec.of("wide", plan=PlanLimits(depth=4, fan_out=8, steps=64)),
            )
        )
        self.plan_limits_seen: list[PlanLimits | None] = []

    def _ports(self, observer: Any) -> Ports:
        return Ports(
            model=None,
            components=(InMemoryComponents([(LOOK, look), (WIPE, wipe)]), plan_components()),
            governance=AskBeforeWorkspaceWrites(),
            sink=ListSink(),
            clock=_OwnIds(),
            observer=observer,
        )

    async def open(
        self,
        *,
        root: str,
        mode: str,
        want: str | None,
        name: str,
        observer: Any,
        roots: Any = None,
        plan_limits: Any = None,
    ) -> Thread:
        limits = PlanLimits(**plan_limits) if isinstance(plan_limits, dict) else plan_limits
        self.plan_limits_seen.append(limits)
        thread = await Thread.open(
            agent=cast(Any, self.agent),
            ports=self._ports(observer),
            store=self.threads,
            root=root or str(self._tmp),
            lease=Lease(Ceiling(60, 600, None), Floor(0)),
            name=name,
            approvals=self.approvals,
            checkpointer=saver_over(InMemoryRunStore()),
            mode=mode,
            modes=self.modes,
            provider="scripted",
            plan_limits=limits,
        )
        self.agent.reach = thread.registry.call
        return thread


async def test_modes_list_says_each_modes_plan_limits(tmp_path: Path) -> None:
    async with loopback(threads=PlanningThreads(tmp_path)) as (host, _runtime):
        await host.initialize()
        listed = await host.peer.call("modes/list", {})
        by_id = {m["id"]: m for m in listed["modes"]}
        assert by_id["narrow"]["plan"] == {"depth": 2, "fan_out": 1, "steps": 8}
        assert by_id["wide"]["plan"] == {"depth": 4, "fan_out": 8, "steps": 64}


async def test_thread_start_takes_the_hosts_plan_limits(tmp_path: Path) -> None:
    threads = PlanningThreads(tmp_path)
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        started = await host.peer.call(
            "thread/start",
            {"root": str(tmp_path), "mode": "wide", "plan_limits": {"fan_out": 2}},
        )
        assert threads.plan_limits_seen == [PlanLimits(fan_out=2)]
        assert started["plan_limits"] == {"depth": 4, "fan_out": 2, "steps": 64}, (
            "the host's met with the mode's — what the next plan is admitted under"
        )


async def test_plan_events_go_down_the_stream_and_thread_amend_is_admitted(
    tmp_path: Path,
) -> None:
    wiped.clear()
    threads = PlanningThreads(tmp_path)
    threads.agent.turns.append(
        ([("compose", {"steps": [invoke("a", "look"), invoke("w", "wipe")]})], "planned")
    )
    heard: list[tuple[str, dict[str, Any]]] = []
    async with loopback(threads=threads) as (host, _runtime):
        await host.initialize()
        host.peer.hears("event", _keeper(heard, "event"))
        started = await host.peer.call("thread/start", {"root": str(tmp_path), "mode": "wide"})
        thread_id = started["thread_id"]
        with anyio.fail_after(30):
            turned = await host.peer.call(
                "turn/start", {"thread_id": thread_id, "text": "plan it", "on_question": "park"}
            )
        assert turned["turn"]["outcome"] == "parked"
        kinds = [p["event"]["kind"] for _, p in heard]
        assert "plan_admitted" in kinds, "the admission crossed as an event"
        admissions = [p["event"] for _, p in heard if p["event"]["kind"] == "plan_admitted"]
        assert len(admissions) == 2, "the one-call plan for `compose`, then the proposed plan"
        proposed = admissions[-1]
        assert proposed["limits"] == {"depth": 4, "fan_out": 8, "steps": 64}
        assert proposed["asks"] == ["w"], "the write named at admission"

        pending = await host.peer.call("approvals/pending", {"thread_id": thread_id})
        [question] = pending["requests"]
        assert question["component"] == "compose"

        # Too wide for the mode: refused, and the refusal crosses as an event on the result.
        refused = await host.peer.call(
            "thread/amend",
            {
                "thread_id": thread_id,
                "handle": question["handle"],
                "composition": {
                    "steps": [
                        {
                            "kind": "fan_out",
                            "id": "f",
                            "steps": [invoke(f"x{i}", "look") for i in range(9)],
                        }
                    ]
                },
                "answer": {"kind": "approve"},
            },
        )
        assert refused["admitted"] is False
        assert [m["axis"] for m in refused["mismatches"]] == ["fan_out"]
        assert any(e["kind"] == "plan_refused" and e["amendment"] for e in refused["events"])
        still = await host.peer.call("approvals/pending", {"thread_id": thread_id})
        assert len(still["requests"]) == 1, "the question stays open"
        assert wiped == []

        # A shape the mode admits: the plan continues where it parked, then the new step.
        amended = await host.peer.call(
            "thread/amend",
            {
                "thread_id": thread_id,
                "handle": question["handle"],
                "composition": {
                    "steps": [invoke("a", "look"), invoke("w", "wipe"), invoke("after", "look")]
                },
                "answer": {"kind": "approve"},
            },
        )
        assert amended["admitted"] is True
        assert any(e["kind"] == "plan_admitted" and e["amendment"] for e in amended["events"])
        ran = [e["step"] for e in amended["events"] if e["kind"] == "invoked"]
        assert ran[-2:] == ["w", "after"]
        assert wiped == [{}]
        settled = await host.peer.call("approvals/pending", {"thread_id": thread_id})
        assert settled["requests"] == []
        await host.peer.call("thread/close", {"thread_id": thread_id})
