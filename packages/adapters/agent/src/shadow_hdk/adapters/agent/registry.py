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

**And the registry is offered as a component** (D55): `SkillComponents` registers `use_skill` — and
`mint_skill`, where the host allows minting — as tools like any other, so choosing and minting are
governed steps on the record, and reach an in-process agent, an agent on the far side of the
wire, and a CLI by subscription through the registry socket alike. One mechanism, every host. The
names and lines ride the tool's own description, rebuilt on every `registrations()` — which
`visible()` asks for on every catalogue — so a skill minted a turn ago is there the next.
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib import resources
from pathlib import Path
from typing import Protocol

from shadow_hdk.adapters.agent.skills import Skill, load_skill, missing_for, skill_from
from pydantic import JsonValue

from shadow_hdk.kernel.components import (
    Component,
    Interface,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.effects import EffectProfile, ScopeSet
from shadow_hdk.kernel.observations import Completed, Failed, Observation, Proposal
from shadow_hdk.kernel.ports import ComponentPort
from shadow_hdk.runtime import current_run


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
    """The union, later sources shadowing earlier ones by name.

    `minted` is the last source and always there: what this registry's agents write down mid-run
    (D56). It lives as long as the registry object does — a host that wants minting scoped to a
    run hands a fresh registry to that run, which is what the host example does.
    """

    def __init__(self, sources: Sequence[SkillSource] = ()) -> None:
        self.sources: tuple[SkillSource, ...] = tuple(sources)
        self.minted = MintedSkills()

    async def _resolved(self) -> tuple[dict[str, Skill], list[Skill]]:
        by_name: dict[str, Skill] = {}
        shadowed: list[Skill] = []
        for source in (*self.sources, self.minted):
            for skill in await source.skills():
                if skill.name in by_name:
                    shadowed.append(by_name[skill.name])
                by_name[skill.name] = skill
        return by_name, shadowed

    async def all(self) -> tuple[Skill, ...]:
        by_name, _ = await self._resolved()
        return tuple(by_name.values())

    async def skills(self) -> Sequence[Skill]:
        """A registry is itself a source, so a host composes one from another."""
        return await self.all()

    async def listing(self) -> tuple[tuple[str, str], ...]:
        """Names and lines — what the model sees until it chooses (D55)."""
        return tuple((s.name, s.description) for s in await self.all())

    async def find(self, name: str) -> Skill | None:
        by_name, _ = await self._resolved()
        return by_name.get(name)

    async def shadowed(self) -> tuple[Skill, ...]:
        _, shadowed = await self._resolved()
        return tuple(shadowed)


USE_SKILL = "use_skill"
MINT_SKILL = "mint_skill"


class SkillComponents(ComponentPort):
    """The registry as tools: `use_skill`, and `mint_skill` where minting is allowed.

    `use_skill` is pure — choosing a procedure changes nothing in the world — so any mode that
    lets the agent see anything lets it choose. `mint_skill` writes to the *record* (it proposes),
    reversibly, so a policy can refuse minting by effect the way it refuses any other write.
    """

    def __init__(
        self,
        registry: SkillRegistry,
        *,
        minting: bool = False,
        registered_by: str = "host",
        at: str = "",
    ) -> None:
        self.registry = registry
        self.minting = minting
        self._provenance = Provenance(registered_by=registered_by, adapter="agent", at=at)

    async def registrations(self) -> Sequence[Registration]:
        listing = await self.registry.listing()
        found: list[Registration] = []
        if listing:
            lines = "; ".join(f"{name} — {line}" if line else name for name, line in listing)
            found.append(
                Registration(
                    id=USE_SKILL,
                    component=Component(
                        interface=Interface(
                            name=USE_SKILL,
                            description=(
                                "Load a procedure to follow for the rest of this work. Each skill "
                                "is a name and one line; the procedure arrives when you choose "
                                f"it. Skills: {lines}."
                            ),
                            input_schema={
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "enum": [n for n, _ in listing]}
                                },
                                "required": ["name"],
                            },
                            output_schema={"type": "object"},
                        ),
                        effects=EffectProfile(),
                        provenance=self._provenance,
                        labels=frozenset({"skill"}),
                    ),
                )
            )
        if self.minting:
            found.append(
                Registration(
                    id=MINT_SKILL,
                    component=Component(
                        interface=Interface(
                            name=MINT_SKILL,
                            description=(
                                "Write down a procedure worth repeating: a name, one line saying "
                                "what it is for, the procedure itself, and the tools it needs. "
                                "Usable at once in this run and proposed to whoever keeps this "
                                "run's record; whether it is kept is their decision."
                            ),
                            input_schema={
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "prompt": {"type": "string"},
                                    "needs": {"type": "array", "items": {"type": "string"}},
                                },
                                "required": ["name", "description", "prompt"],
                            },
                            output_schema={"type": "object"},
                        ),
                        effects=EffectProfile(writes=ScopeSet.of("record"), reversible=True),
                        provenance=self._provenance,
                        labels=frozenset({"skill"}),
                    ),
                )
            )
        return found

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        arguments = inputs if isinstance(inputs, dict) else {}
        if registration == USE_SKILL:
            return await self._use(str(arguments.get("name", "")))
        if registration == MINT_SKILL and self.minting:
            return await self._mint(arguments)
        return Failed(f"no component registered as {registration!r}")

    async def _use(self, name: str) -> Observation:
        """The act of choosing, and where D17's check runs — against `visible()`, so a skill needing
        what this run does not offer is refused by name and its body never arrives."""
        skill = await self.registry.find(name)
        if skill is None:
            names = ", ".join(n for n, _ in await self.registry.listing()) or "none"
            return Failed(f"there is no skill named {name!r}; the skills are: {names}")
        context = current_run()
        visible = await context.visible() if context is not None else []
        missing = missing_for(skill, visible)
        if missing:
            return Failed(
                f"the skill {name!r} needs {sorted(missing)}, which this run does not offer; "
                "it was not loaded"
            )
        return Completed(
            {
                "skill": skill.name,
                "source": skill.source,
                "description": skill.description,
                "needs": sorted(skill.needs),
                "procedure": skill.prompt,
                "how": "follow this procedure from here on",
            }
        )

    async def _mint(self, arguments: dict[str, JsonValue]) -> Observation:
        """Two things happen and neither is a runtime power — the same shape as compaction (D18):
        the skill goes into the registry's `minted` source, usable at once, and to the **sink**
        as a proposal, where whoever keeps the record decides. This adapter writes nowhere."""
        needs = arguments.get("needs", [])
        data: dict[str, object] = {
            "name": arguments.get("name", ""),
            "description": arguments.get("description", ""),
            "prompt": arguments.get("prompt", ""),
            "needs": [str(n) for n in needs] if isinstance(needs, list) else [],
        }
        try:
            minted = self.registry.minted.add(skill_from(data, where=MINT_SKILL, source="minted"))
        except ValueError as malformed:
            return Failed(f"not minted: {malformed}")
        context = current_run()
        if context is not None:
            await context.propose(
                Proposal(
                    kind="skill",
                    payload={
                        "name": minted.name,
                        "description": minted.description,
                        "prompt": minted.prompt,
                        "needs": sorted(minted.needs),
                    },
                    provenance=Provenance(
                        registered_by=context.run_id, adapter="agent", at=context.now()
                    ),
                )
            )
        return Completed(
            {
                "minted": minted.name,
                "usable": f"now, with {USE_SKILL}",
                "kept": "proposed to whoever keeps this run's record; not yours to decide",
            }
        )


def kept_from(proposal: Proposal, *, source: str = "kept") -> Skill:
    """A host's half of keeping: the `kind="skill"` proposal it kept, as a skill it can hand back.

    The payload is exactly what `mint_skill` proposed, and it is checked the way a file is — a
    proposal is data from a run, not a trusted record, and a host that stored a malformed one
    finds out here rather than in a model's catalogue.
    """
    if proposal.kind != "skill" or not isinstance(proposal.payload, dict):
        raise ValueError(f"not a skill proposal: kind={proposal.kind!r}")
    return skill_from(dict(proposal.payload), where=f"proposal {proposal.kind!r}", source=source)


def shipped_skills() -> DirectorySkills:
    """The library this package ships: a few procedures that make sense for any agent. None is
    about code, because the harness is not."""
    where = resources.files("shadow_hdk.adapters.agent") / "skills_library"
    return DirectorySkills(Path(str(where)), source="shipped")


__all__ = [
    "MINT_SKILL",
    "USE_SKILL",
    "DirectorySkills",
    "MintedSkills",
    "SkillComponents",
    "SkillRegistry",
    "SkillSource",
    "kept_from",
    "shipped_skills",
]
