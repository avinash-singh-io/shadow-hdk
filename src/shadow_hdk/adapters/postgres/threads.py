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
);
create table if not exists shadow_hdk_holds (
    thread_id text primary key,
    holder text not null,
    until timestamptz not null
);
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

    # ------------------------------------------------------------------ one holder (D81)

    async def hold(self, thread_id: str, holder: str, *, ttl_seconds: float) -> bool:
        pool = await self._pooled.pool()
        async with pool.connection() as connection:
            taken = await connection.execute(
                "insert into shadow_hdk_holds (thread_id, holder, until) "
                "values (%s, %s, now() + make_interval(secs => %s)) "
                "on conflict (thread_id) do update set holder = excluded.holder, "
                "until = excluded.until "
                "where shadow_hdk_holds.holder = excluded.holder "
                "or shadow_hdk_holds.until <= now()",
                (thread_id, holder, ttl_seconds),
            )
            return bool(taken.rowcount > 0)

    async def renew(self, thread_id: str, holder: str, *, ttl_seconds: float) -> bool:
        pool = await self._pooled.pool()
        async with pool.connection() as connection:
            renewed = await connection.execute(
                "update shadow_hdk_holds set until = now() + make_interval(secs => %s) "
                "where thread_id = %s and holder = %s and until > now()",
                (ttl_seconds, thread_id, holder),
            )
            return bool(renewed.rowcount > 0)

    async def release(self, thread_id: str, holder: str) -> None:
        pool = await self._pooled.pool()
        async with pool.connection() as connection:
            await connection.execute(
                "delete from shadow_hdk_holds where thread_id = %s and holder = %s",
                (thread_id, holder),
            )

    async def held_by(self, thread_id: str) -> str | None:
        pool = await self._pooled.pool()
        async with pool.connection() as connection:
            found = await (
                await connection.execute(
                    "select holder from shadow_hdk_holds where thread_id = %s and until > now()",
                    (thread_id,),
                )
            ).fetchone()
        return str(found[0]) if found else None


__all__ = ["PostgresThreads"]
