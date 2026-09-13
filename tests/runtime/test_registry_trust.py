"""A driver that cannot prove itself is absent, and says why (D27).

Checked in the registry's one funnel, at refresh, so a driver that fails is **absent from the
catalogue** — Phase 3's rule that the model never sees a tool it may not use — rather than refused
per call. Every refusal is tested by name, and the one that matters most is a **revoked key with a
valid signature**, because that is the case revocation exists for.

`must_sign` is an effect ceiling: anything not narrowing it must be signed. `None` means verify only
what claims a signature — the honest default until ADR-1 says which effects must be signed at all.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Floor,
    Invoke,
    Lease,
    Observation,
    ScopeSet,
)
from shadow_hdk.kernel.components import Registration, RegistrationId
from shadow_hdk.runtime import Ports, RunOptions, current_run, run
from shadow_hdk.runtime.registry import Registry
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel, make_registration
from shadow_hdk.runtime.trust import Trust, sign

SECRET = b"fixture-key-one"
OTHER = b"fixture-key-two"
WORKSPACE = ScopeSet.of("workspace")
READS = EffectProfile(reads=WORKSPACE)
REACHES = EffectProfile(reaches=True, reversible=False)

LOOK = make_registration("look", effects=READS)
SEND = make_registration("send_email", effects=REACHES)


class Port:
    """A component port over whatever registrations a test hands it."""

    def __init__(self, *registrations: Registration) -> None:
        self._registrations = list(registrations)

    async def registrations(self) -> Sequence[Registration]:
        return self._registrations

    async def invoke(self, _r: RegistrationId, _i: JsonValue) -> Observation:
        return Completed("ran")


def trust(
    *, must_sign: EffectProfile | None = None, revoked: frozenset[str] = frozenset()
) -> Trust:
    return Trust(keys={"k1": SECRET, "k2": OTHER}, revoked=revoked, must_sign=must_sign)


async def _admitted(registry: Registry) -> set[str]:
    await registry.refresh()
    return {r.id for r in registry.all()}


# ---------------------------------------------------------------- admitted


async def test_a_driver_signed_by_a_trusted_key_is_admitted() -> None:
    registry = Registry([Port(sign(SEND, key_id="k1", secret=SECRET))], trust=trust())
    assert await _admitted(registry) == {"send_email"}
    assert registry.refused == []


async def test_with_no_trust_configured_nothing_is_checked() -> None:
    """A registry without a `Trust` behaves as it always has. Trust is opt-in until ADR-1."""
    registry = Registry([Port(SEND, LOOK)])
    assert await _admitted(registry) == {"send_email", "look"}


async def test_an_unsigned_registration_inside_must_sign_is_admitted() -> None:
    """Reading the workspace narrows a ceiling that permits reads; it need not be signed."""
    registry = Registry([Port(LOOK)], trust=trust(must_sign=READS))
    assert await _admitted(registry) == {"look"}


# ---------------------------------------------------------------- refused, each by name


async def test_an_unsigned_registration_outside_must_sign_is_refused() -> None:
    registry = Registry([Port(SEND)], trust=trust(must_sign=READS))
    assert await _admitted(registry) == set()
    assert len(registry.refused) == 1
    assert "send_email" in registry.refused[0] and "signed" in registry.refused[0]


async def test_a_signature_by_an_unknown_key_is_refused() -> None:
    signed = sign(SEND, key_id="nobody", secret=b"whatever")
    registry = Registry([Port(signed)], trust=trust())
    assert await _admitted(registry) == set()
    assert "nobody" in registry.refused[0]


async def test_a_revoked_key_is_refused_even_with_a_valid_signature() -> None:
    """The case revocation exists for. The signature verifies; the trust does not."""
    signed = sign(SEND, key_id="k1", secret=SECRET)
    registry = Registry([Port(signed)], trust=trust(revoked=frozenset({"k1"})))
    assert await _admitted(registry) == set()
    assert "revoked" in registry.refused[0] and "k1" in registry.refused[0]


async def test_a_forged_signature_is_refused() -> None:
    signed = sign(SEND, key_id="k1", secret=OTHER)  # claims k1, signed with k2's secret
    registry = Registry([Port(signed)], trust=trust())
    assert await _admitted(registry) == set()
    assert "verify" in registry.refused[0]


async def test_a_declaration_edited_after_signing_is_refused() -> None:
    """The point of signing the effects. A driver signed as reaching cannot present as harmless."""
    import dataclasses

    signed = sign(SEND, key_id="k1", secret=SECRET)
    softened = dataclasses.replace(
        signed, component=dataclasses.replace(signed.component, effects=READS)
    )
    registry = Registry([Port(softened)], trust=trust())
    assert await _admitted(registry) == set()


async def test_a_revoked_key_is_refused_as_revoked_whatever_its_signature() -> None:
    """Revocation is a fact about the key, not the signature: once withdrawn, nothing is verified.

    The key here is revoked, unknown to `keys`, and the signature is forged. Every one of those
    would refuse; the reason must be the actionable one — somebody revoked it on purpose."""
    signed = sign(SEND, key_id="gone", secret=b"not-the-secret")
    registry = Registry([Port(signed)], trust=trust(revoked=frozenset({"gone"})))
    assert await _admitted(registry) == set()
    assert "revoked" in registry.refused[0]
    assert "unknown" not in registry.refused[0] and "verify" not in registry.refused[0]


async def test_a_signature_that_names_no_key_is_refused_as_such() -> None:
    """Not 'unknown key None': a signature with no `signed_by` is a malformed claim, and says so."""
    import dataclasses

    signed = sign(SEND, key_id="k1", secret=SECRET)
    nameless = dataclasses.replace(
        signed,
        component=dataclasses.replace(
            signed.component,
            provenance=dataclasses.replace(signed.component.provenance, signed_by=None),
        ),
    )
    registry = Registry([Port(nameless)], trust=trust())
    assert await _admitted(registry) == set()
    assert "no key" in registry.refused[0] and "unknown" not in registry.refused[0]


async def test_refused_is_this_refresh_not_a_history() -> None:
    """Like `unreachable`: what was refused *now*. Two refreshes of one bad driver is one reason."""
    registry = Registry([Port(SEND)], trust=trust(must_sign=READS))
    await registry.refresh()
    await registry.refresh()
    assert len(registry.refused) == 1


async def test_revocation_is_checked_at_every_refresh_not_remembered() -> None:
    """A key revoked between two refreshes is refused on the second. Trust is a list, not memory."""
    signed = sign(SEND, key_id="k1", secret=SECRET)
    live = trust()
    registry = Registry([Port(signed)], trust=live)
    assert await _admitted(registry) == {"send_email"}
    registry.trust = trust(revoked=frozenset({"k1"}))
    assert await _admitted(registry) == set()


async def test_one_bad_driver_does_not_take_the_good_ones_with_it() -> None:
    registry = Registry(
        [Port(sign(SEND, key_id="k1", secret=SECRET), sign(LOOK, key_id="nobody", secret=b"x"))],
        trust=trust(),
    )
    assert await _admitted(registry) == {"send_email"}
    assert len(registry.refused) == 1


# ---------------------------------------------------------------- through a run


async def test_a_refused_driver_is_absent_from_what_the_model_is_offered() -> None:
    """Not greyed out: absent. `visible()` is what the catalogue is built from."""
    seen: list[set[str]] = []

    async def look(_i: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        seen.append({r.id for r in await context.visible()})
        return Completed(None)

    from shadow_hdk.adapters.basic import AllowAll
    from shadow_hdk.runtime.testing import InMemoryComponents

    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(LOOK, look)]), Port(SEND)),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
        trust=trust(must_sign=READS),
    )
    async for _ in run(
        Composition((Invoke("s1", LOOK.id),)),
        ports,
        options=RunOptions(lease=Lease(Ceiling(10, 600, 100), Floor(0))),
    ):
        pass
    assert seen and "send_email" not in seen[0]
    assert "look" in seen[0]


def test_trust_refuses_a_ceiling_it_cannot_compare() -> None:
    """`must_sign` is an effect profile, not a predicate (D23 applies)."""
    with pytest.raises(TypeError):
        Trust(keys={}, revoked=frozenset(), must_sign="reaching")  # type: ignore[arg-type]
