"""An MCP server's tools become components — tested against a real server, over a real pipe.

`tests/adapters/mcp/server.py` is an actual MCP server run as a subprocess. A seam tested against a
stand-in for the other side is a seam tested against your own idea of it, and this seam is the one
most components will arrive through.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from pydantic import JsonValue

from shadow_hdk.adapters.mcp import McpComponents, StdioServerParameters
from shadow_hdk.adapters.modes import Mode, ModeGovernance
from shadow_hdk.kernel import ASSUME_WORST, Completed, EffectProfile, Failed, ScopeSet
from shadow_hdk.kernel.ports import ComponentPort, Context
from tests.adapters.contract import ComponentPortContract

EVERYTHING = ScopeSet(everything=True)
PARAMS = StdioServerParameters(command=sys.executable, args=["tests/adapters/mcp/server.py"])


def server() -> McpComponents:
    return McpComponents(PARAMS, source="reference-server", at="2026-09-10T00:00:00+00:00")


async def profiles() -> dict[str, EffectProfile]:
    async with server() as components:
        return {
            registration.id: registration.component.effects
            for registration in await components.registrations()
        }


class TestMcpComponentsIsAComponentPort(ComponentPortContract):
    """The session is opened and closed **inside each test**.

    A first version used an autouse async fixture and every inherited test errored with
    *"Attempted to exit cancel scope in a different task than it was entered in"* — anyio refusing,
    correctly, to let a session cross tasks. That is a real constraint on this adapter and it is
    written down rather than worked around: an `McpComponents` belongs to whoever entered it.
    """

    @asynccontextmanager
    async def using(self) -> AsyncIterator[ComponentPort]:
        async with server() as components:
            await components.registrations()
            yield components

    def valid_call(self) -> tuple[str, JsonValue]:
        return "look_up", {"topic": "lathe"}


async def test_a_declared_tool_gets_the_narrow_profile_it_declared() -> None:
    look_up = (await profiles())["look_up"]
    assert look_up.writes == ScopeSet(), "read-only means it writes nothing"
    assert not look_up.reaches, "closed-world means it reaches nothing"
    assert look_up.reversible


async def test_read_only_does_not_buy_containment_or_a_free_lunch() -> None:
    """MCP's annotations cover about half our six fields. The rest stay at their worst, because a
    server saying it only reads has said nothing about whether it runs somewhere we trust."""
    look_up = (await profiles())["look_up"]
    assert not look_up.contained
    assert look_up.costs


async def test_a_destructive_tool_comes_out_irreversible() -> None:
    assert not (await profiles())["wipe"].reversible


async def test_a_tool_that_says_it_destroys_nothing_stays_reversible() -> None:
    """The only shape that tells the destructive hint apart from the default.

    MCP's default for an unstated `destructiveHint` is *destructive*, so a tool that omits it and a
    tool that ignores it look identical. `append` says `destructive_hint=False` explicitly — added
    after a mutation that dropped the hint left the suite green.
    """
    found = await profiles()
    assert found["append"].reversible
    assert not found["wipe"].reversible
    assert found["append"].writes.everything, "not read-only means it writes, we do not know where"


async def test_a_tool_that_declares_nothing_is_assumed_to_be_the_worst() -> None:
    """The property the open registry rests on. Nobody vouched for `mystery`, so it is treated as
    if it did everything — not as if it did nothing."""
    assert (await profiles())["mystery"] == ASSUME_WORST


async def test_a_mode_refuses_the_undeclared_tool_and_allows_the_declared_one() -> None:
    """End to end: the annotation is read, turned into effects, and *governed*. This is the whole
    argument for governing effects rather than names — nobody had to know these tools existed."""
    # `contained=False` in a **ceiling** means *uncontained is permitted* — which is the truthful
    # setting for a laptop with no sandbox. A first version left it at the default `True`, and the
    # mode correctly refused `look_up`: a server saying it only reads has said nothing about where
    # it runs. The test was wrong and the arithmetic was right.
    reading = Mode("read", EffectProfile(reads=EVERYTHING, costs=True, contained=False))
    governance = ModeGovernance({"read": reading}, default="read")
    context = Context(run_id="r", step="s")
    found = await profiles()
    assert (await governance.judge(found["look_up"], context)).kind == "allow"
    assert (await governance.judge(found["mystery"], context)).kind == "refuse"
    assert (await governance.judge(found["wipe"], context)).kind == "refuse"


async def test_a_call_comes_back_as_data() -> None:
    async with server() as components:
        await components.registrations()
        observation = await components.invoke("look_up", {"topic": "lathe"})
    assert isinstance(observation, Completed)
    assert isinstance(observation.output, dict)
    assert observation.output["asset"] == "LATHE-3"
    assert observation.output["mass_kg"] == 12
    assert observation.output["measured"] == "2026-08-01"


async def test_a_tool_that_raises_on_the_server_is_a_failed_observation_here() -> None:
    async with server() as components:
        await components.registrations()
        observation = await components.invoke("explode", {})
    assert isinstance(observation, Failed)
    assert "explode" in observation.error


async def test_a_transport_that_dies_mid_call_is_a_failed_observation() -> None:
    """The server is a process on the other end of a pipe, and processes die. When the transport
    raises rather than answering, the agent gets an observation it can route around — not a
    traceback out of `invoke`. Added after a mutation narrowed the `except` and nothing failed:
    every existing test exercised a server that answered, even when it answered with an error.
    """

    class Dies:
        async def call_tool(self, *args: object, **kw: object) -> object:
            raise ConnectionError("the pipe closed")

    async with server() as components:
        await components.registrations()
        components._session = Dies()  # type: ignore[assignment]  # noqa: SLF001
        observation = await components.invoke("look_up", {"topic": "lathe"})
    assert isinstance(observation, Failed)
    assert "ConnectionError" in observation.error and "pipe closed" in observation.error


async def test_an_adapter_that_was_never_started_says_so_rather_than_raising() -> None:
    observation = await server().invoke("look_up", {"topic": "lathe"})
    assert isinstance(observation, Failed)
    assert "not started" in observation.error


async def test_registrations_before_start_are_empty_rather_than_an_error() -> None:
    assert list(await server().registrations()) == []


async def test_the_schema_the_server_published_is_carried_verbatim() -> None:
    async with server() as components:
        registrations = {r.id: r for r in await components.registrations()}
    schema = registrations["look_up"].component.interface.input_schema
    assert isinstance(schema["properties"], dict)
    assert "topic" in schema["properties"]


async def test_provenance_says_which_server_and_which_adapter() -> None:
    async with server() as components:
        registration = next(iter(await components.registrations()))
    assert registration.component.provenance.registered_by == "reference-server"
    assert registration.component.provenance.adapter == "mcp"


async def test_a_deployment_may_expose_only_some_tools_under_its_own_names_and_vouch() -> None:
    """`only`, `aliases`, `effects` (D70): what a battery file says. The undeclared `mystery`
    tool, exposed under a vouched profile, is judged by that profile rather than assumed the
    worst — and the tools left out are not registered at all."""
    vouched = EffectProfile(reaches=True, contained=False)
    async with McpComponents(
        PARAMS,
        source="battery:test",
        only=["mystery", "look_up"],
        aliases={"mystery": "web_search"},
        effects={"mystery": vouched},
    ) as components:
        registrations = {r.id: r for r in await components.registrations()}
        assert set(registrations) == {"web_search", "look_up"}
        assert registrations["web_search"].component.effects == vouched
        assert registrations["web_search"].component.interface.name == "web_search"
        assert registrations["look_up"].component.effects != vouched, "unvouched stays derived"
        answer = await components.invoke("web_search", {"value": "?"})
        assert answer.kind == "completed", answer
