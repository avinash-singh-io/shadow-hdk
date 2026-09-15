"""A durable append-only effect journal on SQLite (D101-D104)."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

from shadow_hdk.kernel.authority import EffectEntry
from shadow_hdk.kernel.ports import EffectJournalPort
from shadow_hdk.runtime.effects import JournalConflict, fold_effect

SCHEMA = """
create table if not exists effect_journal (
    attempt_id text not null,
    sequence integer not null,
    kind text not null,
    stage_digest text not null,
    at text not null,
    authorization_id text unique,
    detail text,
    primary key (attempt_id, sequence)
);
"""


class SqliteEffectJournal(EffectJournalPort):
    """One connection per handle; SQLite serializes compare-and-append across handles."""

    def __init__(self, path: Path | str) -> None:
        self._connection = sqlite3.connect(str(path), check_same_thread=False)
        self._connection.executescript(SCHEMA)
        self._lock = asyncio.Lock()

    def _read(self, attempt_id: str) -> tuple[EffectEntry, ...]:
        rows = self._connection.execute(
            "select attempt_id, sequence, kind, stage_digest, at, authorization_id, detail "
            "from effect_journal where attempt_id = ? order by sequence",
            (attempt_id,),
        ).fetchall()
        return tuple(
            EffectEntry(
                attempt_id=row[0],
                sequence=row[1],
                kind=row[2],
                stage_digest=row[3],
                at=row[4],
                authorization_id=row[5],
                detail=json.loads(row[6]) if row[6] is not None else None,
            )
            for row in rows
        )

    async def read(self, attempt_id: str) -> tuple[EffectEntry, ...]:
        async with self._lock:
            return await asyncio.to_thread(self._read, attempt_id)

    def _append(self, entry: EffectEntry, expected_length: int) -> None:
        try:
            self._connection.execute("begin immediate")
            current = self._read(entry.attempt_id)
            if len(current) != expected_length:
                raise JournalConflict(
                    f"effect history moved from expected length {expected_length} to {len(current)}"
                )
            try:
                fold_effect((*current, entry))
            except ValueError as error:
                raise JournalConflict(str(error)) from error
            self._connection.execute(
                "insert into effect_journal "
                "(attempt_id, sequence, kind, stage_digest, at, authorization_id, detail) "
                "values (?, ?, ?, ?, ?, ?, ?)",
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
            self._connection.commit()
        except sqlite3.IntegrityError as error:
            self._connection.rollback()
            raise JournalConflict(
                "effect authorization or sequence was already consumed"
            ) from error
        except BaseException:
            self._connection.rollback()
            raise

    async def append(self, entry: EffectEntry, *, expected_length: int) -> None:
        async with self._lock:
            await asyncio.to_thread(self._append, entry, expected_length)


__all__ = ["SqliteEffectJournal"]
