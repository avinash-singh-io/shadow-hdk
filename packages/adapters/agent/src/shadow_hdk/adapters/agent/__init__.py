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
    PROPOSE,
    RELEASE,
    SEND,
    SPAWN,
    Pattern,
)
from shadow_hdk.adapters.agent.patterns import SINGLE_ROLE, single
from shadow_hdk.adapters.agent.skills import Skill, load_skill, missing_for, skill_from

__all__ = [
    "COMPACT",
    "MAILBOX",
    "RELEASE",
    "SEND",
    "SPAWN",
    "COMPOSE",
    "DESCRIBE",
    "DONE",
    "META_TOOLS",
    "PROPOSE",
    "SINGLE_ROLE",
    "AgentComponent",
    "Pattern",
    "Skill",
    "describe_for",
    "load_pattern",
    "load_skill",
    "missing_for",
    "pattern_from",
    "skill_from",
    "thin",
    "shipped",
    "single",
]
