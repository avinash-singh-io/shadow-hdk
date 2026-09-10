"""A driver signs what it declares (D27).

What is signed is the registration's **canonical form** — id, interface, effect profile, labels,
and provenance minus the signature itself — so the signature binds to the declared effects. Change
the effects and it no longer verifies. That is the whole point: a driver cannot present narrower
effects than it signed for, and one whose declaration was edited after signing is refused as
forged rather than merely re-judged.

**HMAC-SHA256, from the standard library, symmetric on purpose.** The deployment both mints and
verifies its driver keys, so the trust boundary is *keys this deployment holds*. Asymmetric signing
would be a dependency for a property nobody has asked for yet; the day a driver arrives from
somebody the deployment shares no secret with, that is ADR-1's marketplace question.

Lives in the runtime rather than an adapter because the registry is the one funnel every component
passes through, and because no adapter may import another (`tests/invariants`).
"""

from __future__ import annotations

import dataclasses
import hashlib
import hmac
import json
from collections.abc import Mapping

from shadow_hdk.kernel.components import Registration
from shadow_hdk.kernel.contracts import dump
from shadow_hdk.kernel.effects import EffectProfile


def signing_bytes(registration: Registration) -> bytes:
    """The canonical form with the signature blanked — identical before and after signing, or
    signing would change what was signed and nothing could ever verify."""
    blank = _with_signature(registration, None)
    canonical = json.loads(dump(blank, Registration))
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sign(registration: Registration, *, key_id: str, secret: bytes) -> Registration:
    """The same registration, with `signed_by` naming the key and `signature` holding its proof."""
    claimed = _with_signed_by(registration, key_id)
    digest = hmac.new(secret, signing_bytes(claimed), hashlib.sha256).hexdigest()
    return _with_signature(claimed, digest)


def verify(registration: Registration, secret: bytes) -> bool:
    """True only for a signature this secret would have produced over exactly this declaration."""
    given = registration.component.provenance.signature
    if not given:
        return False
    expected = hmac.new(secret, signing_bytes(registration), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, given)


def _with_signature(registration: Registration, signature: str | None) -> Registration:
    return dataclasses.replace(
        registration,
        component=dataclasses.replace(
            registration.component,
            provenance=dataclasses.replace(registration.component.provenance, signature=signature),
        ),
    )


def _with_signed_by(registration: Registration, key_id: str) -> Registration:
    return dataclasses.replace(
        registration,
        component=dataclasses.replace(
            registration.component,
            provenance=dataclasses.replace(registration.component.provenance, signed_by=key_id),
        ),
    )


@dataclasses.dataclass(frozen=True)
class Trust:
    """What a deployment trusts: keys by id, the ids it has withdrawn, which effects need proof.

    `must_sign` is an effect ceiling, not a predicate (D23 applies): a driver whose declared effects
    do not narrow it must carry a signature. `None` verifies only what claims one — the honest
    default until ADR-1 says which effects must be signed at all.

    Checked on **every** refresh, never remembered: a key revoked between two refreshes is refused
    on the second. Trust is a list the deployment keeps, not a memory the registry forms.
    """

    keys: Mapping[str, bytes]
    revoked: frozenset[str] = frozenset()
    must_sign: EffectProfile | None = None

    def __post_init__(self) -> None:
        if self.must_sign is not None and not isinstance(self.must_sign, EffectProfile):
            raise TypeError(
                f"must_sign is an EffectProfile or None, not {type(self.must_sign).__name__}"
            )

    def refusal(self, registration: Registration) -> str | None:
        """Why this registration may not enter the catalogue, or `None` if it may.

        A registration with no signature is admitted only where nothing requires one. One that
        claims a signature is held to it: the key must be known, not revoked, and the signature
        must verify over exactly what was declared. Revocation is checked **before** verification
        so a revoked key is refused for that reason, however valid its signature.
        """
        provenance = registration.component.provenance
        signature, key = provenance.signature, provenance.signed_by
        if signature is None:
            if self.must_sign is None or registration.component.effects.narrows(self.must_sign):
                return None
            return f"{registration.id}: declares effects that must be signed, and is not signed"
        if key is None:
            return f"{registration.id}: carries a signature but names no key"
        if key in self.revoked:
            return f"{registration.id}: signed by revoked key {key}"
        if key not in self.keys:
            return f"{registration.id}: signed by unknown key {key}"
        if not verify(registration, self.keys[key]):
            return f"{registration.id}: signature by {key} does not verify over what it declares"
        return None


__all__ = ["Trust", "sign", "signing_bytes", "verify"]
