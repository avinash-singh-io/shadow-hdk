"""E: a stored procedure changes execution, rather than merely surviving parsing."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from shadow_hdk.adapters.agent.loader import pattern_from
from shadow_hdk.adapters.agent.model import ModelAgent
from shadow_hdk.adapters.agent.pattern import Pattern
from shadow_hdk.adapters.agent.patterns import PatternRegistry, store_patterns
from shadow_hdk.adapters.agent.registry import SkillRegistry
from shadow_hdk.adapters.agent.skills import Skill
from shadow_hdk.kernel import ModelResponse
from shadow_hdk.kernel.ports import ToolCall
from shadow_hdk.serve import ServeHost, Settings
from tests.adapters.agent.test_an_agent_is_a_store_row import FakeStore

pytestmark = pytest.mark.anyio


class Procedures:
    async def skills(self) -> tuple[Skill, ...]:
        return (Skill(name="procedure", prompt="PROCEDURE-SENTINEL"),)


def host_shape(*, skill: str = "procedure", model: Any = None) -> Any:
    return SimpleNamespace(
        patterns=PatternRegistry(
            (
                store_patterns(
                    FakeStore({"worker": {"name": "worker", "system": "ROLE", "skill": skill}})
                ),
            )
        ),
        skills=SkillRegistry((Procedures(),)),
        _handed_agent=None,
        _model=model,
    )


def test_the_loader_keeps_the_binding_and_defaults_to_none() -> None:
    assert (
        pattern_from({"name": "w", "system": "r", "skill": "procedure"}, where="row").skill
        == "procedure"
    )
    assert pattern_from({"name": "w", "system": "r"}, where="row").skill is None
    assert Pattern(name="w", system="r").skill is None


@pytest.mark.parametrize("model", [None, object()])
async def test_an_unknown_skill_refuses_before_either_provider_opens(model: Any) -> None:
    with pytest.raises(ValueError, match="procedur.*procedure"):
        await ServeHost._agent_named(host_shape(skill="procedur", model=model), "worker")


async def test_the_model_receives_the_resolved_procedure() -> None:
    chosen = await ServeHost._agent_named(host_shape(model=object()), "worker")
    assert cast(ModelAgent, chosen).skill == Skill(name="procedure", prompt="PROCEDURE-SENTINEL")


@pytest.mark.parametrize("model, expected", [(None, ("agent.skill",)), (object(), ())])
async def test_only_a_provider_that_cannot_bind_it_reports_it(
    model: Any, expected: tuple[str, ...]
) -> None:
    carries = await ServeHost._agent_carries(host_shape(model=model), "worker")
    assert carries.unhonoured == expected  # type: ignore[union-attr]


class Listening:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    async def complete(self, request: Any) -> ModelResponse:
        self.requests.append(request)
        return ModelResponse("", (ToolCall("done-1", "done", {"summary": "finished"}),))


@pytest.mark.parametrize("needs, calls", [([], 1), (["absent-dependency"], 0)])
async def test_the_stored_binding_changes_the_first_turn(
    tmp_path: Path, needs: list[str], calls: int
) -> None:
    model = Listening()
    host = ServeHost(
        Settings(root=tmp_path, store=f"sqlite:///{tmp_path}/h.db"), model=cast(Any, model)
    )
    thread = None
    try:
        await host.store.put(
            "skills",
            "procedure",
            {
                "name": "procedure",
                "description": "A procedure",
                "prompt": "PROCEDURE-SENTINEL",
                "needs": needs,
            },
        )
        await host.store.put(
            "agents", "worker", {"name": "worker", "system": "ROLE", "skill": "procedure"}
        )
        thread = await host.open(
            root=str(tmp_path), mode="workspace-write", want=None, name="tools", agent="worker"
        )
        async for _ in thread.turn("go"):
            pass
        assert len(model.requests) == calls
        if calls:
            assert "PROCEDURE-SENTINEL" in model.requests[0].messages[0].content
    finally:
        if thread is not None:
            await thread.close()
        await host.aclose()


@pytest.mark.parametrize(
    "carries, expected",
    [
        (SimpleNamespace(unhonoured=("agent.skill",)), ("temperature", "agent.skill")),
        (SimpleNamespace(), ("temperature",)),
        (None, ("temperature",)),
    ],
)
async def test_the_session_report_keeps_provider_and_binding_limitations(
    carries: Any, expected: tuple[str, ...]
) -> None:
    from shadow_hdk.runtime.conversation import Conversation

    class Provider:
        async def open(self, **kwargs: Any) -> Any:
            return SimpleNamespace(unmapped=("temperature",))

    conversation = SimpleNamespace(
        session_id="",
        _agent=Provider(),
        _sources=(),
        workspace=SimpleNamespace(primary=SimpleNamespace(path="/unused")),
        _behaviour_for_the_provider=lambda: None,
        _give_the_transcript_back=lambda session: None,
        _let_the_provider_wait_for_us=lambda session: None,
        _agent_carries=carries,
    )
    await Conversation._open_provider(cast(Conversation, conversation))
    assert conversation.unmapped_behaviour == expected
