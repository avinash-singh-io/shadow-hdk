"""The agent loop as a component, and agent architectures as data."""

from shadow_hdk.adapters.agent.component import AgentComponent
from shadow_hdk.adapters.agent.loader import load_pattern, pattern_from, shipped
from shadow_hdk.adapters.agent.pattern import COMPOSE, DONE, META_TOOLS, PROPOSE, Pattern
from shadow_hdk.adapters.agent.patterns import SINGLE_ROLE, single

__all__ = [
    "COMPOSE",
    "DONE",
    "META_TOOLS",
    "PROPOSE",
    "SINGLE_ROLE",
    "AgentComponent",
    "Pattern",
    "load_pattern",
    "pattern_from",
    "shipped",
    "single",
]
