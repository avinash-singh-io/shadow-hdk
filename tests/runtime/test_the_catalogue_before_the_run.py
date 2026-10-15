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
