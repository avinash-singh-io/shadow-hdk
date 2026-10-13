"""Generic execution resources close on success, parking, failure and cancellation."""

import asyncio
from typing import Any

import pytest

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Component,
    Composition,
    EffectProfile,
    Floor,
    Interface,
    Invoke,
    Lease,
    Provenance,
    Registration,
)
from shadow_hdk.runtime import Ports, RunOptions, current_run, run
from shadow_hdk.runtime.testing import FixedClock, ListSink


class Managed:
    def __init__(self, *, fail: bool = False, wait: bool = False) -> None:
        self.fail = fail
        self.wait = wait
        self.closing = asyncio.Event()
        self.finish = asyncio.Event()
        self.closed: list[str] = []

    async def registrations(self) -> list[Registration]:
        return [
            Registration(
                "held",
                Component(
                    Interface("held", "held"), EffectProfile(), Provenance("test", "test", "")
                ),
            )
        ]

    async def invoke(self, registration: str, inputs: Any) -> Completed:
        return Completed("held")

    async def release_run(self, resource_scope: str) -> None:
        self.closing.set()
        if self.wait:
            await self.finish.wait()
        self.closed.append(resource_scope)
        if self.fail:
            raise RuntimeError("cleanup sentinel")


async def collect(port: Managed) -> list[Any]:
    ports = Ports(components=(port,), governance=AllowAll(), sink=ListSink(), clock=FixedClock())
    return [
        e
        async for e in run(
            Composition((Invoke("one", "held"),)),
            ports,
            options=RunOptions(lease=Lease(Ceiling(10, 3600, 100), Floor(0))),
        )
    ]


async def test_a_cleanup_failure_is_a_failed_run_with_its_reason() -> None:
    port = Managed(fail=True)
    events = await collect(port)
    assert (events[-1].reason, events[-1].detail, port.closed) == (
        "failed",
        "resource cleanup failed: RuntimeError: cleanup sentinel",
        [events[0].run_id],
    )


async def test_cancellation_during_cleanup_waits_for_the_resource_to_close() -> None:
    port = Managed(wait=True)
    collecting = asyncio.create_task(collect(port))
    await asyncio.wait_for(port.closing.wait(), 2)
    collecting.cancel()
    await asyncio.sleep(0)
    port.finish.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(collecting, 2)
    assert (len(port.closed), current_run()) == (1, None)
