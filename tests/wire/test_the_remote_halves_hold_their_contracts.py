"""The wire's remote halves are ports, and are held to the ports' contracts.

`RemoteModel`, `RemoteComponents`, `RemoteGovernance` and `RemoteSink` are what the served runtime
uses *as* its ports: every `complete`, `invoke`, `judge` and `propose` a run makes over the wire
goes through one of them. They implemented the ports structurally — no base named — and so the
invariant that holds every implementation to a contract never saw them (BUG-007's shape, one layer
over: the net covers what it can see). What it would have found: `RemoteModel.stream` returned a
coroutine around an iterator where the port is an async iterator, so `async for chunk in
model.stream(...)` raised on the runtime's side of every wire.

Each suite runs over a real loopback — two peers, JSON frames, a task group — entered inside each
test, the way the MCP adapter's is.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from pydantic import JsonValue

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.kernel.components import RegistrationId
from shadow_hdk.kernel.observations import Completed, Observation
from shadow_hdk.kernel.ports import (
    ComponentPort,
    GovernancePort,
    Message,
    ModelPort,
    ModelRequest,
    ModelResponse,
    SinkPort,
)
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)
from shadow_hdk.wire.sides import loopback
from tests.adapters.contract import (
    ComponentPortContract,
    GovernancePortContract,
    ModelPortContract,
    SinkPortContract,
)


async def _echo(inputs: JsonValue) -> Observation:
    return Completed({"echoed": inputs})


@asynccontextmanager
async def _crossed() -> AsyncIterator[Ports]:
    """The runtime's ports over a loopback whose host holds one of each real port."""
    host_side = Ports(
        model=ScriptedModel([ModelResponse(text="hello")]),
        components=(InMemoryComponents([(make_registration("echo"), _echo)]),),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    async with loopback(host_side) as (_host, runtime):
        yield runtime.ports()


class TestRemoteModelIsAModelPort(ModelPortContract):
    @asynccontextmanager
    async def using(self) -> AsyncIterator[ModelPort]:
        async with _crossed() as ports:
            assert ports.model is not None
            yield ports.model

    def a_request(self) -> ModelRequest:
        return ModelRequest((Message("user", "hi"),))


class TestRemoteComponentsIsAComponentPort(ComponentPortContract):
    @asynccontextmanager
    async def using(self) -> AsyncIterator[ComponentPort]:
        async with _crossed() as ports:
            yield ports.components[0]

    def valid_call(self) -> tuple[RegistrationId, JsonValue]:
        return "echo", {"text": "hi"}


class TestRemoteGovernanceIsAGovernancePort(GovernancePortContract):
    @asynccontextmanager
    async def using(self) -> AsyncIterator[GovernancePort]:
        async with _crossed() as ports:
            yield ports.governance


class TestRemoteSinkIsASinkPort(SinkPortContract):
    @asynccontextmanager
    async def using(self) -> AsyncIterator[SinkPort]:
        async with _crossed() as ports:
            yield ports.sink
