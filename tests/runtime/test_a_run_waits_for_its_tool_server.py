"""A resident provider is told the catalogue exists, and waited for until it has read it (TD-023).

The registry answers a listing out of the attached run, and a run attaches inside the turn. So
before the first prompt there is nothing to list and the honest answer is empty — which is what a
provider that asks at startup receives. Nothing then told it otherwise, because the change
notification fires for roots and for a mode change and never for a catalogue that has only now
become available, so a governed run could begin with none of the host's tools while both sides
behaved exactly as written.

These controls pin the order that can work, and with it the two mistakes that looked like it:
waiting for a connection, and waiting for any listing at all.
"""

from types import SimpleNamespace
from typing import Any

import pytest

from shadow_hdk.runtime.conversation import Conversation

pytestmark = pytest.mark.anyio


class Registry:
    """An offer that records being announced, and reports whether a listing carried tools."""

    def __init__(self, *, read_it: bool) -> None:
        self.read_it = read_it
        self.announced = 0
        self.waited: float | None = None
        self.order: list[str] = []

    async def changed(self) -> None:
        self.announced += 1
        self.order.append("announced")

    async def offered_once(self, within: float) -> bool:
        self.waited = within
        self.order.append("waited")
        return self.read_it


def conversation_with(*, sources: tuple[Any, ...], registry: Any) -> Any:
    conversation: Any = SimpleNamespace(_sources=sources, registry=registry, unmapped_behaviour=())
    return conversation


def a_session(*, launched: bool = True) -> Any:
    return SimpleNamespace(launched_tool_servers=launched)


async def test_the_catalogue_is_announced_before_it_is_waited_for() -> None:
    """Announcing after waiting would be useless: the provider would have nothing to re-read."""
    registry = Registry(read_it=True)
    conversation = conversation_with(sources=("relay",), registry=registry)
    await Conversation._let_the_catalogue_be_seen(conversation, a_session())
    assert registry.order == ["announced", "waited"], registry.order
    assert registry.waited is not None and registry.waited > 0
    assert conversation.unmapped_behaviour == ()


async def test_a_catalogue_never_read_is_named_not_left_to_look_quiet() -> None:
    registry = Registry(read_it=False)
    conversation = conversation_with(sources=("relay",), registry=registry)
    await Conversation._let_the_catalogue_be_seen(conversation, a_session())
    assert registry.announced == 1, "it must still have been announced"
    assert conversation.unmapped_behaviour == ("tools.unreached",), conversation.unmapped_behaviour


async def test_a_session_that_launched_nothing_is_neither_told_nor_waited_on() -> None:
    """Every key-backed session, and every double in this suite. Waiting on the handed-out sources
    alone made each of them pay the whole deadline, at about ten seconds a test."""
    registry = Registry(read_it=False)
    conversation = conversation_with(sources=("relay",), registry=registry)
    await Conversation._let_the_catalogue_be_seen(conversation, a_session(launched=False))
    assert (registry.announced, registry.waited) == (0, None)
    assert conversation.unmapped_behaviour == ()


async def test_a_run_given_no_tools_is_left_alone() -> None:
    registry = Registry(read_it=False)
    conversation = conversation_with(sources=(), registry=registry)
    await Conversation._let_the_catalogue_be_seen(conversation, a_session())
    assert (registry.announced, registry.waited) == (0, None)
    assert conversation.unmapped_behaviour == ()


async def test_an_offer_that_cannot_report_is_left_alone() -> None:
    """D14: growing the offer must break no adapter. An in-process offer serves no catalogue over a
    wire, so it is neither announced to nor waited for."""
    registry = SimpleNamespace()
    conversation = conversation_with(sources=("relay",), registry=registry)
    await Conversation._let_the_catalogue_be_seen(conversation, a_session())
    assert conversation.unmapped_behaviour == ()
