"""A host-side component's activity crosses to where the record is (D63, principle 7).

`context.activity` on the host's side is a notification to the runtime's side — fire-and-forget,
because activity is never required for correctness — and lands on the observer the process
serving the runtime handed in, stamped with the step that was executing. Phase 26 puts it on the
wire's own stream for a host in another language; this is the crossing itself.
"""

from __future__ import annotations

import asyncio
from typing import Any

import anyio
from shadow_hdk.adapters.basic import AllowAll
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Activity,
    Binding,
    Ceiling,
    Completed,
    Composition,
    Event,
    Floor,
    Invoke,
    Lease,
    Observation,
)
from shadow_hdk.runtime import Ports, RunOptions, current_run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)
from shadow_hdk.wire.sides import loopback

TALKER = make_registration("talker")
PLAN = Composition((Invoke("s1", "talker", (Binding("brief", value="go"),)),))


class Hearing:
    def __init__(self) -> None:
        self.activity: list[Activity] = []
        self.events: list[Event] = []

    async def on(self, event: Event) -> None:
        self.events.append(event)

    async def on_activity(self, activity: Activity) -> None:
        self.activity.append(activity)


async def test_a_host_side_components_activity_lands_on_the_runtimes_observer() -> None:
    async def talks(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        await context.activity("thinking", "hm")
        await context.activity("text", "hello")
        return Completed("said")

    ports = Ports(
        model=None,
        components=(InMemoryComponents([(TALKER, talks)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    hearing = Hearing()
    options = RunOptions(lease=Lease(Ceiling(10, 60, None), Floor(0)), run_id="w")
    async with loopback(ports, observer=hearing) as (host, _runtime):
        await host.initialize()
        with anyio.fail_after(30):
            await host.run(PLAN, options)
        # a notification is fire-and-forget; give the runtime's observer pump a turn
        for _ in range(50):
            if len(hearing.activity) >= 2:
                break
            await asyncio.sleep(0.02)
        after: list[Any] = list(host.events)

    assert [(a.kind, a.text, a.step) for a in hearing.activity] == [
        ("thinking", "hm", "s1"),
        ("text", "hello", "s1"),
    ]
    assert not [e for e in after if isinstance(e, Activity)], "activity never becomes an event"
