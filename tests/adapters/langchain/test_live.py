"""The same adapter against a real provider.

**Opt-in, and deselected by default.** These cost money, so `pyproject.toml` carries
`-m "not live"` in `addopts` and a normal `uv run pytest` never calls anybody. To run them:

    source <your env with INTENT_HF_TOKEN>
    uv run pytest -m live

What they prove is the half a fake cannot: that a real provider's wire shape — its tool-call ids,
its `usage_metadata`, its streaming chunks — survives the translation. Everything else about the
adapter is asserted in `test_langchain.py`, for free.

The endpoint is HuggingFace Inference Providers, which is OpenAI-compatible, so this exercises the
same code path as OpenAI, Together, Groq, vLLM and most self-hosted servers.
"""

from __future__ import annotations

import os

import pytest
from shadow_hdk.adapters.langchain import LangChainModel

from shadow_hdk.kernel import Interface
from shadow_hdk.kernel.ports import Message, ModelRequest

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("INTENT_HF_TOKEN"),
        reason="INTENT_HF_TOKEN is not set; the live check is opt-in because it costs money",
    ),
]

MODEL = os.environ.get("SHADOW_HDK_LIVE_MODEL_ID", "deepseek-ai/DeepSeek-V4-Flash:deepinfra")
BASE_URL = os.environ.get("SHADOW_HDK_LIVE_BASE_URL", "https://router.huggingface.co/v1")

WEIGH = Interface(
    name="weigh",
    description="Weigh a thing and return its mass in kilograms.",
    input_schema={
        "type": "object",
        "properties": {"what": {"type": "string"}},
        "required": ["what"],
    },
)


def live() -> LangChainModel:
    return LangChainModel(
        MODEL,
        model_provider="openai",
        base_url=BASE_URL,
        api_key=os.environ["INTENT_HF_TOKEN"],
        temperature=0,
    )


async def test_a_real_provider_answers() -> None:
    response = await live().complete(
        ModelRequest((Message("user", "Reply with exactly: twelve kilograms"),))
    )
    assert "twelve" in response.text.lower()


async def test_a_real_provider_reports_tokens_and_not_money() -> None:
    """The point of the rule, on a real wire: the provider counts tokens and quotes no price, so
    `cost_cents` is `None` — unknown — and the meter says so instead of adding zero."""
    response = await live().complete(ModelRequest((Message("user", "Say: ok"),)))
    assert response.usage is not None
    assert response.usage.input_tokens and response.usage.input_tokens > 0
    assert response.usage.cost_cents is None


async def test_a_real_tool_call_round_trips() -> None:
    response = await live().complete(
        ModelRequest(
            (Message("user", "How heavy is the lathe? Use the weigh tool."),),
            tools=(WEIGH,),
        )
    )
    assert response.tool_calls, f"no tool call in {response!r}"
    call = response.tool_calls[0]
    assert call.name == "weigh"
    assert isinstance(call.arguments, dict) and "what" in call.arguments
    assert call.id


async def test_a_real_stream_is_translated_faithfully() -> None:
    """What is asserted is the **adapter**, never the provider's temperament.

    A first version of this test asserted `len(chunks) > 2` and failed — and the measurement said
    the assertion was wrong, not the code: over this route the model returns five frames of which
    exactly one carries words, so the honest translation is one text chunk and a final one. A test
    that demands a provider stream token-by-token is testing somebody else's server.

    Multi-chunk streaming is proven against the fake in `test_langchain.py`, where the deltas are
    ours to choose. Here the question is whether a real wire shape survives: deltas concatenate to
    the answer, exactly one chunk says it is the last, and cost arrives at the end or not at all.
    """
    chunks = [
        chunk
        async for chunk in live().stream(
            ModelRequest((Message("user", "Count from one to five, words only."),))
        )
    ]
    assert chunks, "a stream that yields nothing is not a stream"
    assert "".join(c.text for c in chunks).strip(), "the deltas concatenate to an answer"
    assert chunks[-1].done and not any(c.done for c in chunks[:-1])
    priced = [c for c in chunks if c.usage is not None]
    assert priced in ([], [chunks[-1]])
    assert all(c.text for c in chunks[:-1]), "empty deltas are noise and are not yielded"


async def test_a_real_provider_accepts_a_second_turn(caplog: object) -> None:
    """BUG-005 on a real wire, which is the only place it could be seen: a tool result must be
    preceded by the assistant message that made the call. Every unit test used `ScriptedModel`,
    which never checked, so the suite was green while a real second turn would have been rejected.
    """
    model = live()
    first = await model.complete(
        ModelRequest(
            (Message("user", "How heavy is the lathe? Use the weigh tool."),), tools=(WEIGH,)
        )
    )
    assert first.tool_calls, f"no tool call to answer in {first!r}"
    call = first.tool_calls[0]
    second = await model.complete(
        ModelRequest(
            (
                Message("user", "How heavy is the lathe? Use the weigh tool."),
                Message("assistant", first.text, tool_calls=first.tool_calls),
                Message("tool", '{"kilograms": 812}', tool_call_id=call.id),
            ),
            tools=(WEIGH,),
        )
    )
    assert "812" in second.text, f"the provider did not use the answer it was given: {second!r}"
