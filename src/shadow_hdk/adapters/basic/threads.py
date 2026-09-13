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
);
create table if not exists holds (
    thread_id text primary key,
    holder text not null,
    until real not null
);
"""

NOW = "(julianday('now') - 2440587.5) * 86400.0"
"""Unix seconds on the database's own clock (D81) — what every process agrees on."""


class SqliteThreads(ThreadStore):
    """A `ThreadStore` over one sqlite file. Every call runs on a thread, off the loop."""

    def __init__(self, path: Path | str) -> None:
        self._path = str(path)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

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

    # ------------------------------------------------------------------ one holder (D81)

    async def hold(self, thread_id: str, holder: str, *, ttl_seconds: float) -> bool:
        def write() -> bool:
            with self._connect() as connection:
                # Free, lapsed, or already this holder's: take it. Otherwise the insert conflicts
                # with a live hold and does nothing — the row count says which.
                taken = connection.execute(
                    f"insert into holds (thread_id, holder, until) values (?, ?, {NOW} + ?) "
                    "on conflict(thread_id) do update set holder = excluded.holder, "
                    "until = excluded.until "
                    f"where holds.holder = excluded.holder or holds.until <= {NOW}",
                    (thread_id, holder, ttl_seconds),
                ).rowcount
                return taken > 0

        return await asyncio.to_thread(write)

    async def renew(self, thread_id: str, holder: str, *, ttl_seconds: float) -> bool:
        def write() -> bool:
            with self._connect() as connection:
                renewed = connection.execute(
                    f"update holds set until = {NOW} + ? "
                    f"where thread_id = ? and holder = ? and until > {NOW}",
                    (ttl_seconds, thread_id, holder),
                ).rowcount
                return renewed > 0

        return await asyncio.to_thread(write)

    async def release(self, thread_id: str, holder: str) -> None:
        def write() -> None:
            with self._connect() as connection:
                connection.execute(
                    "delete from holds where thread_id = ? and holder = ?", (thread_id, holder)
                )

        await asyncio.to_thread(write)

    async def held_by(self, thread_id: str) -> str | None:
        def read() -> str | None:
            with self._connect() as connection:
                found = connection.execute(
                    f"select holder from holds where thread_id = ? and until > {NOW}", (thread_id,)
                ).fetchone()
            return str(found[0]) if found else None

        return await asyncio.to_thread(read)


__all__ = ["SqliteThreads"]
