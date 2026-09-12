"""The host's act rules, consulted by governance after it says *ask* (D65).

A registry rather than a list: the rules handed in, then each source in order — a `Store`'s
`rules` collection (D66) — and a rule the person makes is written through to the first store, so
it outlives the process and every other reader sees it at its next read.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from typing import Any, Protocol

from shadow_hdk.kernel import ActRule
from shadow_hdk.kernel.contracts import dump, load


class RuleSource(Protocol):
    async def rules(self) -> tuple[ActRule, ...]: ...


class StoreRules:
    """Rules from a `Store`'s collection, reloaded only when its version moved."""

    def __init__(self, store: Any, collection: str = "rules") -> None:
        self._store = store
        self._collection = collection
        self._seen = -1
        self._rules: tuple[ActRule, ...] = ()

    async def rules(self) -> tuple[ActRule, ...]:
        version = await self._store.version(self._collection)
        if version != self._seen:
            found: list[ActRule] = []
            for _key, row in await self._store.list(self._collection):
                try:
                    found.append(load(json.dumps(row), ActRule))
                except Exception:  # noqa: BLE001 — a malformed row is skipped, not fatal
                    continue
            self._rules, self._seen = tuple(found), version
        return self._rules

    async def keep(self, rule: ActRule) -> None:
        key = f"{rule.component}:{abs(hash(dump(rule, ActRule)))}"
        await self._store.put(self._collection, key, json.loads(dump(rule, ActRule)))


def store_rules(store: Any, collection: str = "rules") -> StoreRules:
    return StoreRules(store, collection)


class ActRules:
    """Rules in the order they were added; the first that matches decides."""

    def __init__(
        self, rules: Iterable[ActRule] = (), *, sources: Sequence[RuleSource] = ()
    ) -> None:
        self._rules: list[ActRule] = list(rules)
        self.sources: tuple[RuleSource, ...] = tuple(sources)

    def add(self, rule: ActRule) -> None:
        if rule not in self._rules:
            self._rules.append(rule)

    async def add_now(self, rule: ActRule) -> None:
        """Keep it here, and write it through to the first store source so it outlives us."""
        self.add(rule)
        for source in self.sources:
            keep = getattr(source, "keep", None)
            if keep is not None:
                await keep(rule)
                break

    async def all_now(self) -> tuple[ActRule, ...]:
        merged = list(self._rules)
        for source in self.sources:
            for rule in await source.rules():
                if rule not in merged:
                    merged.append(rule)
        return tuple(merged)

    async def decide_now(self, component: str, inputs: Any, *, mode: str = "") -> str | None:
        """`allow`, `deny`, or `None` — over the handed rules and every source, read now."""
        for rule in await self.all_now():
            if rule.matches(component, inputs, mode=mode):
                return rule.decision
        return None

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


__all__ = ["ActRules", "RuleSource", "StoreRules", "store_rules"]
