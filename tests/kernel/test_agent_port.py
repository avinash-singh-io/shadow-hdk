"""The second seam: a provider that owns its own loop (D39, D22).

`ModelPort` asks a model to *propose* — messages and tool schemas in, text and tool calls out, and
the caller drives. A subscription does not sell that. It sells an agent: a prompt in, work done, a
stream out, and it decides for itself how many turns that took and which tool to reach for.

So the port is shaped around what it can honestly promise. **The tool calls do not come back through
it** — that is the point of D42. They leave through the injected registry and land on the run's own
graph, judged and leased and recorded. What comes back here is what the agent *said* and what it
*spent*, because those are the two things only the provider knows.

Residency is in the contract rather than in one adapter. Phase 4 measured why: a child agent is
expensive to start and a five-step composition must not be five cold starts. `AcpAgent` learned that
alone; `AgentSession` is that lesson lifted into the shape every provider has to satisfy.
"""

from __future__ import annotations

from shadow_hdk.kernel import AgentPort, AgentSession, ToolSource, Turn, Usage


class Recorded(AgentSession):
    """The smallest thing that satisfies the session contract."""

    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.closed = False

    async def turn(self, prompt: str) -> Turn:
        self.prompts.append(prompt)
        return Turn(text=f"did: {prompt}", usage=Usage(10, 5, 2), stop_reason="end_turn")

    async def close(self) -> None:
        self.closed = True


class Provider(AgentPort):
    def __init__(self) -> None:
        self.opened_with: list[tuple[ToolSource, ...]] = []
        self.session = Recorded()

    async def open(
        self, *, tools: tuple[ToolSource, ...] = (), workspace: str | None = None
    ) -> AgentSession:
        self.opened_with.append(tools)
        return self.session


REGISTRY = ToolSource(kind="mcp", address="shadow-hdk://run/registry")


async def test_a_session_takes_a_turn_and_says_what_it_did_and_spent() -> None:
    session = await Provider().open()

    done = await session.turn("write the file")

    assert done.text == "did: write the file"
    assert done.usage is not None and done.usage.cost_cents == 2
    assert done.stop_reason == "end_turn"


async def test_a_session_is_resident_across_turns() -> None:
    """Phase 4's measurement, in the contract: one process per conversation, not one per turn."""
    provider = Provider()
    session = await provider.open()

    await session.turn("first")
    again = await provider.open()
    await again.turn("second")

    assert provider.session.prompts == ["first", "second"]
    assert again is session, "opening twice started a second agent"


async def test_the_registry_is_handed_over_at_open() -> None:
    """D42's socket: the provider is told where its tools are, and they are ours."""
    provider = Provider()

    await provider.open(tools=(REGISTRY,))

    assert provider.opened_with == [(REGISTRY,)]


async def test_a_session_closes() -> None:
    provider = Provider()
    session = await provider.open()

    await session.close()

    assert provider.session.closed


async def test_streaming_has_a_default_that_does_not_pretend(  # noqa: D103
) -> None:
    """D14, one level down, exactly as `ModelPort.stream` does it: a method added to a port later
    gets a default that works, and the default does **not** chop one answer into fake deltas."""
    session = await Provider().open()

    chunks = [chunk async for chunk in session.stream("go")]

    assert len(chunks) == 1
    assert chunks[0].text == "did: go"
    assert chunks[0].done is True
