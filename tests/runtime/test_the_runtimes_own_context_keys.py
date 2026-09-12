"""The runtime's own attributes are not a host's to set (TD-007, D30).

`context_for` tells a policy `posture` and `component` alongside whatever the host put in
`RunOptions.context` — and it wrote them **over** the host's values without a word. A host using
either name for its own purpose lost it silently, on every step, in the one message governance ever
sees.

Overwriting is the right outcome: D30 puts posture in front of governance precisely so that *only
controlled satisfies consent-before-effect* is a rule a policy can enforce rather than a sentence in
a document, and a value the host could set is a value a driver could influence. What was wrong is
that it was silent. These names are the runtime's, so a host using one is making a mistake, and a
mistake in what governance is told is worth a refusal at the door rather than a surprise per step.
"""

from __future__ import annotations

import pytest
from shadow_hdk.adapters.basic import AllowAll, CallableComponents

from shadow_hdk.kernel import Ceiling, Composition, Floor, Invoke, Lease, ScopeSet
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.session import RESERVED_ATTRIBUTES
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

WORKSPACE = ScopeSet.of("workspace")


def look() -> str:
    """Look something up."""
    return "found"


def ports() -> Ports:
    components = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    components.add(look, effects=EffectProfile(reads=WORKSPACE))
    return Ports(
        model=ScriptedModel(),
        components=(components,),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


async def drive(context: dict[str, str]) -> None:
    async for _event in run(
        Composition((Invoke("s1", "look"),)),
        ports(),
        options=RunOptions(lease=Lease(Ceiling(10, 600, 10_000), Floor(0)), context=context),
    ):
        pass


@pytest.mark.parametrize("reserved", sorted(RESERVED_ATTRIBUTES))
async def test_a_host_using_a_reserved_attribute_is_told(reserved: str) -> None:
    """Named at the door, and named individually, because a host that set one of two reserved keys
    should not have to work out which."""
    with pytest.raises(ValueError, match=reserved):
        await drive({reserved: "mine"})


async def test_a_host_may_still_say_anything_else() -> None:
    """The context is the host's to fill; two names are the exception, not the rule."""
    await drive({"mode": "build", "tenant": "acme", "posture_of_the_moon": "waxing"})


def test_the_reserved_names_are_the_ones_the_runtime_writes() -> None:
    """The pair must stay in step with `context_for`, or the guard protects the wrong words while
    the real ones are still overwritten in silence."""
    assert set(RESERVED_ATTRIBUTES) == {"posture", "component", "inputs"}
