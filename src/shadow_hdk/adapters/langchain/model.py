"""One `ModelPort` over every provider LangChain integrates.

We write a direct adapter only where LangChain has nothing — ACP is that case, and it is Phase 4.
Everything else arrives here: OpenAI and every OpenAI-compatible endpoint (which is how HuggingFace
Inference Providers, Together, Groq, vLLM and most of the rest are reached), Anthropic, Ollama,
Bedrock, Vertex, Mistral.

What this file actually is, is a **translation** — messages, tool schemas, tool calls and usage,
both ways. That is what can break, and it is what the tests exercise against a fake chat model
rather than against somebody's server.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import aclosing
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from pydantic import JsonValue

from shadow_hdk.kernel.components import Interface
from shadow_hdk.kernel.ports import (
    Message,
    ModelChunk,
    ModelPort,
    ModelRequest,
    ModelResponse,
    ToolCall,
    Usage,
)

Price = Callable[[Usage], int | None]
"""Tokens to cents. **The product's business, not the harness's** — see `pricing` below."""


class LangChainModel(ModelPort):
    def __init__(self, spec: str, *, price: Price | None = None, **kw: Any) -> None:
        """`spec` is anything `init_chat_model` takes: `"openai:gpt-…"`, `"ollama:llama3.1"`,
        `"anthropic:claude-…"`. For an OpenAI-compatible endpoint pass `base_url` and `api_key`
        alongside it — that is how HuggingFace Inference Providers and most hosts are reached.
        """
        from langchain.chat_models import init_chat_model

        self._chat: BaseChatModel = init_chat_model(spec, **kw)
        self._price = price

    @classmethod
    def over(cls, chat: BaseChatModel, *, price: Price | None = None) -> LangChainModel:
        """Wrap a chat model somebody else built — the seam the tests use, and the escape hatch for
        a host that has already configured one."""
        model = cls.__new__(cls)
        model._chat = chat
        model._price = price
        return model

    # ------------------------------------------------------------------ the port

    async def complete(self, request: ModelRequest) -> ModelResponse:
        answer = await self._bind(request).ainvoke(_to_langchain(request.messages))
        return self._response(answer)

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelChunk]:
        usage: Usage | None = None
        calls: tuple[ToolCall, ...] = ()
        # `aclosing` so the provider's own generator — and the HTTP stream under it — is closed the
        # moment we stop reading, whether we finished or a consumer walked away mid-answer.
        stream = self._bind(request).astream(_to_langchain(request.messages))
        async with aclosing(stream):
            async for piece in stream:
                found = _usage_of(piece)
                if found is not None:
                    usage = self._priced(found)
                calls = calls or _calls_of(piece)
                text = _text_of(piece)
                # Empty deltas are noise, not content: a provider that sends five frames of which
                # one carries words has produced one piece of answer, and saying otherwise would
                # make a run look like it streamed when it did not.
                if text:
                    yield ModelChunk(text=text)
        yield ModelChunk(tool_calls=calls, usage=usage, done=True)

    # ------------------------------------------------------------------ translation

    def _bind(self, request: ModelRequest) -> Any:
        if not request.tools:
            return self._chat
        return self._chat.bind_tools([_as_tool(interface) for interface in request.tools])

    def _response(self, answer: BaseMessage) -> ModelResponse:
        found = _usage_of(answer)
        return ModelResponse(
            text=_text_of(answer),
            tool_calls=_calls_of(answer),
            usage=self._priced(found) if found is not None else None,
            reasoning=_reasoning_of(answer),
        )

    def _priced(self, usage: Usage) -> Usage:
        """**Tokens are the provider's fact; money is the product's.**

        No provider reports cents, and the harness holds no rate card — a rate card is policy about
        *this tenant's contract*, which is exactly the sort of thing `09` §8 keeps on the other side
        of the boundary. So `cost_cents` is `None` unless a host supplies a `price`, and `None`
        means *unknown*: the meter then stops claiming to know the total rather than adding zero.
        """
        if self._price is None:
            return usage
        return Usage(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_cents=self._price(usage),
        )


def _as_tool(interface: Interface) -> dict[str, JsonValue]:
    return {
        "type": "function",
        "function": {
            "name": interface.name,
            "description": interface.description,
            "parameters": dict(interface.input_schema),
        },
    }


def _to_langchain(messages: tuple[Message, ...]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    for message in messages:
        match message.role:
            case "system":
                out.append(SystemMessage(content=message.content))
            case "user":
                out.append(HumanMessage(content=message.content))
            case "assistant":
                out.append(
                    AIMessage(content=message.content, tool_calls=_calls_for(message.tool_calls))
                )
            case "tool":
                out.append(
                    ToolMessage(content=message.content, tool_call_id=message.tool_call_id or "")
                )
    return out


def _text_of(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    # Some providers answer in blocks. Join the text ones and ignore the rest; a block we cannot
    # read is not text, and inventing a rendering for it would put words in the model's mouth.
    return "".join(
        part.get("text", "")
        for part in content
        if isinstance(part, dict) and part.get("type") == "text"
    )


def _reasoning_of(message: BaseMessage) -> str:
    """What the model thought, where the provider exposes it (D45).

    Providers disagree about *where* and agree that it exists: Anthropic answers in blocks, one of
    them `thinking`; OpenAI-compatible reasoning models put `reasoning_content` in the extras; a
    few put a plain `reasoning` string there. All are read. None found is an empty string — *did
    not say* — never a fallback to the answer, which would put the model's words on the record
    twice, once mislabelled as thought.
    """
    content = message.content
    if not isinstance(content, str):
        blocks = "".join(
            str(part.get("thinking", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") == "thinking"
        )
        if blocks:
            return blocks
    extras = getattr(message, "additional_kwargs", None) or {}
    for key in ("reasoning_content", "reasoning"):
        found = extras.get(key)
        if isinstance(found, str) and found:
            return found
    return ""


def _calls_for(calls: tuple[ToolCall, ...]) -> list[dict[str, Any]]:
    """Ours, in LangChain's shape. `args` must be a mapping — a provider names arguments — so a
    call whose arguments are not one is carried under a single key rather than dropped.

    No `"type"`: `AIMessage` stamps `tool_call` on every entry itself, with a wrong value or with
    none, so writing one here is a literal no test could tell from its absence."""
    return [
        {
            "name": call.name,
            "args": call.arguments
            if isinstance(call.arguments, dict)
            else {"value": call.arguments},
            "id": call.id,
        }
        for call in calls
    ]


def _calls_of(message: BaseMessage) -> tuple[ToolCall, ...]:
    raw = getattr(message, "tool_calls", None) or ()
    return tuple(
        ToolCall(
            id=str(call.get("id") or ""), name=str(call.get("name")), arguments=call.get("args")
        )
        for call in raw
        if call.get("name")
    )


def _usage_of(message: BaseMessage) -> Usage | None:
    metadata = getattr(message, "usage_metadata", None)
    if not metadata:
        return None
    return Usage(
        input_tokens=metadata.get("input_tokens"),
        output_tokens=metadata.get("output_tokens"),
        cost_cents=None,
    )


__all__ = ["LangChainModel", "Price"]
