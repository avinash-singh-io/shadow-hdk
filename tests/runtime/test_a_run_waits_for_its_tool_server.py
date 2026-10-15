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


async def test_the_catalogue_is_announced_and_not_waited_for_before_the_prompt() -> None:
    """Measured: this provider asks for its tools when handed a prompt, not when it starts.

    So a wait before the prompt waits for what cannot happen yet. The first version did exactly
    that and spent the whole deadline on every turn — fifty seconds where the file took six.
    """
    registry = Registry(read_it=True)
    conversation = conversation_with(sources=("relay",), registry=registry)
    await Conversation._let_the_catalogue_be_seen(conversation, a_session())
    assert registry.order == ["announced"], registry.order
    assert registry.waited is None, "nothing may be waited for before the prompt"
    assert conversation.unmapped_behaviour == ()


async def test_a_catalogue_never_read_is_named_after_the_turn() -> None:
    registry = Registry(read_it=False)
    conversation = conversation_with(sources=("relay",), registry=registry)
    await Conversation._let_the_catalogue_be_seen(conversation, a_session())
    await Conversation._say_whether_the_catalogue_was_read(conversation, a_session())
    assert registry.announced == 1, "it must still have been announced"
    assert conversation.unmapped_behaviour == ("tools.unreached",), conversation.unmapped_behaviour


async def test_a_catalogue_that_was_read_is_not_named() -> None:
    registry = Registry(read_it=True)
    conversation = conversation_with(sources=("relay",), registry=registry)
    await Conversation._let_the_catalogue_be_seen(conversation, a_session())
    await Conversation._say_whether_the_catalogue_was_read(conversation, a_session())
    assert conversation.unmapped_behaviour == ()


async def test_many_turns_name_it_once() -> None:
    """A long conversation must not accumulate the same report per turn."""
    registry = Registry(read_it=False)
    conversation = conversation_with(sources=("relay",), registry=registry)
    for _ in range(3):
        await Conversation._say_whether_the_catalogue_was_read(conversation, a_session())
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


async def test_the_shipped_offer_answers_the_question_the_run_actually_asks() -> None:
    """The run holds the offer, not the server behind it — so the offer must answer.

    This control exists because it was missing. The wait was implemented on the server, the run
    asked the offer by name, nothing answered, and the barrier was skipped entirely while every
    unit control above passed against a stand-in that did have the method. A governed turn then
    ran with no tools. Asked of the shipped class here, so the two cannot drift apart again.
    """
    from shadow_hdk.adapters.recording import SocketOffer

    offer = SocketOffer()
    for question in ("offered_once", "changed", "attach", "detach"):
        assert hasattr(offer, question), f"the run asks for {question} and the offer must answer"
    # And it must answer with the server's own verdict, not merely exist.
    assert await offer.offered_once(0.01) is False, "nothing has listed yet"
    offer.holder.last_offered = ("read_file",)
    offer.holder._offered.set()
    assert await offer.offered_once(0.01) is True
