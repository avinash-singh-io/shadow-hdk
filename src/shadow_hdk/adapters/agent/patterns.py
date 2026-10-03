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
from shadow_hdk.kernel.threads import agent_now, agent_to_resume

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


def agent_recorded(wanted: str, *, chosen: bool) -> str:
    """Which agent a run resolved to, for the record a product caches by hash (D177).

    `wanted` is the name the thread or its mode asked for; `chosen` says whether the kit actually
    selected a loop. Empty when it did not — a CLI provider owns its own loop, and naming one
    there would be a claim the kit cannot make. An unnamed run records `single`, not empty,
    because empty reads as *we do not know* and `single` is what actually ran.

    A function rather than an expression inside `ServeHost.open` so it can be checked without
    standing up a host — which in this suite means without opening a real sandbox (TD-019).
    """
    return (wanted or single.name) if chosen else ""


def store_patterns(store: Any, collection: str = "agents") -> StorePatterns:
    return StorePatterns(store, collection)


class NoSuchAgent(Exception):
    """A run named an agent nobody registered, and says which — never a silent `single` (D176).

    Falling back to a default would hand a product a run that looks right and is not. The same cut
    `Dialect` makes for an unknown transport and `ModeRegistry` for an unknown mode id.
    """


class PatternRegistry:
    """The agents a run may be given: the shipped library, and the product's own.

    **Later shadows earlier**, as the skill registry does (D54) — a product's `single` wins over
    the shipped one, because later is closer to the run. Nothing here grants anything: choosing a
    loop is the mode's or the thread's, and `find` only answers what exists.
    """

    def __init__(self, sources: Sequence[Any] = (), *, include_shipped: bool = True) -> None:
        self._sources = tuple(sources)
        self._shipped = include_shipped

    async def all(self) -> tuple[Pattern, ...]:
        by_name: dict[str, Pattern] = {}
        if self._shipped:
            by_name.update(shipped())
        for source in self._sources:
            for pattern in await source.patterns():
                by_name[pattern.name] = pattern
        return tuple(by_name[name] for name in sorted(by_name))

    async def find(self, name: str) -> Pattern | None:
        for pattern in await self.all():
            if pattern.name == name:
                return pattern
        return None

    async def named(self, name: str) -> Pattern:
        """The agent by that name, or `NoSuchAgent` saying what there is (D176)."""
        found = await self.find(name)
        if found is not None:
            return found
        have = ", ".join(p.name for p in await self.all()) or "none"
        raise NoSuchAgent(f"no agent called {name!r} is registered here; there is: {have}")

    async def listing(self) -> tuple[tuple[str, str], ...]:
        """Name and one line, for a product showing a person what it may run."""
        return tuple(
            (p.name, p.system.strip().splitlines()[0] if p.system.strip() else "")
            for p in await self.all()
        )


__all__ = [
    # `agent_now` and `agent_to_resume` live in the kernel — the runtime decides a mode switch and a
    # resume with them, and the runtime may import no adapter — and are re-exported here so every
    # decision about which agent runs is found in one place.
    "SINGLE_ROLE",
    "agent_now",
    "agent_recorded",
    "agent_to_resume",
    "NoSuchAgent",
    "PatternRegistry",
    "StorePatterns",
    "single",
    "store_patterns",
]
