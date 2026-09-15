"""A durable append-only effect journal on Postgres (D101-D104)."""

from __future__ import annotations

import json
from typing import Any, cast

from shadow_hdk.adapters.postgres.connection import Pooled
from shadow_hdk.kernel.authority import EffectEntry, EffectEntryKind
from shadow_hdk.kernel.ports import EffectJournalPort
from shadow_hdk.runtime.effects import JournalConflict, fold_effect

SCHEMA = """
create table if not exists shadow_hdk_effect_journal (
    attempt_id text not null,
    sequence bigint not null,
    kind text not null,
    stage_digest text not null,
    at text not null,
    authorization_id text unique,
    detail jsonb,
    primary key (attempt_id, sequence)
);
"""


def _entries(rows: list[tuple[Any, ...]]) -> tuple[EffectEntry, ...]:
    return tuple(
        EffectEntry(
            attempt_id=row[0],
            sequence=row[1],
            kind=cast(EffectEntryKind, row[2]),
            stage_digest=row[3],
            at=row[4],
            authorization_id=row[5],
            detail=row[6],
        )
        for row in rows
    )


class PostgresEffectJournal(EffectJournalPort):
    """Compare-and-append serialized by an attempt-scoped transaction advisory lock."""

    def __init__(self, url: str) -> None:
        self._pooled = Pooled(url, schema=SCHEMA)

    async def aclose(self) -> None:
        await self._pooled.aclose()

    async def read(self, attempt_id: str) -> tuple[EffectEntry, ...]:
        pool = await self._pooled.pool()
        async with pool.connection() as connection:
            rows = await (
                await connection.execute(
                    "select attempt_id, sequence, kind, stage_digest, at, authorization_id, detail "
                    "from shadow_hdk_effect_journal where attempt_id = %s order by sequence",
                    (attempt_id,),
                )
            ).fetchall()
        return _entries(rows)

    async def append(self, entry: EffectEntry, *, expected_length: int) -> None:
        from psycopg.errors import UniqueViolation

        pool = await self._pooled.pool()
        try:
            async with pool.connection() as connection, connection.transaction():
                await connection.execute(
                    "select pg_advisory_xact_lock(hashtextextended(%s, 0))",
                    (entry.attempt_id,),
                )
                rows = await (
                    await connection.execute(
                        "select attempt_id, sequence, kind, stage_digest, at, "
                        "authorization_id, detail from shadow_hdk_effect_journal "
                        "where attempt_id = %s order by sequence",
                        (entry.attempt_id,),
                    )
                ).fetchall()
                current = _entries(rows)
                if len(current) != expected_length:
                    raise JournalConflict(
                        "effect history moved from expected length "
                        f"{expected_length} to {len(current)}"
                    )
                try:
                    fold_effect((*current, entry))
                except ValueError as error:
                    raise JournalConflict(str(error)) from error
                await connection.execute(
                    "insert into shadow_hdk_effect_journal "
                    "(attempt_id, sequence, kind, stage_digest, at, authorization_id, detail) "
                    "values (%s, %s, %s, %s, %s, %s, %s::jsonb)",
                    (
                        entry.attempt_id,
                        entry.sequence,
                        entry.kind,
                        entry.stage_digest,
                        entry.at,
                        entry.authorization_id,
                        json.dumps(entry.detail, sort_keys=True, separators=(",", ":")),
                    ),
                )
        except UniqueViolation as error:
            raise JournalConflict(
                "effect authorization or sequence was already consumed"
            ) from error


__all__ = ["PostgresEffectJournal"]
