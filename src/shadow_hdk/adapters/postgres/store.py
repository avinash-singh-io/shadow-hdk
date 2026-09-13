"""A `Store` on Postgres (D79): one table of rows as `jsonb`, one of versions per collection."""

from __future__ import annotations

import json

from pydantic import JsonValue

from shadow_hdk.adapters.postgres.connection import Pooled
from shadow_hdk.kernel.ports import Store

SCHEMA = """
create table if not exists shadow_hdk_rows (
    collection text not null,
    key text not null,
    row jsonb not null,
    primary key (collection, key)
);
create table if not exists shadow_hdk_versions (
    collection text primary key,
    version bigint not null default 0
);
"""

BUMP = (
    "insert into shadow_hdk_versions (collection, version) values (%s, 1) "
    "on conflict (collection) do update set version = shadow_hdk_versions.version + 1"
)


class PostgresStore(Store):
    def __init__(self, url: str) -> None:
        self._pooled = Pooled(url, schema=SCHEMA)

    async def aclose(self) -> None:
        await self._pooled.aclose()

    async def put(self, collection: str, key: str, row: JsonValue) -> None:
        pool = await self._pooled.pool()
        async with pool.connection() as connection:
            await connection.execute(
                "insert into shadow_hdk_rows (collection, key, row) values (%s, %s, %s::jsonb) "
                "on conflict (collection, key) do update set row = excluded.row",
                (collection, key, json.dumps(row)),
            )
            await connection.execute(BUMP, (collection,))

    async def get(self, collection: str, key: str) -> JsonValue | None:
        pool = await self._pooled.pool()
        async with pool.connection() as connection:
            found = await (
                await connection.execute(
                    "select row from shadow_hdk_rows where collection = %s and key = %s",
                    (collection, key),
                )
            ).fetchone()
        loaded: JsonValue | None = found[0] if found else None
        return loaded

    async def delete(self, collection: str, key: str) -> None:
        pool = await self._pooled.pool()
        async with pool.connection() as connection:
            gone = await connection.execute(
                "delete from shadow_hdk_rows where collection = %s and key = %s", (collection, key)
            )
            if gone.rowcount:
                await connection.execute(BUMP, (collection,))

    async def list(self, collection: str) -> tuple[tuple[str, JsonValue], ...]:
        pool = await self._pooled.pool()
        async with pool.connection() as connection:
            rows = await (
                await connection.execute(
                    "select key, row from shadow_hdk_rows where collection = %s order by key",
                    (collection,),
                )
            ).fetchall()
        return tuple((key, row) for key, row in rows)

    async def version(self, collection: str) -> int:
        pool = await self._pooled.pool()
        async with pool.connection() as connection:
            found = await (
                await connection.execute(
                    "select version from shadow_hdk_versions where collection = %s", (collection,)
                )
            ).fetchone()
        return int(found[0]) if found else 0


__all__ = ["PostgresStore"]
