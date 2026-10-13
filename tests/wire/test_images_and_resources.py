"""Generic image and resource contracts also survive the runtime/host boundary."""

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.kernel import Ceiling, Completed, Composition, Floor, Invoke, Lease
from shadow_hdk.runtime import Ports, RunOptions
from shadow_hdk.runtime.testing import FixedClock, ListSink
from shadow_hdk.wire.sides import loopback
from tests.adapters.browser.test_images_reach_the_model_and_wire import PNG, Picture


async def test_a_crossed_component_sees_its_resource_scope_and_closes_with_the_run() -> None:
    picture = Picture()
    ports = Ports(components=(picture,), governance=AllowAll(), sink=ListSink(), clock=FixedClock())
    async with loopback(ports) as (host, _):
        await host.initialize()
        await host.run(
            Composition((Invoke("one", "picture"), Invoke("two", "picture"))),
            RunOptions(lease=Lease(Ceiling(10, 3600, 100), Floor(0))),
        )
        seen = [e.observation for e in host.events if e.kind == "observed"]
        assert (seen, picture.scopes, picture.released) == (
            [Completed({"caption": "page"}, images=(PNG,))] * 2,
            [host.events[0].run_id] * 2,
            [host.events[0].run_id],
        )


async def test_crossed_agent_children_share_the_root_resource_scope() -> None:
    from shadow_hdk.adapters.agent import AgentComponent, Pattern
    from shadow_hdk.kernel import Binding, EffectProfile, ModelResponse, ToolCall
    from shadow_hdk.runtime.testing import ScriptedModel

    picture = Picture()
    agent = AgentComponent(pattern=Pattern(name="a", system="Look"), effects=EffectProfile())
    model = ScriptedModel(
        [
            ModelResponse(tool_calls=(ToolCall("c1", "picture", {}),)),
            ModelResponse(tool_calls=(ToolCall("c2", "picture", {}),)),
            ModelResponse(tool_calls=(ToolCall("d", "done", {"summary": "seen"}),)),
        ]
    )
    ports = Ports(
        model=model,
        components=(picture, agent),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    async with loopback(ports) as (host, _):
        await host.initialize()
        await host.run(
            Composition(
                (Invoke("a", agent.registration_id, (Binding(name="brief", value="look"),)),)
            ),
            RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0))),
        )
        assert (picture.scopes, picture.released) == (
            [host.events[0].run_id] * 2,
            [host.events[0].run_id],
        )


async def test_an_older_host_has_the_no_resource_default() -> None:
    from typing import Any, cast

    from shadow_hdk.wire.peer import Peer, RemoteError
    from shadow_hdk.wire.remote import RemoteComponents

    class Older:
        async def call(self, method: str, params: Any) -> Any:
            raise RemoteError(-32601, "unknown method")

    answer: int | None = None
    try:
        await RemoteComponents(cast(Peer, Older())).release_run("root")
    except RemoteError as error:
        answer = error.code
    assert answer is None
