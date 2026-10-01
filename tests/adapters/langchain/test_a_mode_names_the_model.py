"""A mode asking for a model gets that model (D180, phase 65, BUG-231).

Phase 62 closed BUG-229 with the words *`Behaviour.model` reaches `ModelRequest.model` — the field
was already there*. It does reach the request. It then went nowhere: `LangChainModel._bind` read
`request.tools` and returned the chat model it was constructed with, so the only `ModelPort` over
real providers **discarded the field** — while `unmapped_for_a_model` named `effort` and
`temperature` and not `model`, which a product reads as *your model was honoured*.

A product running one host with a cheap model for one mode and a strong one for another had no way
to do it and no way to find out.

**No kernel change** (D180): the field is already on `ModelRequest`. What changes is that the
adapter honours it where it can — constructing a second chat model for the asked-for spec and
caching it — and **says so where it cannot**, which is the `over()` seam: a chat model somebody else
built cannot be re-specified, and guessing would be the same lie in a new place.
"""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import AIMessage

from shadow_hdk.adapters.langchain import LangChainModel
from shadow_hdk.kernel.ports import Message, ModelRequest
from tests.adapters.langchain.fake import FakeChat

pytestmark = pytest.mark.anyio

ASKED = (Message("user", "hello"),)


def _request(model: str | None = None) -> ModelRequest:
    return ModelRequest(ASKED, (), model=model)


# ------------------------------------------------------- a wrapped chat model says it cannot


def test_a_wrapped_chat_model_cannot_be_respecified_and_says_so() -> None:
    """`over()` is the escape hatch for a host that already configured a chat model, and the tests'
    own seam. It has no spec to vary, so the honest answer is *this one cannot*."""
    model = LangChainModel.over(FakeChat(answers=[], deltas=[], seen=[], bound=[]))

    assert model.selects_model is False


async def test_a_wrapped_chat_model_still_answers_a_request_naming_a_model() -> None:
    """It must not refuse or crash — it answers with the model it has, and the honesty field is
    where the discrepancy is reported, not an exception a product cannot act on."""
    chat = FakeChat(answers=[AIMessage(content="said")], deltas=[], seen=[], bound=[])
    model = LangChainModel.over(chat)

    answer = await model.complete(_request("some-other-model"))

    assert answer.text == "said"


# ------------------------------------------------------- and the honesty field names it


def test_the_model_is_named_as_unhonourable_where_the_port_cannot_select_one() -> None:
    """D180's other half. Naming `effort` and `temperature` while silently dropping `model` is the
    shape of BUG-229 all over again."""
    from shadow_hdk.kernel.providers import Behaviour, unmapped_for_a_model

    named = unmapped_for_a_model(Behaviour(model="strong-one"), selects_model=False)

    assert "model" in named, named


def test_the_model_is_not_named_where_the_port_can_select_one() -> None:
    """Paired, so the test above cannot pass because the field is named unconditionally."""
    from shadow_hdk.kernel.providers import Behaviour, unmapped_for_a_model

    assert "model" not in unmapped_for_a_model(Behaviour(model="strong-one"), selects_model=True)


def test_a_mode_asking_for_no_model_is_never_told_one_was_dropped() -> None:
    """A port that cannot select a model has nothing to report for a mode that asked for none."""
    from shadow_hdk.kernel.providers import Behaviour, unmapped_for_a_model

    assert unmapped_for_a_model(Behaviour(), selects_model=False) == ()


def test_the_default_is_that_a_port_honours_its_own_contract() -> None:
    """`model` is a `ModelRequest` field, so a port is expected to read it. A port that does not say
    otherwise is taken at its word — the kit's own adapter is the one that has to be accurate."""
    from shadow_hdk.kernel.providers import Behaviour, unmapped_for_a_model

    assert unmapped_for_a_model(Behaviour(model="m")) == ()


def test_effort_and_temperature_are_still_named_either_way() -> None:
    """Nothing phase 62 established moves."""
    from shadow_hdk.kernel.providers import Behaviour, unmapped_for_a_model

    behaviour = Behaviour(effort="high", temperature=0.2)

    assert unmapped_for_a_model(behaviour, selects_model=True) == ("effort", "temperature")
    assert unmapped_for_a_model(behaviour, selects_model=False) == ("effort", "temperature")


# ------------------------------------------------------- and a spec-built one re-binds


async def test_a_spec_built_model_asks_the_model_the_mode_named(monkeypatch: Any) -> None:
    """The property that matters: a request naming a model is answered by a chat model built for
    **that** spec, not by the one the host constructed."""
    built: list[str] = []

    def _init(spec: str, **kw: Any) -> Any:
        built.append(spec)
        return FakeChat(answers=[AIMessage(content=spec)], deltas=[], seen=[], bound=[])

    import langchain.chat_models as chat_models

    monkeypatch.setattr(chat_models, "init_chat_model", _init)

    model = LangChainModel("openai:cheap-one")
    assert model.selects_model is True, "a model built from a spec can be built from another"

    answer = await model.complete(_request("openai:strong-one"))

    assert answer.text == "openai:strong-one", answer.text
    assert built == ["openai:cheap-one", "openai:strong-one"], built


