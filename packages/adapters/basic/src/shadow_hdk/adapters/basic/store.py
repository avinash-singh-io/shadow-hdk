"""A `Store` on sqlite — the live data a host gets with nothing to write (D66).

One table of rows and one of versions; every call runs off the loop. A product with its own
database implements the port and this file is not imported.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

from pydantic import JsonValue

from shadow_hdk.kernel.ports import Store

SCHEMA = """
create table if not exists rows (
    collection text not null,
    key text not null,
    row text not null,
    primary key (collection, key)
);
create table if not exists versions (
    collection text primary key,
    version integer not null default 0
);
"""


class SqliteStore(Store):
    def __init__(self, path: Path | str) -> None:
        self._path = str(path)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _bump(self, connection: sqlite3.Connection, collection: str) -> None:
        connection.execute(
            "insert into versions (collection, version) values (?, 1) "
            "on conflict(collection) do update set version = version + 1",
            (collection,),
        )

    async def put(self, collection: str, key: str, row: JsonValue) -> None:
        def write() -> None:
            with self._connect() as connection:
                connection.execute(
                    "insert into rows (collection, key, row) values (?, ?, ?) "
                    "on conflict(collection, key) do update set row = excluded.row",
                    (collection, key, json.dumps(row)),
                )
                self._bump(connection, collection)

        await asyncio.to_thread(write)

    async def get(self, collection: str, key: str) -> JsonValue | None:
        def read() -> JsonValue | None:
            with self._connect() as connection:
                found = connection.execute(
                    "select row from rows where collection = ? and key = ?", (collection, key)
                ).fetchone()
            loaded: JsonValue | None = json.loads(found[0]) if found else None
            return loaded

        return await asyncio.to_thread(read)

    async def delete(self, collection: str, key: str) -> None:
        def write() -> None:
            with self._connect() as connection:
                gone = connection.execute(
                    "delete from rows where collection = ? and key = ?", (collection, key)
                ).rowcount
                if gone:
                    self._bump(connection, collection)

        await asyncio.to_thread(write)

    async def list(self, collection: str) -> tuple[tuple[str, JsonValue], ...]:
        def read() -> tuple[tuple[str, JsonValue], ...]:
            with self._connect() as connection:
                rows = connection.execute(
                    "select key, row from rows where collection = ? order by key", (collection,)
                ).fetchall()
            return tuple((key, json.loads(row)) for key, row in rows)

        return await asyncio.to_thread(read)

    async def version(self, collection: str) -> int:
        def read() -> int:
            with self._connect() as connection:
                found = connection.execute(
                    "select version from versions where collection = ?", (collection,)
                ).fetchone()
            return int(found[0]) if found else 0

        return await asyncio.to_thread(read)


__all__ = ["SqliteStore"]
