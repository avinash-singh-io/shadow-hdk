"""The catalogue is readable before a run attaches, by the predicate a run would use (TD-023).

A listing is served out of the attached run, and a run attaches inside the turn — so a provider
that asks at startup is told, correctly, that there is nothing yet. An announcement afterwards only
helps a provider that re-reads before composing its request, and the gate caught one composing from
the stale list instead. The fix is to remove the empty answer, which means being able to compute the
listing with no run.

The danger in doing that is the one `bindings.py` names: the listing and the executor must resolve
the same way, or a model is offered what the runtime will refuse. BUG-235 is what that looks like.
So there is one predicate with two context sources, and the control that matters is the one
asserting both paths agree.
"""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from shadow_hdk.adapters.basic import AllowAll
from shadow_hdk.kernel import Refuse
from shadow_hdk.kernel.ports import GovernancePort
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.bindings import Catalogue
from shadow_hdk.runtime.registry import Registry
from shadow_hdk.runtime.testing import FixedClock, ListSink
from tests.adapters.recording.conftest import tools, with_a_run

pytestmark = pytest.mark.anyio


class RefusesReads:
    """A policy that hides anything which reads, so the two paths have something to disagree on."""

    async def judge(self, effects: Any, context: Any) -> Any:
        if getattr(effects, "reads", False):
            return Refuse("no reading here")
        return await AllowAll().judge(effects, context)


