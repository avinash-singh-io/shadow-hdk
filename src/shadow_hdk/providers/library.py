"""Providers are files, and a bad file is refused at load (D40).

The shipped library sits beside this module, the way the agent adapter's patterns sit beside theirs
(D17). A team adds a provider by adding a file; only a genuinely new transport costs an adapter.

**An unknown key is an error.** A loader that shrugs at `strip_evn = ["CLAUDECODE"]` produces a
provider that parses, loads, and then silently fails to start on exactly the machines the field
existed for. The refusal names the file and the key, because a library of twenty files and an error
naming none of them is not a diagnosis.
"""

from __future__ import annotations

import tomllib
from dataclasses import fields
from pathlib import Path
from typing import Any, get_args

from pydantic import TypeAdapter, ValidationError

from shadow_hdk.kernel import (
    BehaviourArg,
    Delta,
    Dialect,
    EnvVar,
    Provider,
    ProviderCapabilities,
    ProviderKind,
)

HERE = Path(__file__).resolve().parent / "library"

TUPLE_FIELDS = {
    "fallback_bins",
    "version_probe",
    "auth_probe",
    "auth_failure_patterns",
    "launch_args",
    "strip_env",
    "backfill_env",
}
KNOWN = {f.name for f in fields(Provider)}
KINDS = set(get_args(ProviderKind))
CAPABILITY_FIELDS = {f.name for f in fields(ProviderCapabilities)}
CAPABILITIES = TypeAdapter(ProviderCapabilities)


class MalformedProvider(ValueError):
    """A provider file that cannot be believed. Naming the file and the field is the whole job."""


def load_provider(path: Path) -> Provider:
    """One file, one provider."""
    try:
        raw: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as broken:
        raise MalformedProvider(f"{path.name}: {broken}") from broken
    return provider_from_data(raw, where=path.name)


def provider_from_data(raw: dict[str, Any], *, where: str) -> Provider:
    """A provider from the document a file or a store row carries (D66) — the same checks."""
    raw = dict(raw)
    if unknown := sorted(set(raw) - KNOWN):
        raise MalformedProvider(
            f"{where}: unknown field(s) {', '.join(unknown)} — a typo here produces a provider "
            f"that loads and does not work"
        )
    for required in ("id", "kind", "bin"):
        if not raw.get(required):
            raise MalformedProvider(f"{where}: {required} is required")
    if raw["kind"] not in KINDS:
        raise MalformedProvider(
            f"{where}: kind {raw['kind']!r} is neither seam — it is 'model' or 'agent' (D39)"
        )

    made = dict(raw)
    for name in TUPLE_FIELDS:
        if name in made:
            made[name] = tuple(made[name])
    if "capabilities" in made:
        spoken = made["capabilities"]
        if not isinstance(spoken, dict):
            raise MalformedProvider(f"{where}: capabilities must be a table")
        if unknown_here := sorted(set(spoken) - CAPABILITY_FIELDS):
            names = ", ".join(f"capabilities.{name}" for name in unknown_here)
            raise MalformedProvider(f"{where}: unknown field(s) {names}")
        try:
            made["capabilities"] = CAPABILITIES.validate_python(spoken)
        except ValidationError as wrong:
            first = wrong.errors()[0]
            loc = ".".join(str(part) for part in first["loc"])
            if not loc and "evidence" in str(first["msg"]):
                loc = "evidence"
            path = f"capabilities.{loc}" if loc else "capabilities"
            raise MalformedProvider(f"{where}: {path}: {first['msg']}") from wrong
    if "dialect" in made:
        spoken = made["dialect"]
        if not isinstance(spoken, dict):
            raise MalformedProvider(f"{where}: dialect must be a table")
        unknown_here = sorted(set(spoken) - {f.name for f in fields(Dialect)})
        if unknown_here:
            raise MalformedProvider(f"{where}: unknown dialect field(s) {', '.join(unknown_here)}")
        for name, value in list(spoken.items()):
            if isinstance(value, list):
                spoken[name] = tuple(value)
        if "behaviour_args" in spoken:
            try:
                spoken["behaviour_args"] = tuple(
                    BehaviourArg(field=a["field"], flag=a["flag"]) for a in spoken["behaviour_args"]
                )
            except (KeyError, TypeError) as wrong:
                raise MalformedProvider(
                    f"{where}: each dialect.behaviour_args entry needs field and flag"
                ) from wrong
        if "deltas" in spoken:
            try:
                spoken["deltas"] = tuple(
                    Delta(on=d["on"], kind=d["kind"], at=d["at"]) for d in spoken["deltas"]
                )
            except (KeyError, TypeError) as wrong:
                raise MalformedProvider(
                    f"{where}: each dialect.deltas entry needs on, kind and at"
                ) from wrong
        if "session_gone_matches" in spoken and not all(
            isinstance(m, str) and m for m in spoken["session_gone_matches"]
        ):
            raise MalformedProvider(f"{where}: dialect.session_gone_matches is a list of strings")
        made["dialect"] = Dialect(**spoken)
    if "set_env" in made:
        try:
            made["set_env"] = tuple(
                EnvVar(name=e["name"], value=e["value"]) for e in made["set_env"]
            )
        except (KeyError, TypeError) as wrong:
            raise MalformedProvider(f"{where}: set_env wants name and value ({wrong})") from wrong
    try:
        return Provider(**made)
    except TypeError as wrong:
        raise MalformedProvider(f"{where}: {wrong}") from wrong


def shipped() -> dict[str, Provider]:
    """Every provider that ships with this package, by id."""
    return {p.id: p for p in (load_provider(f) for f in sorted(HERE.glob("*.toml")))}


def load_dir(where: Path) -> dict[str, Provider]:
    """A team's own library — the same shape, somewhere else."""
    return {p.id: p for p in (load_provider(f) for f in sorted(Path(where).glob("*.toml")))}


class StoreProviders:
    """Providers from a `Store`'s `providers` collection (D66): the same document a file carries,
    reloaded only when the collection's version moved. A malformed row is reported, not loaded."""

    def __init__(self, store: Any, collection: str = "providers") -> None:
        self._store = store
        self._collection = collection
        self._seen = -1
        self._providers: dict[str, Provider] = {}
        self._problems: tuple[str, ...] = ()

    async def providers(self) -> dict[str, Provider]:
        version = await self._store.version(self._collection)
        if version != self._seen:
            found: dict[str, Provider] = {}
            problems: list[str] = []
            for key, row in await self._store.list(self._collection):
                if not isinstance(row, dict):
                    problems.append(f"{self._collection}/{key}: not a table")
                    continue
                try:
                    made = provider_from_data(row, where=f"{self._collection}/{key}")
                except MalformedProvider as wrong:
                    problems.append(str(wrong))
                    continue
                found[made.id] = made
            self._providers, self._problems, self._seen = found, tuple(problems), version
        return dict(self._providers)

    async def problems(self) -> tuple[str, ...]:
        await self.providers()
        return self._problems


def store_providers(store: Any, collection: str = "providers") -> StoreProviders:
    return StoreProviders(store, collection)


async def library_from(*sources: Any) -> dict[str, Provider]:
    """The shipped library, then each source in order, later shadowing earlier by id."""
    found = shipped()
    for source in sources:
        found.update(await source.providers())
    return found


__all__ = [
    "MalformedProvider",
    "StoreProviders",
    "library_from",
    "load_dir",
    "load_provider",
    "provider_from_data",
    "shipped",
    "store_providers",
]
