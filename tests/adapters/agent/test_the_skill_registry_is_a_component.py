"""`SkillComponents` is held to the component contract like every other port implementation."""

from __future__ import annotations

from pydantic import JsonValue

from shadow_hdk.adapters.agent import MintedSkills, Skill, SkillComponents, SkillRegistry
from shadow_hdk.kernel.components import RegistrationId
from shadow_hdk.kernel.ports import ComponentPort
from shadow_hdk.testing.contracts import ComponentPortContract


class TestSkillComponentsIsAComponentPort(ComponentPortContract):
    def port(self) -> ComponentPort:
        handed = MintedSkills()
        handed.add(Skill(name="triage", description="Sort by urgency.", prompt="Sort them."))
        return SkillComponents(
            SkillRegistry((handed,)), minting=True, at="2026-01-01T00:00:00+00:00"
        )

    def valid_call(self) -> tuple[RegistrationId, JsonValue]:
        # Outside a run there is no `visible()` to check against; a skill needing nothing loads.
        return "use_skill", {"name": "triage"}
