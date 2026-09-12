"""Modes as a registry: a policy, a behaviour and a presentation, as data (D64).

The policy half is this adapter's `Mode`/`ModeGovernance` — governance over effect profiles. A
`ModeSpec` adds the behaviour (who the model is) and the presentation (id, name, description a host
shows); a `ModeRegistry` is the set. The three shipped defaults live here, one per environment
mode — out of the example (D48, D64). The runtime's `Thread` reads a registry structurally: it
never imports this adapter, so a product may hand in its own.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from shadow_hdk.adapters.modes.mode import Mode as Policy
from shadow_hdk.adapters.modes.mode import ModeGovernance

from shadow_hdk.kernel import Behaviour, EffectProfile, ScopeSet

EVERYTHING = ScopeSet(everything=True)
OURS = ScopeSet.of("workspace", "record", "provider-state")
PROVIDER = ScopeSet.of("provider-state")
"""What holding a turn writes whatever the mode: the provider's own state, never the root."""


@dataclass(frozen=True)
class ModeSpec:
    """One mode: its presentation, its policy, its behaviour."""

    id: str
    policy: Policy
    name: str = ""
    description: str = ""
    behaviour: Behaviour = field(default_factory=Behaviour)
    source: str = "shipped"

    @classmethod
    def of(
        cls,
        mode_id: str,
        *,
        policy: Policy | None = None,
        name: str = "",
        description: str = "",
        behaviour: Behaviour | None = None,
        source: str = "shipped",
    ) -> ModeSpec:
        return cls(
            id=mode_id,
            policy=policy or Policy(mode_id, EffectProfile(reads=EVERYTHING, costs=True)),
            name=name or mode_id.replace("-", " ").title(),
            description=description,
            behaviour=behaviour or Behaviour(),
            source=source,
        )


class ModeRegistry:
    """The modes a host offers, later shadowing earlier by id — shipped, files, a store."""

    def __init__(self, specs: Iterable[ModeSpec] = ()) -> None:
        self._by_id: dict[str, ModeSpec] = {}
        for spec in specs:
            self._by_id[spec.id] = spec

    def listing(self) -> Sequence[ModeSpec]:
        return list(self._by_id.values())

    def get(self, mode_id: str) -> ModeSpec | None:
        return self._by_id.get(mode_id)

    def policies(self) -> dict[str, Policy]:
        return {spec.id: replace(spec.policy, name=spec.id) for spec in self._by_id.values()}


def governance_for(
    registry: ModeRegistry, *, default: str, key: str = "mode", rules: Any = None
) -> ModeGovernance:
    """`ModeGovernance` over a registry's policies — one selection, by the context key `mode` —
    consulting the host's `ActRules` after it says *ask* (D65)."""
    return ModeGovernance(registry.policies(), default=default, key=key, rules=rules)


def _looking() -> Policy:
    return Policy(
        "read-only",
        EffectProfile(
            reads=EVERYTHING,
            writes=PROVIDER,
            reaches=True,
            reversible=False,
            contained=False,
            costs=True,
        ),
    )


def _confined() -> Policy:
    return Policy(
        "workspace-write",
        ceiling=EffectProfile(
            reads=EVERYTHING,
            writes=OURS,
            reaches=True,
            reversible=False,
            contained=True,
            costs=True,
        ),
    )


def _open() -> Policy:
    return Policy(
        "full",
        ceiling=EffectProfile(
            reads=EVERYTHING,
            writes=EVERYTHING,
            reaches=True,
            reversible=False,
            contained=False,
            costs=True,
        ),
        ask_above=EffectProfile(
            reads=EVERYTHING,
            writes=OURS,
            reaches=True,
            reversible=False,
            contained=False,
            costs=True,
        ),
    )


def shipped_modes() -> tuple[ModeSpec, ...]:
    """The three the harness ships, one per environment mode (D48, D64)."""
    return (
        ModeSpec.of(
            "read-only",
            policy=_looking(),
            description="Look, don't touch: nothing in the workspace is written or run.",
        ),
        ModeSpec.of(
            "workspace-write",
            policy=_confined(),
            description="Write and run inside the workspace, confined by the OS sandbox.",
        ),
        ModeSpec.of(
            "full",
            policy=_open(),
            description="Reach the whole machine; a write outside the workspace is asked about.",
        ),
    )


__all__ = ["ModeRegistry", "ModeSpec", "governance_for", "shipped_modes"]
