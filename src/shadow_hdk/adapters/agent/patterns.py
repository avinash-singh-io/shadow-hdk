"""The patterns the framework ships, and the ones a product keeps in its own store (D17, D174).

This module stays so that `single` is importable as it always was, but it is no longer where the
pattern *lives*: the file is. A team adds its own by writing one and calling `load_pattern`, which
is the same call this uses (`09` §5).

**And since phase 64, a product's agents are store rows** — `StorePatterns` over an `agents`
collection, the last of the plugin concepts to work that way. Skills, modes, rules, batteries,
providers and component switches all read from the product's database already; an agent read only
from a packaged file, so a plugin's Build agent, Reviewer, Test fixer and Release writer had
nowhere to live. `pattern_from` already took a dict, so this is the missing source and nothing
more.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from shadow_hdk.adapters.agent.loader import pattern_from, shipped
from shadow_hdk.adapters.agent.pattern import Pattern

single = shipped()["single"]
"""One reasoning loop over its tools. No `compose`, so the model cannot change its own shape —
which is what makes a deterministic one-agent product possible on this runtime."""

SINGLE_ROLE = single.system


class StorePatterns:
    """Every row of a `Store`'s `agents` collection as a `Pattern` (D174), reloaded only when the
    collection's version moves — the same gate `StoreSkills` keeps, and for the same reason: an
    agent listing re-read on every turn would make a store round trip out of something that
    changes when a person edits a plugin.

    The row is the document a pattern file carries: `name`, `system`, and optionally `meta_tools`,
    `tool_names`, `ceiling`, `max_turns`, `nudge`, `catalogue_threshold`.

    **A malformed row is skipped, never fatal**, and what was skipped is kept on `skipped` so a
    product can show it. Losing three good agents to one bad one is the failure; losing one
    silently, so somebody debugs an agent that simply never appears, is the other.
    """

    def __init__(self, store: Any, collection: str = "agents") -> None:
        self._store = store
        self._collection = collection
        self._seen = -1
        self._patterns: tuple[Pattern, ...] = ()
        self.skipped: list[str] = []
        """What could not be read, and why — so a product can show it rather than wonder."""

    async def patterns(self) -> Sequence[Pattern]:
        version = await self._store.version(self._collection)
        if version != self._seen:
            found: list[Pattern] = []
            skipped: list[str] = []
            # Sorted by key, so a listing a person reads does not reshuffle between calls.
            for key, row in sorted(await self._store.list(self._collection), key=lambda r: r[0]):
                where = f"{self._collection}/{key}"
                if not isinstance(row, dict):
                    skipped.append(f"{where}: not an object")
                    continue
                try:
                    found.append(pattern_from(row, where=where))
                except (KeyError, ValueError, TypeError) as wrong:
                    skipped.append(str(wrong))
            self._patterns, self._seen, self.skipped = tuple(found), version, skipped
        return self._patterns


def store_patterns(store: Any, collection: str = "agents") -> StorePatterns:
    return StorePatterns(store, collection)


__all__ = ["SINGLE_ROLE", "StorePatterns", "single", "store_patterns"]
