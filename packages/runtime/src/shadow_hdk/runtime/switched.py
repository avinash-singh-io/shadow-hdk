"""Which components are on: a `ComponentPort` that reads switches from a `Store` (D66).

A product turns a tool off in its database and it is gone from what the agent is offered at the
next refresh — the runtime already refreshes registries at every step boundary (Phase 5) — and
refused if invoked anyway, without a restart. Rows in the `components` collection: `{"id", "on"}`.
No row means on.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import JsonValue

from shadow_hdk.kernel import Observation, Refused, Registration
from shadow_hdk.kernel.ports import ComponentPort


class StoreSwitches:
    """The off-switches, reloaded only when the collection's version moved."""

    def __init__(self, store: Any, collection: str = "components") -> None:
        self._store = store
        self._collection = collection
        self._seen = -1
        self._off: frozenset[str] = frozenset()

    async def off(self) -> frozenset[str]:
        version = await self._store.version(self._collection)
        if version != self._seen:
            found: set[str] = set()
            for key, row in await self._store.list(self._collection):
                if isinstance(row, dict) and row.get("on") is False:
                    found.add(str(row.get("id", key)))
            self._off, self._seen = frozenset(found), version
        return self._off


def store_switches(store: Any, collection: str = "components") -> StoreSwitches:
    return StoreSwitches(store, collection)


class Switched(ComponentPort):
    """`inner`, minus what the switches say is off."""

    def __init__(self, inner: ComponentPort, switches: StoreSwitches) -> None:
        self._inner = inner
        self._switches = switches

    async def registrations(self) -> Sequence[Registration]:
        off = await self._switches.off()
        return [r for r in await self._inner.registrations() if r.id not in off]

    async def invoke(self, registration: str, inputs: JsonValue) -> Observation:
        if registration in await self._switches.off():
            return Refused(f"{registration!r} is switched off")
        return await self._inner.invoke(registration, inputs)


__all__ = ["StoreSwitches", "Switched", "store_switches"]
