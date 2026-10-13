"""Resources outlive approval pauses and close with their execution owner."""

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


async def test_a_park_keeps_the_resource_until_the_resumed_run_ends() -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    from shadow_hdk.kernel.observations import ApprovalRequest
    from shadow_hdk.kernel.ports import Allow
    from shadow_hdk.runtime import resume

    class Asking(Managed):
        async def invoke(self, registration: str, inputs: Any) -> Any:
            context = current_run()
            assert context is not None
            if await context.resumed() is None:
                return ApprovalRequest(question="continue?", handle="approval")
            return Completed({"closed_before_resume": list(self.closed)})

    port = Asking()
    ports = Ports(components=(port,), governance=AllowAll(), sink=ListSink(), clock=FixedClock())
    options = RunOptions(
        lease=Lease(Ceiling(10, 3600, 100), Floor(0)),
        run_id="parked-resource",
        checkpointer=InMemorySaver(),
    )
    plan = Composition((Invoke("one", "held"),))
    first = [e async for e in run(plan, ports, options=options)]
    assert (port.closed, [e.kind for e in first if e.kind == "ended"]) == ([], [])
    after = [e async for e in resume(plan, Allow(), ports, options=options)]
    assert ([e.observation for e in after if e.kind == "observed"], port.closed) == (
        [Completed({"closed_before_resume": []})],
        ["parked-resource"],
    )


async def test_a_thread_owns_one_scope_across_turns_and_closes_it_once(tmp_path: Any) -> None:
    from typing import cast

    from shadow_hdk.runtime.threads import InMemoryThreads, Thread
    from tests.adapters.browser.test_images_reach_the_model_and_wire import Picture
    from tests.runtime.test_a_conversation_without_a_record import Agent

    port = Picture()
    agent = Agent([([("picture", {})], "first"), ([("picture", {})], "second")])
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=Ports(
            components=(port, port), governance=AllowAll(), sink=ListSink(), clock=FixedClock()
        ),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
    )
    agent.reach = thread.registry.call
    try:
        [e async for e in thread.turn("first")]
        assert port.released == [], "the conversation still owns its resources"
        [e async for e in thread.turn("second")]
        assert (port.scopes, port.released) == ([thread.id, thread.id], [])
    finally:
        await thread.close()
    await thread.close()
    assert port.released == [thread.id], "aliases and repeated close must not duplicate teardown"


async def test_cancelling_thread_close_releases_resources_and_the_store_hold(tmp_path: Any) -> None:
    from typing import cast

    from shadow_hdk.runtime.threads import InMemoryThreads, Thread
    from tests.runtime.test_a_conversation_without_a_record import Agent

    port = Managed(wait=True)
    store = InMemoryThreads()
    thread = await Thread.open(
        agent=cast(Any, Agent([])),
        ports=Ports(components=(port,), governance=AllowAll(), sink=ListSink(), clock=FixedClock()),
        store=store,
        root=tmp_path,
        holder="owner",
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
    )
    closing = asyncio.create_task(thread.close())
    await asyncio.wait_for(port.closing.wait(), 2)
    closing.cancel()
    await asyncio.sleep(0)
    port.finish.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(closing, 2)
    assert (port.closed, thread.conversation.closed, await store.held_by(thread.id)) == (
        [thread.id],
        True,
        None,
    )


async def test_a_thread_cleanup_failure_releases_the_hold_and_tries_every_port(
    tmp_path: Any,
) -> None:
    from typing import cast

    from shadow_hdk.runtime.threads import InMemoryThreads, Thread
    from tests.runtime.test_a_conversation_without_a_record import Agent

    first, broken = Managed(), Managed(fail=True)
    store = InMemoryThreads()
    thread = await Thread.open(
        agent=cast(Any, Agent([])),
        ports=Ports(
            components=(first, broken), governance=AllowAll(), sink=ListSink(), clock=FixedClock()
        ),
        store=store,
        root=tmp_path,
        holder="owner",
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
    )
    with pytest.raises(
        RuntimeError, match="resource cleanup failed: RuntimeError: cleanup sentinel"
    ):
        await thread.close()
    assert (first.closed, broken.closed, await store.held_by(thread.id)) == (
        [thread.id],
        [thread.id],
        None,
    )


async def test_repeated_cancellation_waits_for_the_thread_hold_to_release(tmp_path: Any) -> None:
    from typing import cast

    from shadow_hdk.runtime.threads import InMemoryThreads, Thread
    from tests.runtime.test_a_conversation_without_a_record import Agent

    class WaitingStore(InMemoryThreads):
        def __init__(self) -> None:
            super().__init__()
            self.releasing = asyncio.Event()
            self.finish = asyncio.Event()

        async def release(self, thread_id: str, holder: str) -> None:
            self.releasing.set()
            await self.finish.wait()
            await super().release(thread_id, holder)

    port, store = Managed(wait=True), WaitingStore()
    thread = await Thread.open(
        agent=cast(Any, Agent([])),
        ports=Ports(components=(port,), governance=AllowAll(), sink=ListSink(), clock=FixedClock()),
        store=store,
        root=tmp_path,
        holder="owner",
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
    )
    closing = asyncio.create_task(thread.close())
    await asyncio.wait_for(port.closing.wait(), 2)
    closing.cancel()
    port.finish.set()
    await asyncio.wait_for(store.releasing.wait(), 2)
    closing.cancel()
    await asyncio.sleep(0)
    store.finish.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(closing, 2)
    assert (port.closed, await store.held_by(thread.id)) == ([thread.id], None)


async def test_conversation_close_settles_teardown_before_delivering_cancellation(
    tmp_path: Any,
) -> None:
    from typing import cast

    from shadow_hdk.runtime.conversation import Conversation
    from tests.runtime.test_a_conversation_without_a_record import Agent

    port = Managed(wait=True)
    conversation = await Conversation.open(
        agent=cast(Any, Agent([])),
        ports=Ports(components=(port,), governance=AllowAll(), sink=ListSink(), clock=FixedClock()),
        root=tmp_path,
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
    )
    closing = asyncio.create_task(conversation.close())
    await asyncio.wait_for(port.closing.wait(), 2)
    closing.cancel()
    await asyncio.sleep(0)
    port.finish.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(closing, 2)
    assert (port.closed, conversation.closed) == ([conversation.id], True)
