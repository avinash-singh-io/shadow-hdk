"""A skill: a team's procedure, as a file that says what it needs (D17).

`10` §306 — *a team-authored procedure, a file in a registry, declaring which components it needs
**so skill and mode can be checked against each other***.

That last clause is the design. The check runs **before the first turn**, against
`RunContext.visible()` — the same computation the model's catalogue comes from, so a skill can never
be told it may use something the model would not be offered. A skill needing a component the
deployment's mode hides is refused with the names of what is missing.

It is the same move as `visible()` itself: what the policy would refuse is **absent**, not greyed
out (`09` §4). A skill is simply the first thing that can say what it wants in advance.

A skill is *not* a permission. `needs` is a declaration of dependency, and naming a component grants
nothing — permission is still effects, judged per step (`09` §2). The check can only ever say no.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shadow_hdk.kernel.components import Registration

KEYS = frozenset({"name", "prompt", "needs"})
REQUIRED = ("name", "prompt")


@dataclass(frozen=True)
class Skill:
    """A procedure somebody wrote down, and the components it cannot do without."""

    name: str
    prompt: str
    needs: frozenset[str] = frozenset()


def skill_from(data: dict[str, Any], *, where: str) -> Skill:
    unknown = set(data) - KEYS
    if unknown:
        raise ValueError(
            f"{where}: unknown key(s) {sorted(unknown)}; known keys are {sorted(KEYS)}"
        )
    for key in REQUIRED:
        if not data.get(key):
            raise ValueError(f"{where}: needs a {key!r}")
    return Skill(
        name=str(data["name"]),
        prompt=str(data["prompt"]).strip(),
        needs=frozenset(data.get("needs", ())),
    )


def load_skill(path: str | Path) -> Skill:
    where = str(path)
    try:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as broken:
        raise ValueError(f"{where}: not readable as TOML — {broken}") from broken
    return skill_from(data, where=where)


def missing_for(skill: Skill, visible: Iterable[Registration]) -> frozenset[str]:
    """What this deployment does not offer. Empty means the skill may start.

    `visible` is what `RunContext.visible()` returned — the registry as the policy leaves it. A
    component absent because a mode hides it and one absent because nobody registered it are the
    same answer here, and deliberately so: the skill cannot run either way, and which of the two it
    is belongs to whoever reads the record, not to the check.

    **Names are registration ids**, which is what `Invoke.component` takes. Matching an interface
    name as well would let a skill declare a need it could not then invoke — an adapter is free to
    register `search` under the id `brave:search`, and only one of those two is addressable.
    """
    offered = {registration.id for registration in visible}
    return frozenset(skill.needs - offered)


__all__ = ["KEYS", "Skill", "load_skill", "missing_for", "skill_from"]
