"""A provider given tools must not start its first turn before they can be reached (TD-023).

The kit hands a CLI a relay to launch and then writes it a prompt. Nothing waited in between, so
on a slow machine the CLI composed its tool list before the relay arrived and the turn ran with
none of the host's tools — and because the SDK says nothing about a server it dropped, that was
indistinguishable from an agent that chose to call nothing. Waiting is the fix; saying so when the
wait fails is what makes the remaining case visible instead of silent.
"""

from types import SimpleNamespace
from typing import Any

import pytest

from shadow_hdk.runtime.conversation import Conversation

pytestmark = pytest.mark.anyio


def conversation_with(*, sources: tuple[Any, ...], registry: Any, launched: bool = True) -> Any:
    class Provider:
        async def open(self, **kwargs: Any) -> Any:
            return SimpleNamespace(unmapped=(), launched_tool_servers=launched)

    conversation: Any = SimpleNamespace(
        session_id="",
        _agent=Provider(),
        _sources=sources,
        workspace=SimpleNamespace(primary=SimpleNamespace(path="/unused")),
        _behaviour_for_the_provider=lambda: None,
        _give_the_transcript_back=lambda session: None,
        _let_the_provider_wait_for_us=lambda session: None,
        _agent_carries=None,
        registry=registry,
    )
    # The real barrier, bound to this stand-in, so these controls exercise it rather than a double.
    conversation._wait_for_the_tools_to_be_reachable = lambda session: (
        Conversation._wait_for_the_tools_to_be_reachable(conversation, session)
    )
    return conversation


class Door:
    """An offer that reports whether its relay ever got in, and how long it was asked to wait."""

    def __init__(self, arrives: bool) -> None:
        self.arrives = arrives
        self.waited: float | None = None

    async def reached_once(self, within: float) -> bool:
        self.waited = within
        return self.arrives


async def test_a_relay_that_arrives_is_waited_for_and_reported_as_nothing() -> None:
    door = Door(arrives=True)
    conversation = conversation_with(sources=("relay",), registry=door)
    await Conversation._open_provider(conversation)
    assert door.waited is not None and door.waited > 0, "the run must actually wait"
    assert conversation.unmapped_behaviour == (), conversation.unmapped_behaviour


async def test_a_relay_that_never_arrives_is_named_not_left_to_look_quiet() -> None:
    door = Door(arrives=False)
    conversation = conversation_with(sources=("relay",), registry=door)
    await Conversation._open_provider(conversation)
    assert conversation.unmapped_behaviour == ("tools.unreached",), conversation.unmapped_behaviour


async def test_a_run_given_no_tools_does_not_wait_for_a_relay_it_never_asked_for() -> None:
    door = Door(arrives=False)
    conversation = conversation_with(sources=(), registry=door)
    await Conversation._open_provider(conversation)
    assert door.waited is None, "nothing was launched, so there is nothing to wait for"
    assert conversation.unmapped_behaviour == (), conversation.unmapped_behaviour


async def test_an_offer_that_cannot_answer_the_question_is_left_alone() -> None:
    """D14: growing the offer must break no adapter. An in-process offer has no door to watch."""
    conversation = conversation_with(sources=("relay",), registry=SimpleNamespace())
    await Conversation._open_provider(conversation)
    assert conversation.unmapped_behaviour == (), conversation.unmapped_behaviour


async def test_a_session_that_launched_nothing_is_never_waited_on() -> None:
    """Every key-backed session, and every double in this suite, launches no relay of its own.

    Waiting on the handed-out sources alone made each of them pay the whole deadline, which turned
    a five-minute suite into a crawl. The condition is what the session launched, not what the run
    was given.
    """
    door = Door(arrives=False)
    conversation = conversation_with(sources=("relay",), registry=door, launched=False)
    await Conversation._open_provider(conversation)
    assert door.waited is None, "a session with no relay of its own has nobody to wait for"
    assert conversation.unmapped_behaviour == (), conversation.unmapped_behaviour
