"""Reference host authority for the ready-made Shadow Harness (D99-D104)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from shadow_hdk.kernel import AuthoritySnapshot, EffectAuthorization, StagedEffect, Workspace
from shadow_hdk.kernel.ports import ClockPort, ComponentPort, Refuse
from shadow_hdk.runtime import current_run


def _plain(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _plain(asdict(value))
    if isinstance(value, dict):
        ordered = sorted(value.items(), key=lambda row: str(row[0]))
        return {str(key): _plain(item) for key, item in ordered}
    if isinstance(value, (list, tuple, set, frozenset)):
        return sorted(
            (_plain(item) for item in value),
            key=lambda item: json.dumps(item, sort_keys=True),
        )
    if isinstance(value, Path):
        return str(value)
    return value


def _revision(name: str, value: Any) -> str:
    encoded = json.dumps(
        _plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return f"{name}:sha256:{hashlib.sha256(encoded).hexdigest()}"


class HostAuthority:
    """Recompute the host facts that may move between consent and an irreversible act.

    The current run supplies identity, attributes and selected mode. Rules, modes and component
    registrations are read live; changing any of them moves the corresponding revision and makes
    an older grant unusable. The values are digests only—no policy object or credential crosses.
    """

    def __init__(
        self,
        *,
        workspace: Workspace,
        modes: Any,
        rules: Any,
        components: tuple[ComponentPort, ...],
        provider_revision: str,
        principal: str | None = None,
        attributes: dict[str, Any] | None = None,
        mode: str = "",
    ) -> None:
        self.workspace = workspace
        self.modes = modes
        self.rules = rules
        self.components = components
        self.provider_revision = provider_revision
        self.principal = principal
        self.attributes = dict(attributes or {})
        self.mode = mode
        self._workspace_revision = _revision("workspace", workspace)

    async def current(self, *, run_id: str, step: str) -> AuthoritySnapshot:
        principal = self.principal
        attributes = dict(self.attributes)
        selected_mode = self.mode
        context = current_run()
        if context is not None and context.run_id == run_id:
            governed = context.context(step)
            principal = governed.principal
            attributes = dict(governed.attributes)
            if isinstance(attributes.get("mode"), str):
                selected_mode = cast(str, attributes["mode"])

        rules = await self.rules.all_now(principal=principal, attributes=attributes)
        modes = await self.modes.all(principal=principal, attributes=attributes)
        selected = next((candidate for candidate in modes if candidate.id == selected_mode), None)
        registrations: list[Any] = []
        for port in self.components:
            registrations.extend(await port.registrations())

        return AuthoritySnapshot(
            principal=principal,
            workspace_revision=self._workspace_revision,
            policy_revision=_revision("policy", {"mode": selected, "rules": rules}),
            registry_revision=_revision("registry", registrations),
            provider_revision=_revision("provider", self.provider_revision),
            mode_revision=_revision("mode", selected),
        )


class HostAuthorizer:
    """Issue one short-lived grant after governance has admitted the exact staged act."""

    def __init__(self, clock: ClockPort, *, ttl_seconds: int = 300) -> None:
        self.clock = clock
        self.ttl_seconds = ttl_seconds

    async def authorize(
        self, effect: StagedEffect, current: AuthoritySnapshot
    ) -> EffectAuthorization | Refuse:
        expires = datetime.fromisoformat(self.clock.now()) + timedelta(seconds=self.ttl_seconds)
        return EffectAuthorization(
            authorization_id=f"authorization:{self.clock.new_id()}",
            stage_digest=effect.digest,
            run_id=effect.run_id,
            step=effect.step,
            principal=current.principal,
            authority_digest=current.digest,
            expires_at=expires.isoformat(),
            idempotency_key=effect.idempotency_key,
        )


__all__ = ["HostAuthority", "HostAuthorizer"]