def a_catalogue(*, governance: GovernancePort | None = None) -> Catalogue:
    components = (tools(),)
    ports = Ports(
        components=components,
        governance=governance or AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    return Catalogue(ports, Registry(components, trust=ports.trust), attributes={})


async def test_the_catalogue_can_be_read_with_no_run_attached() -> None:
    """The whole point: a listing before the first turn, carrying the run's own tools."""
    names = [r.id for r in await a_catalogue().visible()]
    assert names, "a catalogue read before a run must not be empty"


async def test_the_policy_is_asked_even_with_no_run() -> None:
    """Not a bypass. A component the policy would refuse is absent here as it is in a run."""
    everything = {r.id for r in await a_catalogue().visible()}
    narrowed = {r.id for r in await a_catalogue(governance=RefusesReads()).visible()}
    assert narrowed < everything, (narrowed, everything)


async def test_the_pre_run_and_in_run_catalogues_are_the_same_catalogue() -> None:
    """The BUG-235 guard, and the reason the seam is safe to have at all.

    `bindings.py`: the listing and the executor resolve against the same registry so that what the
    model was offered and what the runtime will let it invoke cannot drift apart. A listing computed
    without a run has a context missing the turn's keys, so this asserts the two paths agree rather
    than assuming it.
    """

    async def inside(context: Any) -> list[str]:
        return sorted(r.id for r in await context.visible())

    in_run, _ = await with_a_run(inside)
    before = sorted(r.id for r in await a_catalogue().visible())
    assert before == [name for name in in_run if name != "driver"], (before, in_run)


class Remembers:
    """A policy that keeps what it was told, so the context can be asserted rather than assumed."""

    def __init__(self) -> None:
        self.seen: list[dict[str, Any]] = []

    async def judge(self, effects: Any, context: Any) -> Any:
        self.seen.append(dict(context.attributes))
        return await AllowAll().judge(effects, context)


async def test_the_policy_is_told_the_posture_and_the_component_with_no_run() -> None:
    """D30, which the pre-run path must honour exactly as a run does.

    The policy is told *what* it is judging — the component's id and its posture — so that
    "only controlled satisfies consent-before-effect" is a rule a policy can enforce rather than a
    sentence in a document. These two are the policy's and not the host's, and they used to be
    overridden silently (TD-007), so a second path that computed a listing without them would
    quietly reopen that.
    """
    policy = Remembers()
    components = (tools(),)
    ports = Ports(
        components=components,
        governance=policy,
        sink=ListSink(),
        clock=FixedClock(),
    )
    catalogue = Catalogue(
        ports,
        Registry(components, trust=ports.trust),
        identity="thread-1",
        # A host trying to speak for the policy about what is being judged.
        attributes={"posture": "pretend", "component": "pretend"},
    )
    shown = await catalogue.visible()
    assert shown, "nothing was judged, so nothing is proved"
    for told, registration in zip(policy.seen, shown, strict=True):
        assert told["component"] == registration.id, told
        assert told["posture"] == registration.component.provenance.posture, told
        assert told["posture"] != "pretend", "the host must not speak for the policy (D30, TD-007)"


async def test_a_registry_with_no_run_attached_answers_the_catalogue() -> None:
    """The point of the whole phase: a provider that asks at startup gets the real tools.

    Before this, a listing was served only out of the attached run, and a run attaches inside the
    turn — so the answer was honestly empty and a provider that composed from it had none of the
    host's tools. The registry now falls back to a catalogue read with no run.
    """
    from shadow_hdk.adapters.recording import SocketOffer

    components = (tools(),)
    ports = Ports(components=components, governance=AllowAll(), sink=ListSink(), clock=FixedClock())
    offer = SocketOffer(withhold={"turn"})
    assert await offer.holder.tools() == [], "with nothing supplied it must still answer honestly"

    offer.reads_from(Catalogue(ports, Registry(components, trust=ports.trust), identity="t1"))
    offered = [tool.name for tool in await offer.holder.tools()]
    assert offered, "a listing before any turn must carry the run's tools"
    assert "turn" not in offered, "what the offer withholds stays withheld on this path too"


async def test_the_conversation_gives_its_registry_a_catalogue_at_open() -> None:
    """Wired at open, where the components and the mode are known and only the run is not.

    Asked of the registry by name, so an offer that cannot answer before a run — an in-process one,
    or any predating this — is left alone (D14). The catalogue is told the conversation's own
    identity and attributes, with an empty turn, because there is no turn yet and a policy should
    be able to see that rather than be handed a fabricated one.
    """
    from shadow_hdk.runtime.conversation import Conversation

    given: list[Any] = []
    components = (tools(),)
    ports = Ports(components=components, governance=AllowAll(), sink=ListSink(), clock=FixedClock())
    conversation: Any = SimpleNamespace(
        id="thread-9",
        _ports=ports,
        registry=SimpleNamespace(reads_from=given.append),
        context_for=lambda turn: {"thread": "thread-9", "turn": turn},
    )
    Conversation._let_the_registry_answer_before_a_run(conversation)
    assert len(given) == 1, given
    catalogue = given[0]
    assert [r.id for r in await catalogue.visible()], "it must answer with the run's tools"

    # An offer that cannot answer before a run is left alone rather than broken.
    conversation.registry = SimpleNamespace()
    Conversation._let_the_registry_answer_before_a_run(conversation)
    assert len(given) == 1, "nothing more should have been handed over"


async def test_opening_the_conversation_actually_hands_the_catalogue_over() -> None:
    """That a method exists is not that it is called — how 0.48.0's own wait came to be inert.

    A mutation deleting the call from the open path left every control above green, because they
    all invoke the method directly. So this one drives `_start`, the real open path, and asserts the
    registry was given a catalogue there. The catalogue is also asked who it speaks for, since a
    wrong identity is the other thing nothing was measuring.
    """
    from shadow_hdk.runtime.conversation import Conversation

    given: list[Any] = []
    components = (tools(),)
    ports = Ports(components=components, governance=AllowAll(), sink=ListSink(), clock=FixedClock())

    class Offer:
        def reads_from(self, catalogue: Any) -> None:
            given.append(catalogue)

        @asynccontextmanager
        async def served(self) -> Any:
            yield ()

    conversation: Any = SimpleNamespace(
        id="thread-7",
        _ports=ports,
        registry=Offer(),
        context_for=lambda turn: {"thread": "thread-7", "turn": turn},
        _open_provider=lambda: _nothing(),
    )
    # The real wiring method, bound to this stand-in, so `_start` exercises it rather than a double.
    conversation._let_the_registry_answer_before_a_run = lambda: (
        Conversation._let_the_registry_answer_before_a_run(conversation)
    )
    await Conversation._start(conversation)
    assert len(given) == 1, "opening must hand the registry a catalogue"
    assert given[0].context().run_id == "thread-7", given[0].context()
    assert given[0].context().attributes.get("turn") == "", (
        "there is no turn yet, and it must say so"
    )


async def _nothing() -> None:
    return None
