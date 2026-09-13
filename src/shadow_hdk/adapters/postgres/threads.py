"""Threads on Postgres (D79): one table, the record as `jsonb` — the record is a kernel
contract and `dump`/`load` are its serialisation, so the table neither knows nor repeats its
shape, exactly as the sqlite one does not."""

from __future__ import annotations

from dataclasses import replace

from shadow_hdk.adapters.postgres.connection import Pooled
from shadow_hdk.kernel import ThreadRecord
from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.kernel.ports import ThreadStore

SCHEMA = """
create table if not exists shadow_hdk_threads (
    id text primary key,
    created_at text not null,
    archived boolean not null default false,
    record jsonb not null
)
"""


class PostgresThreads(ThreadStore):
    def __init__(self, url: str) -> None:
        self._pooled = Pooled(url, schema=SCHEMA)

    async def aclose(self) -> None:
        await self._pooled.aclose()

    async def create(self, thread: ThreadRecord) -> None:
        await self.save(thread)

    async def get(self, thread_id: str) -> ThreadRecord | None:
        pool = await self._pooled.pool()
        async with pool.connection() as connection:
            row = await (
                await connection.execute(
                    "select record::text from shadow_hdk_threads where id = %s", (thread_id,)
                )
            ).fetchone()
        return load(row[0], ThreadRecord) if row else None

    async def save(self, thread: ThreadRecord) -> None:
        pool = await self._pooled.pool()
        async with pool.connection() as connection:
            await connection.execute(
                "insert into shadow_hdk_threads (id, created_at, archived, record) "
                "values (%s, %s, %s, %s::jsonb) "
                "on conflict (id) do update set archived = excluded.archived, "
                "record = excluded.record",
                (thread.id, thread.created_at, thread.archived, dump(thread, ThreadRecord)),
            )

    async def list(self, *, include_archived: bool = False) -> tuple[ThreadRecord, ...]:
        pool = await self._pooled.pool()
        async with pool.connection() as connection:
            rows = await (
                await connection.execute(
                    "select record::text from shadow_hdk_threads"
                    + ("" if include_archived else " where not archived")
                    + " order by created_at, id"
                )
            ).fetchall()
        return tuple(load(row[0], ThreadRecord) for row in rows)

    async def archive(self, thread_id: str) -> None:
        found = await self.get(thread_id)
        if found is not None:
            await self.save(replace(found, archived=True))


__all__ = ["PostgresThreads"]
