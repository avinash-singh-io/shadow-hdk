"""LangChain's `usage_metadata.input_token_details` carries what the cache did — `cache_read`,
`cache_creation` — for every provider whose API reports it (Anthropic, OpenAI, the compatible
endpoints). The translation carries it onto `Usage`; absent, the fields are `None` (D141)."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from shadow_hdk.adapters.langchain import LangChainModel
from shadow_hdk.kernel.ports import Message, ModelRequest, Usage
from tests.adapters.langchain.fake import FakeChat


async def _usage(answer: AIMessage) -> Usage | None:
    model = LangChainModel.over(FakeChat(answers=[answer], deltas=[], seen=[], bound=[]))
    return (await model.complete(ModelRequest((Message("user", "?"),)))).usage


async def test_cache_read_and_creation_are_reported() -> None:
    usage = await _usage(
        AIMessage(
            content="ok",
            usage_metadata={
                "input_tokens": 10,
                "output_tokens": 4,
                "total_tokens": 14,
                "input_token_details": {"cache_read": 8, "cache_creation": 2},
            },
        )
    )
    assert usage is not None
    assert usage.input_tokens == 10 and usage.output_tokens == 4
    assert usage.cache_read_tokens == 8
    assert usage.cache_write_tokens == 2


async def test_without_the_details_the_cache_fields_are_unknown() -> None:
    usage = await _usage(
        AIMessage(
            content="ok",
            usage_metadata={"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
        )
    )
    assert usage is not None
    assert usage.cache_read_tokens is None
    assert usage.cache_write_tokens is None
