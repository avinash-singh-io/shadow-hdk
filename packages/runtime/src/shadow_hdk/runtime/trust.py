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

from shadow_hdk.kernel.components import Registration
from shadow_hdk.kernel.contracts import dump


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


__all__ = ["sign", "signing_bytes", "verify"]
