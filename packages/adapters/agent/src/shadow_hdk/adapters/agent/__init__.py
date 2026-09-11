"""The agent loop as a component, and agent architectures as data."""

from shadow_hdk.adapters.agent.catalogue import describe_for, thin
from shadow_hdk.adapters.agent.component import AgentComponent
from shadow_hdk.adapters.agent.loader import load_pattern, pattern_from, shipped
from shadow_hdk.adapters.agent.pattern import (
    COMPACT,
    COMPOSE,
    DESCRIBE,
    DONE,
    MAILBOX,
    META_TOOLS,
    MINT_SKILL,
    PROPOSE,
    RECALL,
    RELEASE,
    SEND,
    SPAWN,
    USE_SKILL,
    Pattern,
)
from shadow_hdk.adapters.agent.patterns import SINGLE_ROLE, single
from shadow_hdk.adapters.agent.registry import (
    DirectorySkills,
    MintedSkills,
    SkillRegistry,
    SkillSource,
    kept_from,
    shipped_skills,
)
from shadow_hdk.adapters.agent.skills import Skill, load_skill, missing_for, skill_from

__all__ = [
    "COMPACT",
    "MAILBOX",
    "MINT_SKILL",
    "RELEASE",
    "SEND",
    "SPAWN",
    "COMPOSE",
    "DESCRIBE",
    "RECALL",
    "USE_SKILL",
    "DONE",
    "META_TOOLS",
    "PROPOSE",
    "SINGLE_ROLE",
    "AgentComponent",
    "Pattern",
    "DirectorySkills",
    "MintedSkills",
    "Skill",
    "SkillRegistry",
    "SkillSource",
    "describe_for",
    "load_pattern",
    "load_skill",
    "missing_for",
    "pattern_from",
    "kept_from",
    "skill_from",
    "thin",
    "shipped",
    "shipped_skills",
    "single",
]
