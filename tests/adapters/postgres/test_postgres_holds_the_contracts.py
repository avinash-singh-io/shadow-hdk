"""A `Store` and a `ThreadStore` on Postgres (Phase 29 group 1, D79): the same contracts the
sqlite ones hold, against a real server. The tables are made on first use; a second store over
the same url sees what the first wrote, because the rows are the server's, not the object's."""

from __future__ import annotations

import os
from typing import Any

import pytest

from shadow_hdk.testing.contracts import StoreContract, ThreadStoreContract
from tests.adapters.postgres.conftest import wiped

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        not os.environ.get("SHADOW_HDK_TEST_POSTGRES_URL"),
        reason="SHADOW_HDK_TEST_POSTGRES_URL is not set",
    ),
]

URL = os.environ.get("SHADOW_HDK_TEST_POSTGRES_URL", "")


def _fresh(kind: str) -> Any:
    """A store over wiped tables. The wipe runs synchronously here because the contract suites
    build their store inside the test body, before any `await`."""
    import psycopg

    from shadow_hdk.adapters.postgres import PostgresStore, PostgresThreads

    with psycopg.connect(URL, autocommit=True) as connection:
        for table in (
            "shadow_hdk_rows",
            "shadow_hdk_versions",
            "shadow_hdk_threads",
            "shadow_hdk_holds",
        ):
            connection.execute(f"drop table if exists {table}")
    return PostgresStore(URL) if kind == "store" else PostgresThreads(URL)


class TestPostgresStoreIsAStore(StoreContract):
    def store(self) -> Any:
        return _fresh("store")


class TestPostgresThreadsIsAThreadStore(ThreadStoreContract):
    def store(self) -> Any:
        return _fresh("threads")


async def test_a_second_store_over_the_same_url_sees_the_rows_and_the_version() -> None:
    from shadow_hdk.adapters.postgres import PostgresStore

    await wiped(URL)
    first = PostgresStore(URL)
    await first.put("modes", "calm", {"id": "calm", "n": [1, {"x": None}]})
    second = PostgresStore(URL)
    assert await second.get("modes", "calm") == {"id": "calm", "n": [1, {"x": None}]}
    assert await second.version("modes") == 1
    await first.aclose()
    await second.aclose()


async def test_a_second_thread_store_over_the_same_url_sees_the_threads() -> None:
    from shadow_hdk.adapters.postgres import PostgresThreads
    from shadow_hdk.kernel import ThreadRecord

    await wiped(URL)
    first = PostgresThreads(URL)
    await first.create(ThreadRecord(id="t1", root="/w", created_at="2026-01-01T00:00:00+00:00"))
    second = PostgresThreads(URL)
    assert [t.id for t in await second.list()] == ["t1"]
    await first.aclose()
    await second.aclose()
