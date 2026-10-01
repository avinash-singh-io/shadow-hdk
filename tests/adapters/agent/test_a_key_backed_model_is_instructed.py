"""BUG-229: a key-backed model never received a mode's instructions, and the thread said it had.

Lane P wrote *"a key-backed model takes instructions and skills directly."* It did not.
`ModelSession.__init__` stored `behaviour` and nothing read it, so a mode's `system`,
`append_system`, `model`, `effort` and `temperature` all vanished into an attribute.

And the reporting made it worse. `Conversation` reads what a provider could not take **off the
session by name** — `getattr(session, "unmapped", ())` — and a `ModelSession` has no such
attribute, so `thread.unmapped_behaviour` came back empty, which a host reads as *your mode was
honoured in full*. Codex at least named what it dropped (ENH-020); this dropped in silence and
reported the opposite. That is what makes it a defect and not a gap: the field exists to say what
was not honoured, and it lied.

D168: a mode's words are **layered on** the pattern's system message, never replacing it — the
pattern carries the loop's own mechanics, and a `system` that replaced it would remove the
instructions that make the loop work.

D170: `effort` and `temperature` are named, honestly, because `ModelRequest` has nowhere to put
them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.adapters.modes.registry import ModeRegistry, ModeSpec
from shadow_hdk.kernel import Ceiling, Floor, Lease, ModelResponse
from shadow_hdk.kernel.ports import Message
from shadow_hdk.kernel.providers import Behaviour, Fragment
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, InMemoryComponents, ListSink
from shadow_hdk.runtime.threads import InMemoryThreads, Thread

pytestmark = pytest.mark.anyio


class Listening:
    """A `ModelPort` that keeps every request, so what a model was actually told is readable."""

    def __init__(self) -> None:
        self.asked: list[Any] = []

    async def complete(self, request: Any) -> ModelResponse:
        self.asked.append(request)
        return ModelResponse(text="done")

    async def stream(self, request: Any) -> Any:  # pragma: no cover — complete is enough here
        from shadow_hdk.kernel.ports import ModelChunk

        self.asked.append(request)
        yield ModelChunk(text="done", done=True)

    def system_said(self) -> str:
        systems = [
            m.content
            for request in self.asked
            for m in request.messages
            if isinstance(m, Message) and m.role == "system"
        ]
        return "\n".join(systems)


async def a_thread(root: Path, model: Listening, behaviour: Behaviour) -> Thread:
    from shadow_hdk.adapters.agent import ModelAgent, single

    modes = ModeRegistry((ModeSpec.of("worded", behaviour=behaviour),))
    return await Thread.open(
        agent=ModelAgent(model=cast(Any, model), pattern=single),
        ports=Ports(
            model=cast(Any, model),
            components=(InMemoryComponents([]),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=root,
        lease=Lease(Ceiling(20, 600, None), Floor(0)),
        modes=modes,
        mode="worded",
    )


# ------------------------------------------------------------------ it is instructed


async def test_a_modes_instructions_reach_a_key_backed_model(tmp_path: Path) -> None:
    model = Listening()
    thread = await a_thread(tmp_path, model, Behaviour(system="answer only in haiku"))
    try:
        async for _ in thread.turn("hello"):
            pass
    finally:
        await thread.close()

    assert "answer only in haiku" in model.system_said(), model.system_said()


async def test_append_system_reaches_it_too(tmp_path: Path) -> None:
    model = Listening()
    thread = await a_thread(
        tmp_path, model, Behaviour(system="be brief", append_system="cite every file")
    )
    try:
        async for _ in thread.turn("hello"):
            pass
    finally:
        await thread.close()

    said = model.system_said()
    assert "be brief" in said and "cite every file" in said, said


async def test_the_patterns_own_role_still_leads(tmp_path: Path) -> None:
    """D168. The pattern carries the loop's mechanics — how to call a tool, when to stop. A mode's
    `system` layers on it; replacing it would remove the instructions that make the loop work."""
    from shadow_hdk.adapters.agent import single

    pattern_says = single.system
    model = Listening()
    thread = await a_thread(tmp_path, model, Behaviour(system="answer only in haiku"))
    try:
        async for _ in thread.turn("hello"):
            pass
    finally:
        await thread.close()

    said = model.system_said()
    assert pattern_says[:40] in said, "the pattern's role was replaced rather than layered on"
    assert said.index(pattern_says[:40]) < said.index("answer only in haiku")


async def test_a_product_fragment_reaches_it_named(tmp_path: Path) -> None:
    """Lane P's ask 5: named, attributable, not an unmarked prefix."""
    model = Listening()
    thread = await a_thread(
        tmp_path,
        model,
        Behaviour(
            fragments=(
                Fragment(name="house-style", text="tabs, never spaces", source="the plugin"),
            )
        ),
    )
    try:
        async for _ in thread.turn("hello"):
            pass
    finally:
        await thread.close()

    said = model.system_said()
    assert "tabs, never spaces" in said, said
    assert "house-style" in said, "a fragment must say what it is"
    assert "the plugin" in said, "and where it came from"


async def test_the_model_a_mode_asks_for_is_the_model_that_is_asked(tmp_path: Path) -> None:
    """`ModelRequest.model` exists, so this one is honourable and must be honoured."""
    model = Listening()
    thread = await a_thread(tmp_path, model, Behaviour(model="a-particular-model"))
    try:
        async for _ in thread.turn("hello"):
            pass
    finally:
        await thread.close()

    assert model.asked, "nothing was asked"
    assert model.asked[0].model == "a-particular-model", model.asked[0].model


# ------------------------------------------------------------------ and it stops lying


async def test_a_key_backed_thread_names_what_it_cannot_take(tmp_path: Path) -> None:
    """The half that makes BUG-229 a defect. `effort` and `temperature` have nowhere to go in a
    `ModelRequest`, so they are **named** (D170) — where before, everything was reported as
    honoured."""
    model = Listening()
    thread = await a_thread(
        tmp_path, model, Behaviour(system="be brief", effort="high", temperature=0.2)
    )
    try:
        named = list(thread.unmapped_behaviour)
    finally:
        await thread.close()

    assert named == ["effort", "temperature"], named


async def test_what_it_can_take_is_not_named(tmp_path: Path) -> None:
    """The pair that keeps the above from being a blanket claim: a mode asking only for what a
    key-backed model can honour is reported as fully honoured, because it was."""
    model = Listening()
    thread = await a_thread(
        tmp_path, model, Behaviour(system="be brief", append_system="cite", model="m")
    )
    try:
        named = list(thread.unmapped_behaviour)
    finally:
        await thread.close()

    assert named == [], named


async def test_a_mode_that_sets_nothing_names_nothing(tmp_path: Path) -> None:
    model = Listening()
    thread = await a_thread(tmp_path, model, Behaviour())
    try:
        assert list(thread.unmapped_behaviour) == []
        async for _ in thread.turn("hello"):
            pass
        said = model.system_said()
    finally:
        await thread.close()

    assert "<context" not in said, "no fragments means no framing at all"
