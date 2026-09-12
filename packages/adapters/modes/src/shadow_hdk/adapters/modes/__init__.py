"""Governance as data: a mode is a ceiling and an ask line, and a rule is a row."""

from shadow_hdk.adapters.modes.acts import ActRules
from shadow_hdk.adapters.modes.check import FIELDS, Wider, widens
from shadow_hdk.adapters.modes.files import load_rules, rules_from, shipped_example
from shadow_hdk.adapters.modes.mode import Mode, ModeGovernance, layer
from shadow_hdk.adapters.modes.registry import (
    ModeRegistry,
    ModeSpec,
    governance_for,
    shipped_modes,
)
from shadow_hdk.adapters.modes.rules import Rule, RuleGovernance, RuleSet, Selected

__all__ = [
    "ActRules",
    "FIELDS",
    "Mode",
    "ModeGovernance",
    "ModeRegistry",
    "ModeSpec",
    "Rule",
    "RuleGovernance",
    "RuleSet",
    "Selected",
    "Wider",
    "governance_for",
    "layer",
    "load_rules",
    "rules_from",
    "shipped_example",
    "shipped_modes",
    "widens",
]
