"""One adapter, every provider — and what breaks is the translation, not their servers."""

from __future__ import annotations

from langchain_core.messages import AIMessage, ToolMessage

from shadow_hdk.adapters.langchain import LangChainModel
from shadow_hdk.kernel import Interface
from shadow_hdk.kernel.ports import Message, ModelPort, ModelRequest, Usage
from tests.adapters.contract import ModelPortContract
from tests.adapters.langchain.fake import FakeChat

WEIGH = Interface(
    name="weigh",
    description="Weigh a thing.",
    input_schema={
        "type": "object",
        "properties": {"what": {"type": "string"}},
        "required": ["what"],
    },
)


def a_model(
    *answers: AIMessage, deltas: list[str] | None = None
) -> tuple[LangChainModel, FakeChat]:
    chat = FakeChat(answers=list(answers), deltas=deltas or [], seen=[], bound=[])
    return LangChainModel.over(chat), chat


class TestLangChainModelIsAModelPort(ModelPortContract):
    def port(self) -> ModelPort:
        model, _ = a_model(
            AIMessage(
                content="twelve kilograms",
                usage_metadata={"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
            ),
            AIMessage(
                content="twelve kilograms",
                usage_metadata={"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
            ),
            deltas=["twelve", " kilo", "grams"],
        )
        return model

    def a_request(self) -> ModelRequest:
        return ModelRequest((Message("user", "how heavy is the lathe?"),))


async def test_text_comes_back() -> None:
    model, _ = a_model(AIMessage(content="twelve kilograms"))
    assert (await model.complete(ModelRequest((Message("user", "?"),)))).text == "twelve kilograms"


async def test_every_role_reaches_the_model_as_its_own_kind_of_message() -> None:
    model, chat = a_model(AIMessage(content="ok"))
    await model.complete(
        ModelRequest(
            (
                Message("system", "you are careful"),
                Message("user", "weigh it"),
                Message("assistant", ""),
                Message("tool", '{"kg": 12}', tool_call_id="c1"),
            )
        )
    )
    kinds = [type(m).__name__ for m in chat.seen[0]]
    assert kinds == ["SystemMessage", "HumanMessage", "AIMessage", "ToolMessage"]
    last = chat.seen[0][-1]
    assert isinstance(last, ToolMessage)
    assert last.tool_call_id == "c1"


async def test_our_interfaces_are_bound_as_tools_the_model_can_call() -> None:
    model, chat = a_model(AIMessage(content="ok"))
    await model.complete(ModelRequest((Message("user", "?"),), tools=(WEIGH,)))
    assert len(chat.bound) == 1
    bound = chat.bound[0]
    assert bound["function"]["name"] == "weigh"
    assert bound["function"]["parameters"] == WEIGH.input_schema


async def test_a_tool_call_comes_back_as_ours() -> None:
    model, _ = a_model(
        AIMessage(
            content="",
            tool_calls=[
                {"name": "weigh", "args": {"what": "lathe"}, "id": "c1", "type": "tool_call"}
            ],
        )
    )
    response = await model.complete(ModelRequest((Message("user", "?"),), tools=(WEIGH,)))
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "weigh"
    assert response.tool_calls[0].arguments == {"what": "lathe"}
    assert response.tool_calls[0].id == "c1"


async def test_tokens_are_reported_and_money_is_not_invented() -> None:
    """A provider reports tokens; nobody reports cents. The adapter says `None` for what it does not
    know rather than `0`, because zero is a claim and unknown is the truth (`10` §5 R2)."""
    model, _ = a_model(
        AIMessage(
            content="ok",
            usage_metadata={"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
        )
    )
    usage = (await model.complete(ModelRequest((Message("user", "?"),)))).usage
    assert usage == Usage(input_tokens=10, output_tokens=4, cost_cents=None)


async def test_a_model_that_reports_nothing_reports_nothing() -> None:
    model, _ = a_model(AIMessage(content="ok"))
    assert (await model.complete(ModelRequest((Message("user", "?"),)))).usage is None


async def test_a_price_list_is_the_products_business_and_may_be_supplied() -> None:
    """Pricing is policy: the adapter knows tokens, the product knows its contract. Supplying a
    price makes the cost ceiling usable without the harness ever holding a rate card."""
    chat = FakeChat(
        answers=[
            AIMessage(
                content="ok",
                usage_metadata={"input_tokens": 1000, "output_tokens": 500, "total_tokens": 1500},
            )
        ],
        deltas=[],
        seen=[],
        bound=[],
    )
    model = LangChainModel.over(chat, price=lambda u: (u.input_tokens or 0) // 100)
    usage = (await model.complete(ModelRequest((Message("user", "?"),)))).usage
    assert usage is not None and usage.cost_cents == 10


async def test_streaming_yields_the_answer_in_pieces() -> None:
    model, _ = a_model(
        AIMessage(
            content="twelve kilograms",
            usage_metadata={"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
        ),
        deltas=["twelve", " kilo", "grams"],
    )
    chunks = [c async for c in model.stream(ModelRequest((Message("user", "?"),)))]
    assert "".join(c.text for c in chunks) == "twelve kilograms"
    assert chunks[-1].done
    assert chunks[-1].usage == Usage(10, 4, None)


async def test_empty_frames_are_not_yielded_as_pieces_of_answer() -> None:
    """What a real provider actually sends. Over HuggingFace Inference Providers this model returns
    five frames of which exactly one carries words — so a stream that passed the empty ones on would
    make a run look like it streamed when it did not, and would put four empty deltas in the record.

    Written after a mutation that stopped filtering them left the suite green: the fake had been too
    tidy, and the only test covering it was the live one, which a normal run deselects.
    """
    model, _ = a_model(
        AIMessage(
            content="One two three four five",
            usage_metadata={"input_tokens": 13, "output_tokens": 6, "total_tokens": 19},
        ),
        deltas=["", "", "One two three four five", ""],
    )
    chunks = [c async for c in model.stream(ModelRequest((Message("user", "count"),)))]
    assert [c.text for c in chunks] == ["One two three four five", ""]
    assert all(c.text for c in chunks[:-1])
    assert chunks[-1].done and chunks[-1].usage == Usage(13, 6, None)


def test_an_assistant_message_reaches_langchain_with_its_calls() -> None:
    """The adapter's half of BUG-005, without a provider: what `_to_langchain` builds."""
    from langchain_core.messages import AIMessage

    from shadow_hdk.adapters.langchain.model import _to_langchain
    from shadow_hdk.kernel.ports import Message, ToolCall

    built = _to_langchain(
        (
            Message("user", "look it up"),
            Message(
                "assistant", "looking", tool_calls=(ToolCall("c1", "look", {"topic": "lathes"}),)
            ),
            Message("tool", "found lathes", tool_call_id="c1"),
        )
    )
    assistant = built[1]
    assert isinstance(assistant, AIMessage)
    assert assistant.tool_calls == [
        {"name": "look", "args": {"topic": "lathes"}, "id": "c1", "type": "tool_call"}
    ]


def test_arguments_that_are_not_a_mapping_are_carried_not_dropped() -> None:
    """A provider names its arguments, so LangChain wants a mapping. A model that sent something
    else is still shown to the next turn rather than silently losing its own call."""
    from shadow_hdk.adapters.langchain.model import _calls_for
    from shadow_hdk.kernel.ports import ToolCall

    assert _calls_for((ToolCall("c1", "look", "lathes"),))[0]["args"] == {"value": "lathes"}
