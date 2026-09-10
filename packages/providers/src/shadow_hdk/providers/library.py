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

from shadow_hdk.kernel import EnvVar, Provider, ProviderKind

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


class MalformedProvider(ValueError):
    """A provider file that cannot be believed. Naming the file and the field is the whole job."""


def load_provider(path: Path) -> Provider:
    """One file, one provider."""
    try:
        raw: dict[str, Any] = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as broken:
        raise MalformedProvider(f"{path.name}: {broken}") from broken

    if unknown := sorted(set(raw) - KNOWN):
        raise MalformedProvider(
            f"{path.name}: unknown field(s) {', '.join(unknown)} — a typo here produces a provider "
            f"that loads and does not work"
        )
    for required in ("id", "kind", "bin"):
        if not raw.get(required):
            raise MalformedProvider(f"{path.name}: {required} is required")
    if raw["kind"] not in KINDS:
        raise MalformedProvider(
            f"{path.name}: kind {raw['kind']!r} is neither seam — it is 'model' or 'agent' (D39)"
        )

    made = dict(raw)
    for name in TUPLE_FIELDS:
        if name in made:
            made[name] = tuple(made[name])
    if "set_env" in made:
        try:
            made["set_env"] = tuple(
                EnvVar(name=e["name"], value=e["value"]) for e in made["set_env"]
            )
        except (KeyError, TypeError) as wrong:
            raise MalformedProvider(
                f"{path.name}: set_env wants name and value ({wrong})"
            ) from wrong
    try:
        return Provider(**made)
    except TypeError as wrong:
        raise MalformedProvider(f"{path.name}: {wrong}") from wrong


def shipped() -> dict[str, Provider]:
    """Every provider that ships with this package, by id."""
    return {p.id: p for p in (load_provider(f) for f in sorted(HERE.glob("*.toml")))}


def load_dir(where: Path) -> dict[str, Provider]:
    """A team's own library — the same shape, somewhere else."""
    return {p.id: p for p in (load_provider(f) for f in sorted(Path(where).glob("*.toml")))}


__all__ = ["MalformedProvider", "load_dir", "load_provider", "shipped"]
