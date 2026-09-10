"""A driver signs what it declares, and the signature is checked, not the name (D27).

`signed_by` has been on `Provenance` since Phase 0 and nothing has ever read it. What is signed here
is the registration's canonical form *including its effect profile*, so the signature binds to what
the driver declared: change the effects, and the signature no longer verifies. That is the whole
point — a driver cannot present narrower effects than it signed for.

Every refusal is tested, not only the acceptance. A test that a good signature verifies does not
test that a bad one is refused.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from shadow_hdk.kernel import Acted, EffectProfile, ScopeSet
from shadow_hdk.kernel.components import Registration
from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.runtime.testing import make_registration
from shadow_hdk.runtime.trust import sign, signing_bytes, verify

SECRET = b"a test fixture generated for this file and nothing else"
OTHER = b"a different fixture"
WORKSPACE = ScopeSet.of("workspace")

DRIVER = make_registration("send_email", effects=EffectProfile(reaches=True, reversible=False))


def _with(registration: Registration, **provenance: Any) -> Registration:
    return dataclasses.replace(
        registration,
        component=dataclasses.replace(
            registration.component,
            provenance=dataclasses.replace(registration.component.provenance, **provenance),
        ),
    )


# ---------------------------------------------------------------- the acceptance


def test_a_signed_registration_verifies_under_its_key() -> None:
    signed = sign(DRIVER, key_id="deployment-2026", secret=SECRET)
    assert signed.component.provenance.signed_by == "deployment-2026"
    assert signed.component.provenance.signature, "signing left no signature"
    assert verify(signed, SECRET) is True


def test_the_signature_survives_a_contract_round_trip() -> None:
    """A signature that did not cross the wire would be a proof that stayed at home."""
    signed = sign(DRIVER, key_id="k", secret=SECRET)
    back = load(dump(signed, Registration), Registration)
    assert back == signed
    assert verify(back, SECRET) is True


# ---------------------------------------------------------------- the refusals


def test_a_tampered_effect_profile_does_not_verify() -> None:
    """The point of signing the effects: a driver signed as reaching-and-irreversible cannot present
    itself as harmless under the same signature."""
    signed = sign(DRIVER, key_id="k", secret=SECRET)
    tampered = dataclasses.replace(
        signed,
        component=dataclasses.replace(signed.component, effects=EffectProfile(reads=WORKSPACE)),
    )
    assert verify(tampered, SECRET) is False


def test_a_tampered_id_does_not_verify() -> None:
    signed = sign(DRIVER, key_id="k", secret=SECRET)
    assert verify(dataclasses.replace(signed, id="delete_everything"), SECRET) is False


def test_a_tampered_interface_does_not_verify() -> None:
    signed = sign(DRIVER, key_id="k", secret=SECRET)
    renamed = dataclasses.replace(
        signed,
        component=dataclasses.replace(
            signed.component,
            interface=dataclasses.replace(signed.component.interface, description="harmless"),
        ),
    )
    assert verify(renamed, SECRET) is False


def test_the_wrong_key_does_not_verify() -> None:
    signed = sign(DRIVER, key_id="k", secret=SECRET)
    assert verify(signed, OTHER) is False


def test_an_unsigned_registration_does_not_verify() -> None:
    assert verify(DRIVER, SECRET) is False


def test_a_signature_copied_onto_another_registration_does_not_verify() -> None:
    """Replay: lifting a valid signature from one driver onto another."""
    signed = sign(DRIVER, key_id="k", secret=SECRET)
    other = make_registration(
        "wipe_disk", effects=EffectProfile(writes=WORKSPACE, reversible=False)
    )
    forged = _with(other, signed_by="k", signature=signed.component.provenance.signature)
    assert verify(forged, SECRET) is False


# ---------------------------------------------------------------- canonical


def test_signing_bytes_ignore_the_signature_itself() -> None:
    """The signature field is blanked before hashing — or signing would change what was signed
    and nothing could ever verify. The **key id** is not blanked: it is part of the claim, so a
    signature cannot be lifted and re-attributed to a different key. The first version of this test
    compared unsigned against signed and so contradicted the test below; this is the property."""
    signed = sign(DRIVER, key_id="k", secret=SECRET)
    blanked = _with(signed, signature=None)
    assert signing_bytes(signed) == signing_bytes(blanked)
    assert signing_bytes(signed) != signing_bytes(DRIVER), "the key id is part of what is signed"


def test_signing_bytes_cover_the_effects_and_the_provenance_claim() -> None:
    plain = signing_bytes(DRIVER)
    assert b"reaches" in plain
    assert signing_bytes(_with(DRIVER, signed_by="someone")) != plain


def test_signing_twice_with_the_same_key_is_the_same_signature() -> None:
    """Deterministic, so a second machine can re-sign and compare."""
    a = sign(DRIVER, key_id="k", secret=SECRET).component.provenance.signature
    b = sign(DRIVER, key_id="k", secret=SECRET).component.provenance.signature
    assert a == b


# ---------------------------------------------------------------- the receipt


def test_an_act_leaves_a_receipt_with_all_four_fields() -> None:
    receipt = Acted(
        foreign_id="msg_8f2",
        idempotency_key="run-1:step-3",
        exit="sent",
        grounds={"argv": ["send", "--to", "x"], "under": {"max_steps": 4}},
    )
    assert receipt.kind == "acted"
    back = load(dump(receipt, Acted), Acted)
    assert back == receipt


def test_an_acted_observation_is_one_of_the_observation_kinds() -> None:
    """It has to be in the union, or a wire client generated from the schema would not know it."""
    from shadow_hdk.kernel.contracts import CONTRACTS, round_trip

    receipt = Acted(foreign_id="x", idempotency_key="y", exit="ok", grounds=None)
    assert round_trip(receipt, CONTRACTS["Observation"]) == receipt


@pytest.mark.parametrize("missing", ["foreign_id", "idempotency_key", "exit"])
def test_a_receipt_cannot_omit_what_attributes_it(missing: str) -> None:
    fields = {"foreign_id": "x", "idempotency_key": "y", "exit": "ok", "grounds": None}
    del fields[missing]
    with pytest.raises(TypeError):
        Acted(**fields)  # type: ignore[arg-type]
