"""A parked tool keeps the same session resources when the person returns."""

from pathlib import Path
from typing import Any, cast

from langgraph.checkpoint.memory import InMemorySaver

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.kernel import Completed
from shadow_hdk.runtime import Approvals, Approve, Ports, current_run
from shadow_hdk.runtime.testing import FixedClock, ListSink
from shadow_hdk.runtime.threads import InMemoryThreads, Thread
from tests.adapters.browser.test_images_reach_the_model_and_wire import Picture
from tests.runtime.test_a_component_can_ask_and_the_run_parks import AsksOnce
from tests.runtime.test_a_conversation_without_a_record import Agent, _lease


class PausedResource(Picture):
    def __init__(self) -> None:
        super().__init__()
        self.asker = AsksOnce()

    async def invoke(self, registration: str, inputs: Any) -> Any:
        context = current_run()
        assert context is not None
        self.scopes.append(context.resource_scope)
        return await self.asker(inputs)


async def test_a_parked_conversation_tool_reuses_its_scope_on_settle(tmp_path: Path) -> None:
    port = PausedResource()
    agent = Agent([([("picture", {})], "waiting")])
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=Ports(components=(port,), governance=AllowAll(), sink=ListSink(), clock=FixedClock()),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=_lease(),
        approvals=Approvals(),
        checkpointer=InMemorySaver(),
    )
    agent.reach = thread.registry.call
    try:
        [e async for e in thread.turn("look", on_question="park")]
        assert (port.scopes, port.released, len(thread.pending)) == ([thread.id], [], 1)
        events = await thread.settle(thread.pending[0].handle, Approve())
        assert (
            [e.observation for e in events if e.kind == "observed"],
            port.scopes,
            port.released,
        ) == (
            [Completed({"finished": True, "from": {"draft": "half done", "n": 3}})],
            [thread.id, thread.id],
            [],
        )
    finally:
        await thread.close()
    assert port.released == [thread.id]
