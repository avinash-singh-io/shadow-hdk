"""The doubles satisfy the same contracts the real adapters do.

If they did not, every test in this repository would be proving something about a fiction.
"""

from __future__ import annotations

from pydantic import JsonValue

from shadow_hdk.kernel.ports import (
    ClockPort,
    ComponentPort,
    GovernancePort,
    Message,
    ModelRequest,
    ModelResponse,
)
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    Judge,
    ListObserver,
    ListSink,
    ScriptedModel,
    make_registration,
)
from tests.adapters.contract import (
    ClockPortContract,
    ComponentPortContract,
    GovernancePortContract,
    ModelPortContract,
    ObserverPortContract,
    SinkPortContract,
)
from tests.adapters.contract.suites import an_observation


class TestFixedClockIsAClockPort(ClockPortContract):
    def port(self) -> ClockPort:
        return FixedClock()


class TestJudgeIsAGovernancePort(GovernancePortContract):
    def port(self) -> GovernancePort:
        return Judge.allow_all()


class TestListSinkIsASinkPort(SinkPortContract):
    def port(self) -> ListSink:
        return ListSink()


class TestListObserverIsAnObserverPort(ObserverPortContract):
    def port(self) -> ListObserver:
        return ListObserver()


class TestInMemoryComponentsIsAComponentPort(ComponentPortContract):
    def port(self) -> ComponentPort:
        async def handler(_inputs: JsonValue) -> object:
            return an_observation()

        return InMemoryComponents([(make_registration("echo"), handler)])  # type: ignore[list-item]

    def valid_call(self) -> tuple[str, JsonValue]:
        return "echo", {"text": "hi"}


class TestScriptedModelIsAModelPort(ModelPortContract):
    def port(self) -> ScriptedModel:
        return ScriptedModel([ModelResponse(text="hello"), ModelResponse(text="hello")])

    def a_request(self) -> ModelRequest:
        return ModelRequest((Message("user", "hi"),))
