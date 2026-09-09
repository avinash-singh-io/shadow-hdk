"""A port may grow a method, if it grows a default with it (D14).

`09` §3 says a *port* is added with a refuse-not-crash default. `stream` is a method on an existing
port, which is the same rule one level down: an adapter that ignores it keeps working, and one that
can do better overrides it. The five adapters written in Phase 0 needed no edit, and that is the
property asserted here.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from shadow_hdk.kernel.ports import (
    Message,
    ModelChunk,
    ModelPort,
    ModelRequest,
    ModelResponse,
    ToolCall,
    Usage,
)

A_REQUEST = ModelRequest((Message("user", "how heavy is the lathe?"),))


class OnlyCompletes(ModelPort):
    """An adapter written before `stream` existed. It is not edited; it inherits."""

    async def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            text="twelve kilograms",
            tool_calls=(ToolCall(id="c1", name="weigh", arguments={"what": "lathe"}),),
            usage=Usage(10, 3, 2),
        )


class ReallyStreams(ModelPort):
    async def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(text="twelve kilograms", usage=Usage(10, 3, 2))

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelChunk]:
        for word in ("twelve", " kilo", "grams"):
            yield ModelChunk(text=word)
        yield ModelChunk(usage=Usage(10, 3, 2), done=True)


async def test_an_adapter_that_ignores_stream_keeps_working() -> None:
    chunks = [chunk async for chunk in OnlyCompletes().stream(A_REQUEST)]
    assert len(chunks) == 1
    assert chunks[0].text == "twelve kilograms"
    assert chunks[0].tool_calls[0].name == "weigh"
    assert chunks[0].usage == Usage(10, 3, 2)
    assert chunks[0].done


async def test_the_default_is_honest_rather_than_pretend() -> None:
    """A provider that answers all at once really does produce one chunk. The default does not
    chop the answer into fake deltas to look like streaming."""
    chunks = [chunk async for chunk in OnlyCompletes().stream(A_REQUEST)]
    assert [c.text for c in chunks] == ["twelve kilograms"]


async def test_text_is_the_delta_not_the_accumulation() -> None:
    chunks = [chunk async for chunk in ReallyStreams().stream(A_REQUEST)]
    assert [c.text for c in chunks] == ["twelve", " kilo", "grams", ""]
    assert "".join(c.text for c in chunks) == (await ReallyStreams().complete(A_REQUEST)).text


async def test_the_last_chunk_carries_what_it_cost() -> None:
    chunks = [chunk async for chunk in ReallyStreams().stream(A_REQUEST)]
    assert chunks[-1].done
    assert chunks[-1].usage == Usage(10, 3, 2)
    assert [c for c in chunks if c.usage is not None] == [chunks[-1]]
