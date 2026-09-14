"""A `ThreadStore` on sqlite: threads outlive the process that opened them (D62).

The shipped default. A product keeps threads in its own tables by implementing the port; this is
what a host gets with nothing to write. Every record field round-trips, listing hides archived
threads unless asked, and a second store over the same file sees what the first wrote.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.adapters.basic import SqliteThreads
from shadow_hdk.kernel import ThreadRecord, TurnRecord
from shadow_hdk.testing.contracts import ThreadStoreContract

pytestmark = pytest.mark.anyio


def a_thread(thread_id: str, *, turns: int = 2, **fields: object) -> ThreadRecord:
    return ThreadRecord(
        id=thread_id,
        root="/work",
        created_at="2026-09-12T00:00:00+00:00",
        mode="confined",
        provider="Claude Code 2.1",
        turns=tuple(
            TurnRecord(
                id=f"turn-{i + 1}",
                run_id=f"run-{i + 1}",
                prompt=f"prompt {i + 1}",
                at="2026-09-12T00:00:01+00:00",
                outcome="completed",
                text=f"answer {i + 1}",
            )
            for i in range(turns)
        ),
        **fields,  # type: ignore[arg-type]
    )


async def test_a_record_round_trips_field_for_field(tmp_path: Path) -> None:
    store = SqliteThreads(tmp_path / "threads.sqlite")
    record = a_thread("t1", forked_from="t0", seeded_turns=1, session_id="claude-abc")
    await store.create(record)

    assert await store.get("t1") == record


async def test_save_replaces_and_a_second_store_sees_it(tmp_path: Path) -> None:
    where = tmp_path / "threads.sqlite"
    first = SqliteThreads(where)
    await first.create(a_thread("t1", turns=1))
    await first.save(a_thread("t1", turns=3))

    second = SqliteThreads(where)
    found = await second.get("t1")
    assert found is not None and [t.prompt for t in found.turns] == [
        "prompt 1",
        "prompt 2",
        "prompt 3",
    ]


async def test_listing_hides_archived_unless_asked(tmp_path: Path) -> None:
    store = SqliteThreads(tmp_path / "threads.sqlite")
    await store.create(a_thread("a"))
    await store.create(a_thread("b"))
    await store.archive("b")

    assert [t.id for t in await store.list()] == ["a"]
    assert sorted(t.id for t in await store.list(include_archived=True)) == ["a", "b"]
    archived = await store.get("b")
    assert archived is not None and archived.archived


async def test_a_missing_thread_is_none_not_an_error(tmp_path: Path) -> None:
    store = SqliteThreads(tmp_path / "threads.sqlite")
    assert await store.get("nobody") is None


class TestSqliteThreadsIsAThreadStore(ThreadStoreContract):
    def store(self) -> SqliteThreads:
        import tempfile

        return SqliteThreads(Path(tempfile.mkdtemp()) / "threads.sqlite")
