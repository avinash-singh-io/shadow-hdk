"""Modes as a registry: a policy, a behaviour and a presentation, as data (D64).

The policy half is this adapter's `Mode`/`ModeGovernance` — governance over effect profiles. A
`ModeSpec` adds the behaviour (who the model is) and the presentation (id, name, description a host
shows); a `ModeRegistry` is the set. The three shipped defaults live here, one per environment
mode — out of the example (D48, D64). The runtime's `Thread` reads a registry structurally: it
never imports this adapter, so a product may hand in its own.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, fields, replace
from typing import Any, Protocol

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


class ModeSource(Protocol):
    """Where modes come from beyond the ones handed in: files, a store (D66)."""

    async def modes(self) -> tuple[ModeSpec, ...]: ...

    async def problems(self) -> tuple[str, ...]: ...


class ModeRegistry:
    """The modes a host offers — the ones handed in, then each source in order, later shadowing
    earlier by id. `find` reads the sources every time, which is what makes a row written now a
    mode at the next read (principle 10); `get`/`listing`/`policies` are the last snapshot, for
    callers that cannot await."""

    def __init__(self, specs: Iterable[ModeSpec] = (), *, sources: Sequence[ModeSource] = ()):
        self._handed: dict[str, ModeSpec] = {spec.id: spec for spec in specs}
        self._by_id: dict[str, ModeSpec] = dict(self._handed)
        self.sources: tuple[ModeSource, ...] = tuple(sources)
        self._problems: tuple[str, ...] = ()

    async def refresh(self) -> None:
        merged = dict(self._handed)
        problems: list[str] = []
        for source in self.sources:
            for spec in await source.modes():
                merged[spec.id] = spec
            problems.extend(await source.problems())
        self._by_id = merged
        self._problems = tuple(problems)

    async def find(self, mode_id: str) -> ModeSpec | None:
        await self.refresh()
        return self._by_id.get(mode_id)

    async def all(self) -> tuple[ModeSpec, ...]:
        await self.refresh()
        return tuple(self._by_id.values())

    async def problems(self) -> tuple[str, ...]:
        await self.refresh()
        return self._problems

    def listing(self) -> Sequence[ModeSpec]:
        return list(self._by_id.values())

    def get(self, mode_id: str) -> ModeSpec | None:
        return self._by_id.get(mode_id)

    def policies(self) -> dict[str, Policy]:
        return {spec.id: replace(spec.policy, name=spec.id) for spec in self._by_id.values()}


def governance_for(
    registry: ModeRegistry, *, default: str, key: str = "mode", rules: Any = None
) -> ModeGovernance:
    """`ModeGovernance` over the registry itself — one selection, by the context key `mode`,
    read at every judgement so a mode added to a source is judged from at the next step (D66) —
    consulting the host's `ActRules` after it says *ask* (D65)."""
    return ModeGovernance(registry, default=default, key=key, rules=rules)


SHIPPED_POLICY_IDS = ("read-only", "ask", "workspace-write", "full")


def policy_named(name: str) -> Policy | None:
    """A shipped policy by the mode id that carries it — what a file or a row names instead of
    authoring effect profiles by hand (D66)."""
    for spec in shipped_modes():
        if spec.id == name:
            return spec.policy
    return None


def mode_from_document(document: Any, *, source: str) -> ModeSpec:
    """A mode from the JSON a file or a row carries: `id`, `name`, `description`, `policy` (the
    id of a shipped policy — never effects by hand), `behaviour` (a `Behaviour`'s fields).
    Raises `ValueError` naming what is wrong."""
    if not isinstance(document, dict):
        raise ValueError("a mode is a table")
    mode_id = str(document.get("id", "") or "")
    if not mode_id:
        raise ValueError("a mode needs an id")
    policy_name = str(document.get("policy", "") or "")
    policy = policy_named(policy_name) if policy_name else None
    if policy is None:
        raise ValueError(
            f"mode {mode_id!r} names policy {policy_name!r}, which is not one of "
            f"{list(SHIPPED_POLICY_IDS)}"
        )
    raw = document.get("behaviour", {}) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"mode {mode_id!r}: behaviour is a table")
    known = {f.name for f in fields(Behaviour)}
    if unknown := sorted(set(raw) - known):
        raise ValueError(f"mode {mode_id!r}: unknown behaviour field(s) {', '.join(unknown)}")
    made: dict[str, Any] = dict(raw)
    if "tools_offered" in made:
        made["tools_offered"] = tuple(made["tools_offered"])
    return ModeSpec.of(
        mode_id,
        policy=policy,
        name=str(document.get("name", "") or ""),
        description=str(document.get("description", "") or ""),
        behaviour=Behaviour(**made),
        source=source,
    )


class StoreModes:
    """Modes from a `Store`'s `modes` collection, reloaded only when its version moved."""

    def __init__(self, store: Any, collection: str = "modes") -> None:
        self._store = store
        self._collection = collection
        self._seen = -1
        self._modes: tuple[ModeSpec, ...] = ()
        self._problems: tuple[str, ...] = ()

    async def _load(self) -> None:
        version = await self._store.version(self._collection)
        if version == self._seen:
            return
        modes: list[ModeSpec] = []
        problems: list[str] = []
        for key, row in await self._store.list(self._collection):
            try:
                modes.append(mode_from_document(row, source="store"))
            except ValueError as wrong:
                problems.append(f"{self._collection}/{key}: {wrong}")
        self._modes, self._problems, self._seen = tuple(modes), tuple(problems), version

    async def modes(self) -> tuple[ModeSpec, ...]:
        await self._load()
        return self._modes

    async def problems(self) -> tuple[str, ...]:
        await self._load()
        return self._problems


def store_modes(store: Any, collection: str = "modes") -> StoreModes:
    return StoreModes(store, collection)


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


def _asking() -> Policy:
    """The workspace is the ceiling, and anything that changes it is asked about first — the mode
    every coding CLI opens in (Claude Code's *default*, Codex's *on-request*). Found wanting
    through the demo: the shipped three had no band between *refuse* and *allow inside*, so a
    person could never be asked about a write, and "approve and add a rule" had nothing to
    answer."""
    return Policy(
        "ask",
        ceiling=EffectProfile(
            reads=EVERYTHING,
            writes=OURS,
            reaches=True,
            reversible=False,
            contained=True,
            costs=True,
        ),
        ask_above=EffectProfile(
            reads=EVERYTHING,
            writes=PROVIDER,
            reaches=True,
            reversible=False,
            contained=True,
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
    """The four the harness ships: one per environment mode (D48, D64), and `ask` — the
    workspace-write environment with a question before every change."""
    return (
        ModeSpec.of(
            "read-only",
            policy=_looking(),
            description="Look, don't touch: nothing in the workspace is written or run.",
        ),
        ModeSpec.of(
            "ask",
            policy=_asking(),
            description="Ask before every write or command inside the workspace; approve once, "
            "or keep a rule.",
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


__all__ = [
    "ModeRegistry",
    "ModeSource",
    "ModeSpec",
    "StoreModes",
    "governance_for",
    "mode_from_document",
    "policy_named",
    "shipped_modes",
    "store_modes",
]
