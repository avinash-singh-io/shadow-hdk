"""Reference effect journals satisfy the same append-only product contract."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from shadow_hdk.adapters.basic.effects import SqliteEffectJournal
from shadow_hdk.kernel import EffectEntry
from shadow_hdk.runtime import InMemoryEffectJournal, JournalConflict
from shadow_hdk.testing import EffectJournalContract

pytestmark = pytest.mark.anyio


def entries() -> tuple[EffectEntry, EffectEntry]:
    return (
        EffectEntry("attempt-1", 0, "staged", "digest-1", "2026-09-15T12:00:00+00:00"),
        EffectEntry(
            "attempt-1",
            1,
            "authorized",
            "digest-1",
            "2026-09-15T12:00:01+00:00",
            authorization_id="grant-1",
        ),
    )


class TestMemoryEffectJournal(EffectJournalContract):
    def journal(self) -> InMemoryEffectJournal:
        return InMemoryEffectJournal()

    def entries(self) -> tuple[EffectEntry, EffectEntry]:
        return entries()


class TestSqliteEffectJournal(EffectJournalContract):
    def journal(self) -> SqliteEffectJournal:
        return SqliteEffectJournal(":memory:")

    def entries(self) -> tuple[EffectEntry, EffectEntry]:
        return entries()


async def test_sqlite_history_survives_a_new_process_handle(tmp_path: Path) -> None:
    path = tmp_path / "effects.sqlite"
    first = SqliteEffectJournal(path)
    one, two = entries()
    await first.append(one, expected_length=0)
    await first.append(two, expected_length=1)
    assert await SqliteEffectJournal(path).read("attempt-1") == (one, two)


async def test_two_sqlite_handles_serialize_the_same_tail(tmp_path: Path) -> None:
    path = tmp_path / "effects.sqlite"
    first = SqliteEffectJournal(path)
    second = SqliteEffectJournal(path)
    one, _ = entries()
    await first.append(one, expected_length=0)
    left = EffectEntry("attempt-1", 1, "refused", "digest-1", "2026-09-15T12:00:01+00:00")
    right = EffectEntry(
        "attempt-1",
        1,
        "authorized",
        "digest-1",
        "2026-09-15T12:00:01+00:00",
        authorization_id="grant-2",
    )
    results = await asyncio.gather(
        first.append(left, expected_length=1),
        second.append(right, expected_length=1),
        return_exceptions=True,
    )
    assert sum(isinstance(result, JournalConflict) for result in results) == 1
    assert len(await first.read("attempt-1")) == 2


@pytest.mark.parametrize(
    "factory", [InMemoryEffectJournal, lambda: SqliteEffectJournal(":memory:")]
)
async def test_two_concurrent_writers_cannot_take_the_same_tail(factory: object) -> None:
    journal = factory()  # type: ignore[operator]
    one, _ = entries()
    await journal.append(one, expected_length=0)
    left = EffectEntry("attempt-1", 1, "refused", "digest-1", "2026-09-15T12:00:01+00:00")
    right = EffectEntry(
        "attempt-1",
        1,
        "authorized",
        "digest-1",
        "2026-09-15T12:00:01+00:00",
        authorization_id="grant-2",
    )
    results = await asyncio.gather(
        journal.append(left, expected_length=1),
        journal.append(right, expected_length=1),
        return_exceptions=True,
    )
    assert sum(isinstance(result, JournalConflict) for result in results) == 1
    assert len(await journal.read("attempt-1")) == 2
