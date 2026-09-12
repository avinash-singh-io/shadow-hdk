"""An in-memory `Store` (D66): tests, and a host that keeps live data only for the process."""

from __future__ import annotations

import copy
from collections import defaultdict

from pydantic import JsonValue

from shadow_hdk.kernel.ports import Store


class InMemoryStore(Store):
    def __init__(self) -> None:
        self._rows: dict[str, dict[str, JsonValue]] = defaultdict(dict)
        self._versions: dict[str, int] = defaultdict(int)

    async def put(self, collection: str, key: str, row: JsonValue) -> None:
        self._rows[collection][key] = copy.deepcopy(row)
        self._versions[collection] += 1

    async def get(self, collection: str, key: str) -> JsonValue | None:
        found = self._rows[collection].get(key)
        return copy.deepcopy(found) if found is not None else None

    async def delete(self, collection: str, key: str) -> None:
        if key in self._rows[collection]:
            del self._rows[collection][key]
            self._versions[collection] += 1

    async def list(self, collection: str) -> tuple[tuple[str, JsonValue], ...]:
        return tuple((k, copy.deepcopy(v)) for k, v in self._rows[collection].items())

    async def version(self, collection: str) -> int:
        return self._versions[collection]


__all__ = ["InMemoryStore"]
