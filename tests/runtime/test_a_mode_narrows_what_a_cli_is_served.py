"""The registry serves a CLI a narrowed list too (D178, D179, phase 65, BUG-230).

The key-backed half of this is `tests/adapters/agent/test_a_mode_narrows_the_catalogue.py`. This is
the half that matters for the providers a product actually runs: Claude Code and Codex do not take a
catalogue as an argument — they **list the registry over MCP** and decide for themselves. So a
narrowing that only reached the in-process loop would leave `unmapped_behaviour`'s claim false for
every CLI, which is where it was read.

Two catalogues, one derivation (`narrowed`/`unanswered`). What is pinned here is that the served
list narrows, that a narrowed name is also **not callable** — a CLI holding a stale listing must not
reach past the narrowing — and that a resident CLI is told to list again when a `set_mode` changes
the narrowing under it.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from shadow_hdk.kernel import Completed, EffectProfile, ScopeSet
from shadow_hdk.runtime.offer import InProcessOffer, Narrowing
from shadow_hdk.runtime.testing import make_registration

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
READ = make_registration("read_it", effects=EffectProfile(reads=WORKSPACE))
WRITE = make_registration("write_it", effects=EffectProfile(writes=WORKSPACE))


async def _nothing(_inputs: Any) -> Completed:
    return Completed({"ok": True})


# ------------------------------------------------------------------ the narrowing is settable


def test_an_offer_starts_narrowed_to_nothing_which_means_everything() -> None:
    """The default is the whole of today's behaviour, and it is a *property*, not an absence."""
    offer = InProcessOffer(name="tools")

    assert offer.narrowing == ()


def test_the_narrowing_can_be_set_and_cleared() -> None:
    """Settable because a mode may change mid-thread (`set_mode`), so it cannot be a construction
    argument the way `withhold` is."""
    offer = InProcessOffer(name="tools")

    offer.narrow_to(("read_it",))
    assert offer.narrowing == ("read_it",)

    offer.narrow_to(())
    assert not offer.narrowing, "clearing it goes back to offering everything"


# ------------------------------------------------------------------ and it is enforced on a call


def test_shows_is_the_one_predicate_for_listing_and_for_calling() -> None:
    """A CLI lists once and calls later, so a narrowing enforced only on the listing is reachable
    by a caller holding a stale one — which is not a narrowing."""
    offer = InProcessOffer(name="tools", withhold=frozenset({"turn"}))

    offer.narrow_to(("read_it",))
    assert offer.shows("read_it")
    assert not offer.shows("write_it"), "outside the narrowing"
    assert not offer.shows("turn"), "withheld by the parent, narrowing or not"

    offer.narrow_to(())
    assert offer.shows("write_it"), "cleared, so everything the parent allows"
    assert not offer.shows("turn"), "clearing a narrowing does not un-withhold"


# ------------------------------------------- and a thread sets it from the mode, on a real turn


class _CliDouble:
    """A provider that calls the tools it was scripted to **through the registry the thread served
    it** — the way Claude Code and Codex do through the relay. The point of testing here rather than
    on the in-process catalogue: a CLI is never handed a list, it asks for one.
    """

    def __init__(self, names: tuple[str, ...]) -> None:
        self.names = names
        self.reach: Any = None
        self.refusals: list[str] = []

    async def open(self, **kw: Any) -> Any:
        return self

    async def turn(self, prompt: str) -> Any:
        from shadow_hdk.kernel import Turn

        for name in self.names:
            answered = await self.reach(name, {})
            reason = str(getattr(answered, "reason", "") or "")
            if reason:
                self.refusals.append(reason)
        return Turn(text="done")

    async def close(self) -> None:
        return None

    async def stream(self, prompt: str) -> Any:  # pragma: no cover
        raise NotImplementedError
        yield


