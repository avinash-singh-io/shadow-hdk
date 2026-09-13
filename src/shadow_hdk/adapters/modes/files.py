"""Rules a team writes, checked when they are read.

D17 made patterns and skills files a team edits — TOML, because a role is prose and `tomllib` costs
no dependency. Rules follow the same move with one addition that is the whole of D24: a file can be
handed the constitution it has to narrow, and if it widens anywhere it is **refused at load**, with
the rule and the field, rather than discovered three steps into a run.

    [[rule]]
    name = "reading"
    applies_to = ["reading"]

    [rule.ceiling]
    reads = { everything = true }
    costs = true

Every refusal names the word that is wrong and the file it is in, because the reader is the person
who wrote it.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import fields as dataclass_fields
from importlib import resources
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.modes.check import widens
from shadow_hdk.adapters.modes.rules import Rule, RuleSet
from shadow_hdk.kernel.contracts import load
from shadow_hdk.kernel.effects import EffectProfile

RULE_KEYS = frozenset({"name", "ceiling", "ask_above", "applies_to"})
EFFECT_KEYS = frozenset(f.name for f in dataclass_fields(EffectProfile))
LIBRARY = "library"


def rules_from(data: dict[str, Any], *, where: str) -> RuleSet:
    """Build a `RuleSet` from parsed TOML, refusing anything a person should fix."""
    rows = data.get("rule")
    if not isinstance(rows, list):
        raise ValueError(f"{where}: expected a list of [[rule]] tables under 'rule'")
    seen: set[str] = set()
    rules: list[Rule] = []
    for index, row in enumerate(rows):
        label = f"{where}: rule #{index + 1}"
        if not isinstance(row, dict):
            raise ValueError(f"{label} is not a table")
        unknown = set(row) - RULE_KEYS
        if unknown:
            raise ValueError(
                f"{label}: unknown key(s) {sorted(unknown)}; known keys are {sorted(RULE_KEYS)}"
            )
        name = row.get("name")
        if not name:
            raise ValueError(f"{label} needs a 'name'")
        label = f"{where}: rule {name!r}"
        if name in seen:
            raise ValueError(f"{label} appears twice; a refusal has to name one rule")
        seen.add(name)
        if "ceiling" not in row:
            raise ValueError(f"{label} needs a 'ceiling'")
        rules.append(
            Rule(
                name=str(name),
                ceiling=_profile(row["ceiling"], where=f"{label} ceiling"),
                ask_above=(
                    _profile(row["ask_above"], where=f"{label} ask_above")
                    if "ask_above" in row
                    else None
                ),
                applies_to=frozenset(str(item) for item in row.get("applies_to", ())),
            )
        )
    return RuleSet(rules)


def _profile(raw: Any, *, where: str) -> EffectProfile:
    if not isinstance(raw, dict):
        raise ValueError(f"{where} must be a table of effect fields")
    unknown = set(raw) - EFFECT_KEYS
    if unknown:
        # Ahead of the kernel's own validation, which would say the same thing without the file.
        raise ValueError(
            f"{where}: unknown effect field(s) {sorted(unknown)}; "
            f"the vocabulary is {sorted(EFFECT_KEYS)}"
        )
    return load(json.dumps(raw), EffectProfile)


def load_rules(path: str | Path, *, narrowing: RuleSet | None = None) -> RuleSet:
    """Read one rule file. With `narrowing`, refuse it if it widens what it was given (D24)."""
    where = str(path)
    try:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as broken:
        raise ValueError(f"{where}: not readable as TOML — {broken}") from broken
    rules = rules_from(data, where=where)
    if narrowing is not None:
        found = widens(rules, narrowing)
        if found:
            lines = "\n  ".join(str(item) for item in found)
            raise ValueError(f"{where} widens what it was given:\n  {lines}")
    return rules


def shipped_example() -> RuleSet:
    """The example a team copies, read from the package so a wheel and a checkout agree."""
    root = resources.files("shadow_hdk.adapters.modes").joinpath(LIBRARY)
    text = root.joinpath("example.toml").read_text(encoding="utf-8")
    return rules_from(tomllib.loads(text), where=f"{LIBRARY}/example.toml")


__all__ = ["EFFECT_KEYS", "RULE_KEYS", "load_rules", "rules_from", "shipped_example"]
