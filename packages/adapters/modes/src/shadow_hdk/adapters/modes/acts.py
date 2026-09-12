"""The host's act rules, consulted by governance after it says *ask* (D65).

A registry rather than a list: a rule added now is read at the next judgement, and group 6 gives
it a store source so a product's database is one more place rules come from.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from shadow_hdk.kernel import ActRule


class ActRules:
    """Rules in the order they were added; the first that matches decides."""

    def __init__(self, rules: Iterable[ActRule] = ()) -> None:
        self._rules: list[ActRule] = list(rules)

    def add(self, rule: ActRule) -> None:
        if rule not in self._rules:
            self._rules.append(rule)

    def remove(self, rule: ActRule) -> None:
        self._rules = [r for r in self._rules if r != rule]

    def all(self) -> tuple[ActRule, ...]:
        return tuple(self._rules)

    def decide(self, component: str, inputs: Any, *, mode: str = "") -> str | None:
        """`allow`, `deny`, or `None` when no rule speaks."""
        for rule in self._rules:
            if rule.matches(component, inputs, mode=mode):
                return rule.decision
        return None


__all__ = ["ActRules"]