async def _a_thread(root: Any, agent: _CliDouble, offered: tuple[str, ...]) -> Any:
    from shadow_hdk.adapters.basic import AllowAll
    from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec
    from shadow_hdk.kernel import Ceiling, Floor, Lease
    from shadow_hdk.kernel.providers import Behaviour
    from shadow_hdk.runtime import Ports
    from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink
    from shadow_hdk.runtime.threads import InMemoryThreads, Thread

    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=Ports(
            model=None,
            components=(InMemoryComponents([(READ, _nothing), (WRITE, _nothing)]),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=root,
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
        modes=ModeRegistry((ModeSpec.of("m", behaviour=Behaviour(tools_offered=offered)),)),
        mode="m",
    )
    agent.reach = thread.registry.call
    return thread


async def test_a_cli_calling_outside_its_modes_narrowing_is_refused(tmp_path: Any) -> None:
    """BUG-230 through the door a CLI actually uses."""
    agent = _CliDouble(("write_it",))
    thread = await _a_thread(tmp_path, agent, ("read_it",))
    try:
        async for _ in thread.turn("go"):
            pass
    finally:
        await thread.close()

    assert agent.refusals, "a name the mode did not offer must not be callable"
    assert "write_it" in agent.refusals[0], agent.refusals


async def test_a_cli_calling_inside_the_narrowing_is_not_refused(tmp_path: Any) -> None:
    """Paired, so the test above cannot pass because nothing was ever callable."""
    agent = _CliDouble(("read_it",))
    thread = await _a_thread(tmp_path, agent, ("read_it",))
    try:
        async for _ in thread.turn("go"):
            pass
    finally:
        await thread.close()

    assert agent.refusals == [], agent.refusals


async def test_a_mode_narrowing_nothing_leaves_every_tool_callable(tmp_path: Any) -> None:
    """Nothing that works today moves."""
    agent = _CliDouble(("read_it", "write_it"))
    thread = await _a_thread(tmp_path, agent, ())
    try:
        async for _ in thread.turn("go"):
            pass
    finally:
        await thread.close()

    assert agent.refusals == [], agent.refusals


async def test_a_mode_switch_renarrows_what_the_cli_may_call(tmp_path: Any) -> None:
    """The reason the narrowing is settable rather than a construction argument.

    A product switches what a step may look at by switching mode — the governed door (D175's
    reasoning). A narrowing fixed when the offer was built would mean the second mode ran under the
    first mode's list, which is the same class of bug as the agent not surviving a switch (BUG-234).
    """
    from shadow_hdk.adapters.basic import AllowAll
    from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec
    from shadow_hdk.kernel import Ceiling, Floor, Lease
    from shadow_hdk.kernel.providers import Behaviour
    from shadow_hdk.runtime import Ports
    from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink
    from shadow_hdk.runtime.threads import InMemoryThreads, Thread

    agent = _CliDouble(("write_it",))
    thread = await Thread.open(
        agent=cast(Any, agent),
        ports=Ports(
            model=None,
            components=(InMemoryComponents([(READ, _nothing), (WRITE, _nothing)]),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(40, 600, None), Floor(0)),
        modes=ModeRegistry(
            (
                ModeSpec.of("reading", behaviour=Behaviour(tools_offered=("read_it",))),
                ModeSpec.of("writing", behaviour=Behaviour(tools_offered=("write_it",))),
            )
        ),
        mode="reading",
    )
    agent.reach = thread.registry.call
    try:
        assert cast(Narrowing, thread.registry).narrowing == ("read_it",), cast(
            Narrowing, thread.registry
        ).narrowing

        await thread.set_mode("writing")

        assert cast(Narrowing, thread.registry).narrowing == ("write_it",), (
            "a mode switch must re-narrow, or the new mode runs under the old mode's list"
        )
        async for _ in thread.turn("go"):
            pass
    finally:
        await thread.close()

    assert agent.refusals == [], f"`write_it` is the new mode's own tool: {agent.refusals}"


# ----------------------------------------- and the LISTING narrows, not only the call (BUG-235)


async def test_the_served_listing_is_narrowed_not_only_the_call(tmp_path: Any) -> None:
    """A CLI asks for a list and then calls from it. Narrowing only the call leaves a model shown
    tools it cannot use — it picks one, is told *no component named ...*, and spends turns learning
    that. Worse than either half alone, and the shape of every *no tools* defect this kit has had.

    The first version of this group tested only the refusal, and the listing went unnarrowed. Pinned
    here against the server that actually answers a CLI's `tools/list`.
    """
    from typing import cast

    from shadow_hdk.adapters.basic import AllowAll
    from shadow_hdk.adapters.recording import RecordingServer
    from shadow_hdk.kernel import Ceiling, Composition, Floor, Invoke, Lease, Observation
    from shadow_hdk.runtime import Ports, RunOptions, current_run, run
    from shadow_hdk.runtime.testing import (
        FixedClock,
        InMemoryComponents,
        ListSink,
        make_registration,
    )

    seen: dict[str, Any] = {}
    DRIVE = make_registration("drive", effects=EffectProfile(reads=WORKSPACE))

    async def drive(_inputs: Any) -> Observation:
        context = current_run()
        assert context is not None
        server = RecordingServer(context)
        server.narrow_to(("read_it",))
        seen["listed"] = sorted(t.name for t in await server.tools())
        server.narrow_to(())
        seen["wide"] = sorted(t.name for t in await server.tools())
        return Completed({"ok": True})

    events = [
        _
        async for _ in run(
            Composition((Invoke("s1", DRIVE.id, ()),)),
            Ports(
                model=None,
                components=(
                    InMemoryComponents([(READ, _nothing), (WRITE, _nothing), (DRIVE, drive)]),
                ),
                governance=cast(Any, AllowAll()),
                sink=ListSink(),
                clock=FixedClock(),
            ),
            options=RunOptions(lease=Lease(Ceiling(20, 600, None), Floor(0))),
        )
    ]
    assert events

    assert seen["listed"] == ["read_it"], (
        f"the list a CLI is served must narrow, not only its calls: {seen['listed']}"
    )
    assert "write_it" in seen["wide"], "and clearing the narrowing restores the whole list"
