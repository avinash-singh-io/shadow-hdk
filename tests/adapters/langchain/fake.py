"""A chat model that satisfies langchain's own interface, so what is tested is our translation.

The OpenAI, Anthropic and HuggingFace paths differ from this only in whose server answers. What can
break is the mapping in both directions — messages, tool schemas, tool calls, usage — and that is
what a fake exercises without spending anyone's money.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult


class FakeChat(BaseChatModel):
    """Says what it was told to. Records what it was sent and what tools were bound to it."""

    answers: list[AIMessage] = []
    deltas: list[str] = []
    pieces: list[AIMessageChunk] = []
    """Chunks yielded verbatim, when given — a provider's own stream shape: thinking blocks,
    a tool call arriving in fragments, usage on the last frame."""
    seen: list[list[BaseMessage]] = []
    bound: list[Any] = []

    @property
    def _llm_type(self) -> str:
        return "fake"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> BaseChatModel:
        self.bound = list(tools)
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.seen.append(list(messages))
        answer = self.answers.pop(0) if self.answers else AIMessage(content="")
        return ChatResult(generations=[ChatGeneration(message=answer)])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        self.seen.append(list(messages))
        if self.pieces:
            for piece in self.pieces:
                yield ChatGenerationChunk(message=piece)
            return
        answer = self.answers.pop(0) if self.answers else AIMessage(content="")
        for delta in self.deltas or [str(answer.content)]:
            yield ChatGenerationChunk(message=AIMessageChunk(content=delta))
        yield ChatGenerationChunk(
            message=AIMessageChunk(content="", usage_metadata=answer.usage_metadata)
            if answer.usage_metadata
            else AIMessageChunk(content="")
        )
