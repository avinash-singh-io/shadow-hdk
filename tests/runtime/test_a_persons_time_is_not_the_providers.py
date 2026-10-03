"""Time the kit spends answering a provider's call is given back to it (D182, phase 65, BUG-233).

The ceiling's own arithmetic is pinned in
`tests/adapters/jsonl/test_a_person_is_not_a_slow_provider.py`. What is pinned here is the wiring,
since without it `waited_for_us` is a method nobody calls.

A CLI that calls a tool is silent until we answer. Answering means routing the call through the
run — judged, recorded, and where the policy says so **put to the person, who may take twenty
minutes** (D58). That silence is ours, not the provider's, and charging it to the provider's
patience failed turns with *the provider did not finish* about a person yet to answer.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.kernel import Ceiling, Completed, EffectProfile, Floor, Lease, ScopeSet, Turn
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.offer import InProcessOffer
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)
from shadow_hdk.runtime.threads import InMemoryThreads, Thread

pytestmark = pytest.mark.anyio

SLOW = make_registration("takes_a_while", effects=EffectProfile(reads=ScopeSet.of("workspace")))


async def _slowly(_inputs: Any) -> Completed:
    await asyncio.sleep(0.15)
    return Completed({"ok": True})


class _CliDouble:
    """A provider that calls one tool through the registry, and records what it was told about its
    own patience — the way `JsonlSession` would be told."""

    def __init__(self) -> None:
        self.reach: Any = None
        self.given_back: list[float] = []

    def waited_for_us(self, seconds: float) -> None:
        self.given_back.append(seconds)

    async def open(self, **kw: Any) -> Any:
        return self

    async def turn(self, prompt: str) -> Turn:
        await self.reach("takes_a_while", {})
        return Turn(text="done")

    async def close(self) -> None:
        return None

    async def stream(self, prompt: str) -> Any:  # pragma: no cover
        raise NotImplementedError
        yield


async def a_thread(root: Path, agent: _CliDouble) -> Thread:
    return await Thread.open(
        agent=cast(Any, agent),
        ports=Ports(
            model=None,
            components=(InMemoryComponents([(SLOW, _slowly)]),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=root,
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
    )


# ------------------------------------------------------------------ the wiring


async def test_a_provider_is_told_how_long_the_kit_took_to_answer_it(tmp_path: Path) -> None:
    """Without this the give-back is a method nobody calls."""
    agent = _CliDouble()
    thread = await a_thread(tmp_path, agent)
    agent.reach = thread.registry.call
    try:
        async for _ in thread.turn("go"):
            pass
    finally:
        await thread.close()

    assert agent.given_back, "the provider was never told what the kit spent on its behalf"
    assert agent.given_back[0] >= 0.15, (
        f"it must be the real duration, not a constant: {agent.given_back}"
    )


async def test_a_provider_that_cannot_be_told_is_left_alone(tmp_path: Path) -> None:
    """Every key-backed session is one: it has no pipe to go quiet on, so it has no such method and
    must not be reached for one. D14 — growing this breaks no adapter."""

    class _Mute:
        def __init__(self) -> None:
            self.reach: Any = None

        async def open(self, **kw: Any) -> Any:
            return self

        async def turn(self, prompt: str) -> Turn:
            await self.reach("takes_a_while", {})
            return Turn(text="done")

        async def close(self) -> None:
            return None

        async def stream(self, prompt: str) -> Any:  # pragma: no cover
            raise NotImplementedError
            yield

    agent = _Mute()
    thread = await a_thread(tmp_path, cast(Any, agent))
    agent.reach = thread.registry.call
    try:
        async for _ in thread.turn("go"):
            pass
    finally:
        await thread.close()

    told = getattr(thread.registry, "answering", None)
    assert told is None, "a session with no patience must not be wired to one"


# ------------------------------------------------------------------ and the offer measures it


async def test_an_offer_with_nobody_listening_routes_as_it_always_did() -> None:
    """The hook is optional, so a host's own composition that never sets it is unchanged."""
    offer = InProcessOffer(name="tools")

    assert offer.answering is None
    refused = await offer.call("anything", {})

    assert "no turn is running" in str(getattr(refused, "reason", "")), refused


async def test_a_call_refused_before_it_was_routed_reports_nothing() -> None:
    """Nothing was answered, so there is no time to give back — and reporting zero would train a
    reader to believe the number means something it does not."""
    told: list[float] = []
    offer = InProcessOffer(name="tools")
    offer.answering = told.append

    await offer.call("anything", {})

    assert told == [], told


async def test_a_hosts_own_offer_that_cannot_take_the_hook_does_not_break_the_thread(
    tmp_path: Path,
) -> None:
    """`Offer` is a port a host may implement, and it does **not** require `answering` — so an
    implementation with no room for the attribute must be left alone rather than written to.

    A `__slots__` class is the case that bites: setting an undeclared attribute on one raises, so
    without the guard a thread opened on such an offer would fail at open. D14 — growing this port
    breaks no adapter, including one nobody here wrote.
    """
    from collections.abc import AsyncIterator, Mapping
    from contextlib import asynccontextmanager

    from pydantic import JsonValue

    from shadow_hdk.kernel import Observation, Refused, ToolSource
    from shadow_hdk.runtime.bindings import RunContext

    class Spartan:
        """A minimal `Offer` with no room for anything it was not born with."""

        __slots__ = ("_context",)

        def __init__(self) -> None:
            self._context: RunContext | None = None

        @property
        def name(self) -> str:
            return "spartan"

        def attach(self, context: RunContext) -> None:
            self._context = context

        def detach(self) -> None:
            self._context = None

        @asynccontextmanager
        async def served(self) -> AsyncIterator[tuple[ToolSource, ...]]:
            yield ()

        async def call(
            self, name: str, arguments: Mapping[str, JsonValue] | None = None
        ) -> Observation:
            return Refused("this offer offers nothing")

        async def changed(self) -> None:
            return None

    agent = _CliDouble()
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=Ports(
            model=None,
            components=(InMemoryComponents([(SLOW, _slowly)]),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
        registry=cast(Any, Spartan()),
    )
    agent.reach = thread.registry.call
    try:
        async for _ in thread.turn("go"):
            pass
    finally:
        await thread.close()

    assert agent.given_back == [], "an offer that cannot measure reports nothing"
