"""The skill registry: three sources, one listing (Phase 24, D54).

A skill used to be a file the host loaded and handed to one agent. That is a directory, and a
directory has three things wrong with it for a harness that is generic and grows while it runs:
the model cannot *choose* a skill, nothing an agent works out mid-run can become one without a
person editing a file, and every body would have to be in the catalogue for the model to know it
exists. A registry is a union of **sources** — a directory of TOML (shipped, or a team's), the run's
own minted skills, and whatever a host hands in as its kept ones — listed by name and line.

**Later shadows earlier, on the record.** A team's version of a shipped skill wins and a minted one
wins over both, because later is closer to the run; what was shadowed is kept, so a skill changing
under the model's feet is never silent.

The registry is data. It grants nothing (D17 stands): choosing a skill is `use_skill`'s act, checked
against `visible()` there.
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib import resources
from pathlib import Path
from typing import Protocol

from shadow_hdk.adapters.agent.skills import Skill, load_skill


class SkillSource(Protocol):
    async def skills(self) -> Sequence[Skill]: ...


class DirectorySkills:
    """Every `*.toml` under a directory, read on each ask — a file added mid-run is found."""

    def __init__(self, where: Path, *, source: str = "file") -> None:
        self.where = Path(where)
        self.source = source

    async def skills(self) -> Sequence[Skill]:
        if not self.where.is_dir():
            return ()
        return tuple(
            load_skill(path, source=self.source) for path in sorted(self.where.glob("*.toml"))
        )


class MintedSkills:
    """What this run's agents wrote down. Empty at the start; usable the moment it is added."""

    def __init__(self) -> None:
        self._skills: list[Skill] = []

    def add(self, skill: Skill) -> Skill:
        minted = Skill(
            name=skill.name,
            prompt=skill.prompt,
            needs=skill.needs,
            description=skill.description,
            source="minted",
        )
        self._skills = [s for s in self._skills if s.name != minted.name] + [minted]
        return minted

    async def skills(self) -> Sequence[Skill]:
        return tuple(self._skills)


class SkillRegistry:
    """The union, later sources shadowing earlier ones by name."""

    def __init__(self, sources: Sequence[SkillSource] = ()) -> None:
        self.sources: tuple[SkillSource, ...] = tuple(sources)

    async def _resolved(self) -> tuple[dict[str, Skill], list[Skill]]:
        by_name: dict[str, Skill] = {}
        shadowed: list[Skill] = []
        for source in self.sources:
            for skill in await source.skills():
                if skill.name in by_name:
                    shadowed.append(by_name[skill.name])
                by_name[skill.name] = skill
        return by_name, shadowed

    async def all(self) -> tuple[Skill, ...]:
        by_name, _ = await self._resolved()
        return tuple(by_name.values())

    async def listing(self) -> tuple[tuple[str, str], ...]:
        """Names and lines — what the model sees until it chooses (D55)."""
        return tuple((s.name, s.description) for s in await self.all())

    async def find(self, name: str) -> Skill | None:
        by_name, _ = await self._resolved()
        return by_name.get(name)

    async def shadowed(self) -> tuple[Skill, ...]:
        _, shadowed = await self._resolved()
        return tuple(shadowed)


def shipped_skills() -> DirectorySkills:
    """The library this package ships: a few procedures that make sense for any agent. None is
    about code, because the harness is not."""
    where = resources.files("shadow_hdk.adapters.agent") / "skills_library"
    return DirectorySkills(Path(str(where)), source="shipped")


__all__ = ["DirectorySkills", "MintedSkills", "SkillRegistry", "SkillSource", "shipped_skills"]
