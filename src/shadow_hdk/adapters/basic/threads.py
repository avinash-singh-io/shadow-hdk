"""Threads on sqlite — the `ThreadStore` a host gets with nothing to write (D62).

One table, one JSON column: the record is a kernel contract and `dump`/`load` are its
serialisation, so the store neither knows nor repeats the record's shape. A product with its own
tables implements the same port and this file is not imported.
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from shadow_hdk.kernel import ThreadRecord
from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.kernel.ports import ThreadStore

SCHEMA = """
create table if not exists threads (
    id text primary key,
    created_at text not null,
    archived integer not null default 0,
    record text not null
)
"""


class SqliteThreads(ThreadStore):
    """A `ThreadStore` over one sqlite file. Every call runs on a thread, off the loop."""

    def __init__(self, path: Path | str) -> None:
        self._path = str(path)
        with self._connect() as connection:
            connection.execute(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    async def create(self, thread: ThreadRecord) -> None:
        await self.save(thread)

    async def get(self, thread_id: str) -> ThreadRecord | None:
        def read() -> ThreadRecord | None:
            with self._connect() as connection:
                row = connection.execute(
                    "select record from threads where id = ?", (thread_id,)
                ).fetchone()
            return load(row[0], ThreadRecord) if row else None

        return await asyncio.to_thread(read)

    async def save(self, thread: ThreadRecord) -> None:
        def write() -> None:
            with self._connect() as connection:
                connection.execute(
                    "insert into threads (id, created_at, archived, record) values (?, ?, ?, ?) "
                    "on conflict(id) do update set archived = excluded.archived, "
                    "record = excluded.record",
                    (
                        thread.id,
                        thread.created_at,
                        int(thread.archived),
                        dump(thread, ThreadRecord),
                    ),
                )

        await asyncio.to_thread(write)

    async def list(self, *, include_archived: bool = False) -> tuple[ThreadRecord, ...]:
        def read() -> tuple[ThreadRecord, ...]:
            with self._connect() as connection:
                rows = connection.execute(
                    "select record from threads"
                    + ("" if include_archived else " where archived = 0")
                    + " order by created_at, id"
                ).fetchall()
            return tuple(load(row[0], ThreadRecord) for row in rows)

        return await asyncio.to_thread(read)

    async def archive(self, thread_id: str) -> None:
        found = await self.get(thread_id)
        if found is not None:
            from dataclasses import replace

            await self.save(replace(found, archived=True))


__all__ = ["SqliteThreads"]
