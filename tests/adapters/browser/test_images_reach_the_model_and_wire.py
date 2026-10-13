"""Tool images remain images across the model loop, JSON checkpoints and MCP boundaries."""

from typing import Any

from mcp.types import CallToolResult, ImageContent, TextContent

from shadow_hdk.adapters.agent import AgentComponent, Pattern
from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.adapters.langchain.model import _to_langchain
from shadow_hdk.adapters.mcp.components import McpComponents
from shadow_hdk.adapters.recording.server import _as_result
from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Completed,
    Component,
    Composition,
    EffectProfile,
    Floor,
    Image,
    Interface,
    Invoke,
    Lease,
    Provenance,
    Registration,
)
from shadow_hdk.kernel.contracts import round_trip
from shadow_hdk.kernel.observations import Observation
from shadow_hdk.kernel.ports import Message, ModelRequest, ModelResponse, ToolCall
from shadow_hdk.runtime import Ports, RunOptions, current_run, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

PNG = Image(mime_type="image/png", data="iVBORw0KGgo=")


class Picture:
    def __init__(self) -> None:
        self.scopes: list[str] = []
        self.released: list[str] = []

    async def registrations(self) -> list[Registration]:
        return [
            Registration(
                "picture",
                Component(
                    Interface("picture", "An image"),
                    EffectProfile(),
                    Provenance("test", "test", "2026-10-13T00:00:00Z"),
                ),
            )
        ]

    async def invoke(self, registration: str, inputs: Any) -> Completed:
        context = current_run()
        if context is not None:
            self.scopes.append(context.resource_scope)
        return Completed({"caption": "page"}, images=(PNG,))

    async def release_run(self, resource_scope: str) -> None:
        self.released.append(resource_scope)


def test_image_contracts_roundtrip_with_old_empty_defaults() -> None:
    observation = Completed({"caption": "page"}, images=(PNG,))
    message = Message("tool", "page", "c1", images=(PNG,))
    assert (
        round_trip(observation, Observation),
        round_trip(ModelRequest((message,)), ModelRequest),
        Completed().images,
        Message("user", "text").images,
    ) == (observation, ModelRequest((message,)), (), ())


async def test_images_reach_the_model_and_the_run_closes_resources() -> None:
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
    events = [
        e
        async for e in run(
            Composition(
                (Invoke("a", agent.registration_id, (Binding(name="brief", value="look"),)),)
            ),
            ports,
            options=RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0))),
        )
    ]
    assert len(model.requests) == 3, events
    results = [m for m in model.requests[2].messages if m.role == "tool"]
    assert (
        [m.images for m in results],
        all(PNG.data not in m.content for m in results),
        len(set(picture.scopes)),
        picture.released,
        events[-1].kind,
    ) == ([(PNG,), (PNG,)], True, 1, [picture.scopes[0]], "ended")


def test_langchain_and_mcp_preserve_image_blocks() -> None:
    message = Message("tool", "page", "c1", images=(PNG,))
    native = _to_langchain((message,))[0]
    wire = _as_result(Completed({"caption": "page"}, images=(PNG,)))
    assert (native.content, [(b.type, getattr(b, "data", None)) for b in wire.content]) == (
        [
            {"type": "text", "text": "page"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + PNG.data}},
        ],
        [("text", None), ("image", PNG.data)],
    )


async def test_mcp_image_results_survive_ingress() -> None:
    from mcp import StdioServerParameters

    class Session:
        async def call_tool(self, name: str, arguments: Any) -> CallToolResult:
            return CallToolResult(
                content=[
                    TextContent(type="text", text='{"caption":"page"}'),
                    ImageContent(type="image", data=PNG.data, mime_type=PNG.mime_type),
                ]
            )

    port = McpComponents(StdioServerParameters(command="unused"))
    port._session = Session()  # type: ignore[assignment]
    port._tools["picture"] = "picture"
    assert await port.invoke("picture", {}) == Completed({"caption": "page"}, images=(PNG,))
