"""H8: model cache counters survive aggregation, metering, persistence and the wire."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from shadow_hdk.adapters.agent import AgentComponent, ModelAgent, single
from shadow_hdk.adapters.basic import AllowAll, CallableComponents
from shadow_hdk.kernel import Binding, Ceiling, Composition, EffectProfile, Floor, Invoke, Lease
from shadow_hdk.kernel.events import Observed
from shadow_hdk.kernel.observations import Completed
from shadow_hdk.kernel.ports import ModelPort, ModelResponse, ToolCall, Usage
from shadow_hdk.kernel.threads import ThreadRecord
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel
from shadow_hdk.runtime.threads import InMemoryThreads, Thread
from shadow_hdk.wire.threads import ThreadMethods

pytestmark = pytest.mark.anyio

CASES = [
    (Usage(10, 2, 1, 11, 2), Usage(20, 3, 2, 13, 3), (24, 5)),
    (Usage(10, 2, 1, 0, 0), Usage(20, 3, 2, 0, 0), (0, 0)),
    (Usage(10, 2, 1, None, 2), Usage(20, 3, 2, 13, 3), (None, 5)),
    (Usage(10, 2, 1, 11, None), Usage(20, 3, 2, 13, 3), (24, None)),
    (None, Usage(20, 3, 2, 13, 3), (None, None)),
]


def setup(first: Usage | None, last: Usage) -> Ports:
    def ping() -> str:
        """A governed, counted step between model calls."""
        return "pong"

    tools = CallableComponents(registered_by="test", at="2026-01-01T00:00:00+00:00")
    tools.add(ping, effects=EffectProfile())
    return Ports(
        model=ScriptedModel(
            [
                ModelResponse("", (ToolCall("p", "ping", {}),), usage=first),
                ModelResponse("", (ToolCall("d", "done", {"summary": "finished"}),), usage=last),
            ]
        ),
        components=(tools,),
        governance=AllowAll(),
        clock=FixedClock(),
        sink=ListSink(),
    )


@pytest.mark.parametrize("first,last,cache", CASES)
async def test_component_usage_keeps_both_cache_axes(
    first: Usage | None, last: Usage, cache: tuple[int | None, int | None]
) -> None:
    ports = setup(first, last)
    agent = AgentComponent(pattern=single, effects=EffectProfile())
    ports = replace(ports, components=(*ports.components, agent))
    events = [
        e
        async for e in run(
            Composition(
                (Invoke("agent", agent.registration_id, (Binding(name="brief", value="go"),)),)
            ),
            ports,
            options=RunOptions(lease=Lease(Ceiling(40, 600, 1000), Floor(0))),
        )
    ]
    output = next(
        e.observation.output
        for e in reversed(events)
        if isinstance(e, Observed) and e.step == "agent" and isinstance(e.observation, Completed)
    )
    known = first is not None
    assert cast(dict[str, Any], output)["usage"] == {
        "input_tokens": 30 if known else None,
        "output_tokens": 5 if known else None,
        "cost_cents": 3 if known else None,
        "cache_read_tokens": cache[0],
        "cache_write_tokens": cache[1],
    }


@pytest.mark.parametrize("first,last,cache", CASES)
async def test_cache_usage_reaches_the_thread_record_and_wire(
    tmp_path: Path, first: Usage | None, last: Usage, cache: tuple[int | None, int | None]
) -> None:
    ports = setup(first, last)
    store = InMemoryThreads()
    thread = await Thread.open(
        agent=ModelAgent(model=cast(ModelPort, ports.model), pattern=single),
        ports=ports,
        store=store,
        root=tmp_path,
        lease=Lease(Ceiling(40, 600, 1000), Floor(0)),
    )
    notices: list[dict[str, Any]] = []

    async def notify(method: str, value: dict[str, Any]) -> None:
        if method == "event":
            notices.append(value["event"])

    peer = SimpleNamespace(serves=lambda *args: None, notify=notify)
    host = SimpleNamespace(threads=store, list=store.list)
    methods = ThreadMethods(peer, host, ports.clock)
    methods.threads[thread.id] = thread
    try:
        await methods._turn({"thread_id": thread.id, "text": "go"})
        wire = await methods._list({})
        kept = cast(ThreadRecord, await store.get(thread.id))
        usage = next(e["usage"] for e in notices if e["kind"] == "usage")
        actual = (
            (usage["cache_read_tokens"], usage["cache_write_tokens"]),
            (kept.spent.cache_read_tokens, kept.spent.cache_write_tokens),
            (
                wire["threads"][0]["spent"]["cache_read_tokens"],
                wire["threads"][0]["spent"]["cache_write_tokens"],
            ),
        )
        counted = (cache[0] or 0, cache[1] or 0)
        assert actual == (cache, counted, counted)
    finally:
        await thread.close()
