"""Canonical, secret-free authority and effect-transaction records (D99-D104).

These values describe what a host authorized; they never carry a credential, callback or policy
payload. Digests use canonical JSON so an authorization can bind exactly the values that crossed a
wire and a journal can be independently verified.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Literal

from pydantic import JsonValue

from shadow_hdk.kernel.effects import EffectProfile

EffectEntryKind = Literal[
    "staged",
    "authorized",
    "executing",
    "receipt",
    "refused",
    "failed",
    "unknown",
    "reconciled",
]


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class AuthoritySnapshot:
    """The host-controlled revisions that are relevant at one act."""

    principal: str | None
    workspace_revision: str
    policy_revision: str
    registry_revision: str
    provider_revision: str
    mode_revision: str

    @property
    def digest(self) -> str:
        return authority_digest(self)


def authority_digest(snapshot: AuthoritySnapshot) -> str:
    return _digest(asdict(snapshot))


def _scope_json(scope: object) -> dict[str, JsonValue]:
    names = sorted(getattr(scope, "names", ()))
    return {"names": names, "everything": bool(getattr(scope, "everything", False))}


def _effects_json(effects: EffectProfile) -> dict[str, JsonValue]:
    return {
        "reads": _scope_json(effects.reads),
        "writes": _scope_json(effects.writes),
        "reaches": effects.reaches,
        "reversible": effects.reversible,
        "contained": effects.contained,
        "costs": effects.costs,
    }


@dataclass(frozen=True)
class StagedEffect:
    """The exact irreversible component invocation for which authority is requested."""

    run_id: str
    step: str
    component: str
    inputs: JsonValue
    effects: EffectProfile
    authority_digest: str
    idempotency_key: str

    @property
    def digest(self) -> str:
        return _digest(
            {
                "run_id": self.run_id,
                "step": self.step,
                "component": self.component,
                "inputs": self.inputs,
                "effects": _effects_json(self.effects),
                "authority_digest": self.authority_digest,
                "idempotency_key": self.idempotency_key,
            }
        )


def stage_effect(
    *,
    run_id: str,
    step: str,
    component: str,
    inputs: JsonValue,
    effects: EffectProfile,
    authority_digest: str,
    idempotency_key: str,
) -> StagedEffect:
    return StagedEffect(
        run_id=run_id,
        step=step,
        component=component,
        inputs=inputs,
        effects=effects,
        authority_digest=authority_digest,
        idempotency_key=idempotency_key,
    )


@dataclass(frozen=True)
class EffectAuthorization:
    """A host grant for one stage under one authority snapshot; data, never executable power."""

    authorization_id: str
    stage_digest: str
    run_id: str
    step: str
    principal: str | None
    authority_digest: str
    expires_at: str
    idempotency_key: str

    def permits(self, effect: StagedEffect, authority: AuthoritySnapshot) -> bool:
        return (
            self.stage_digest == effect.digest
            and self.run_id == effect.run_id
            and self.step == effect.step
            and self.principal == authority.principal
            and self.authority_digest == authority.digest == effect.authority_digest
            and self.idempotency_key == effect.idempotency_key
        )


@dataclass(frozen=True)
class EffectEntry:
    """One immutable fact in an effect attempt's append-only history."""

    attempt_id: str
    sequence: int
    kind: EffectEntryKind
    stage_digest: str
    at: str
    authorization_id: str | None = None
    detail: JsonValue = None


__all__ = [
    "AuthoritySnapshot",
    "EffectAuthorization",
    "EffectEntry",
    "EffectEntryKind",
    "StagedEffect",
    "authority_digest",
    "stage_effect",
]
