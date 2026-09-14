"""Governance as data: a mode is a ceiling and an ask line, and a rule is a row."""

from shadow_hdk.adapters.modes.acts import ActRules, StoreRules, store_rules
from shadow_hdk.adapters.modes.check import FIELDS, Wider, widens
from shadow_hdk.adapters.modes.files import load_rules, rules_from, shipped_example
from shadow_hdk.adapters.modes.mode import Mode, ModeGovernance, layer
from shadow_hdk.adapters.modes.mode_files import FileModes, modes_in
from shadow_hdk.adapters.modes.registry import (
    ModeRegistry,
    ModeSpec,
    StoreModes,
    governance_for,
    mode_from_document,
    policy_named,
    shipped_modes,
    store_modes,
)
from shadow_hdk.adapters.modes.routed import Routed
from shadow_hdk.adapters.modes.rules import Rule, RuleGovernance, RuleSet, Selected

__all__ = [
    "Routed",
    "ActRules",
    "FileModes",
    "StoreModes",
    "StoreRules",
    "mode_from_document",
    "modes_in",
    "policy_named",
    "store_modes",
    "store_rules",
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
