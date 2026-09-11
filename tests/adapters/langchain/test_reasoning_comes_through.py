"""A provider's reasoning reaches `ModelResponse.reasoning`, where the provider exposes it (D45).

Providers disagree about *where* thinking lives, and agree it exists:

* Anthropic answers in content blocks, one of them `{"type": "thinking", "thinking": …}`.
* OpenAI-compatible reasoning models put it in `additional_kwargs["reasoning_content"]`.
* Some put a string under `additional_kwargs["reasoning"]`.

The adapter reads all three and joins what it finds, in that order of preference. A message with
none of them reasons an empty string — *did not say* — never an invented summary: the record is not
the place to put words in a model's mouth.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from shadow_hdk.kernel.ports import Message, ModelRequest
from tests.adapters.langchain.test_langchain import a_model

ASK = ModelRequest((Message("user", "how heavy is the lathe?"),))


async def test_a_thinking_block_is_reasoning() -> None:
    model, _ = a_model(
        AIMessage(
            content=[
                {"type": "thinking", "thinking": "the handbook lists it by line"},
                {"type": "text", "text": "12kg"},
            ]
        )
    )

    answer = await model.complete(ASK)

    assert answer.reasoning == "the handbook lists it by line"
    assert answer.text == "12kg", "the thinking block leaked into the text"


async def test_reasoning_content_is_reasoning() -> None:
    model, _ = a_model(
        AIMessage(content="12kg", additional_kwargs={"reasoning_content": "line 3, so 12"})
    )

    assert (await model.complete(ASK)).reasoning == "line 3, so 12"


async def test_a_model_that_said_nothing_about_its_thinking_reasons_nothing() -> None:
    model, _ = a_model(AIMessage(content="12kg"))

    assert (await model.complete(ASK)).reasoning == ""


async def test_reasoning_is_never_invented_from_the_answer() -> None:
    """A mutant that fell back to `text` when no reasoning was present would put the answer on the
    record twice, once labelled as thought."""
    model, _ = a_model(AIMessage(content="a very long and detailed answer that is not reasoning"))

    assert (await model.complete(ASK)).reasoning == ""