async def test_a_request_naming_the_constructed_model_builds_nothing_new(monkeypatch: Any) -> None:
    """Asking for what the host already configured must not pay to construct it twice."""
    built: list[str] = []

    def _init(spec: str, **kw: Any) -> Any:
        built.append(spec)
        return FakeChat(answers=[AIMessage(content=spec)], deltas=[], seen=[], bound=[])

    import langchain.chat_models as chat_models

    monkeypatch.setattr(chat_models, "init_chat_model", _init)
    model = LangChainModel("openai:cheap-one")

    await model.complete(_request("openai:cheap-one"))

    assert built == ["openai:cheap-one"], built


async def test_the_second_turn_on_the_same_model_reuses_it(monkeypatch: Any) -> None:
    """A thread that runs twenty turns on one mode must not construct twenty chat models."""
    built: list[str] = []

    def _init(spec: str, **kw: Any) -> Any:
        built.append(spec)
        return FakeChat(
            answers=[AIMessage(content=spec), AIMessage(content=spec)],
            deltas=[],
            seen=[],
            bound=[],
        )

    import langchain.chat_models as chat_models

    monkeypatch.setattr(chat_models, "init_chat_model", _init)
    model = LangChainModel("openai:cheap-one")

    await model.complete(_request("openai:strong-one"))
    await model.complete(_request("openai:strong-one"))

    assert built == ["openai:cheap-one", "openai:strong-one"], built


async def test_a_request_naming_nothing_is_answered_by_the_constructed_one(
    monkeypatch: Any,
) -> None:
    """Byte for byte the behaviour every host has today."""
    built: list[str] = []

    def _init(spec: str, **kw: Any) -> Any:
        built.append(spec)
        return FakeChat(answers=[AIMessage(content=spec)], deltas=[], seen=[], bound=[])

    import langchain.chat_models as chat_models

    monkeypatch.setattr(chat_models, "init_chat_model", _init)
    model = LangChainModel("openai:cheap-one")

    answer = await model.complete(_request(None))

    assert answer.text == "openai:cheap-one"
    assert built == ["openai:cheap-one"]


async def test_the_streaming_path_honours_it_too(monkeypatch: Any) -> None:
    """Two paths diverging is how BUG-229 happened: Q1 folded instructions into a CLI's prompt while
    a key-backed model got nothing. `_bind` is the one seam, so both get it — asserted, not assumed.
    """

    def _init(spec: str, **kw: Any) -> Any:
        return FakeChat(answers=[AIMessage(content=spec)], deltas=[spec], seen=[], bound=[])

    import langchain.chat_models as chat_models

    monkeypatch.setattr(chat_models, "init_chat_model", _init)
    model = LangChainModel("openai:cheap-one")

    said = "".join([chunk.text async for chunk in model.stream(_request("openai:strong-one"))])

    assert "openai:strong-one" in said, said


# ------------------------------------------------- and the run reports the port's own answer


async def test_a_run_on_a_wrapped_chat_model_names_the_model_it_could_not_honour() -> None:
    """End to end, through the field a product actually reads. `_ModelSession.unmapped` asked the
    port rather than assuming, which is the whole of D180's reporting half."""
    from typing import cast

    from shadow_hdk.adapters.agent import ModelAgent, single
    from shadow_hdk.kernel.providers import Behaviour

    chat = FakeChat(answers=[AIMessage(content="said")], deltas=[], seen=[], bound=[])
    agent = ModelAgent(model=cast(Any, LangChainModel.over(chat)), pattern=single)
    session = await agent.open(behaviour=Behaviour(model="strong-one", temperature=0.3))

    assert "model" in session.unmapped, session.unmapped
    assert "temperature" in session.unmapped, session.unmapped


async def test_a_run_on_a_port_that_selects_a_model_does_not_name_it() -> None:
    """Paired against the test above, so neither can pass by naming the field unconditionally."""
    from typing import cast

    from shadow_hdk.adapters.agent import ModelAgent, single
    from shadow_hdk.kernel import ModelResponse
    from shadow_hdk.kernel.providers import Behaviour

    class Selects:
        selects_model = True

        async def complete(self, request: Any) -> ModelResponse:  # pragma: no cover
            return ModelResponse(text="")

        async def stream(self, request: Any) -> Any:  # pragma: no cover
            from shadow_hdk.kernel.ports import ModelChunk

            yield ModelChunk(text="", done=True)

    agent = ModelAgent(model=cast(Any, Selects()), pattern=single)
    session = await agent.open(behaviour=Behaviour(model="strong-one", temperature=0.3))

    assert "model" not in session.unmapped, session.unmapped
    assert "temperature" in session.unmapped, "and the genuinely unmappable is still named"
