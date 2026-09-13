"""The Postgres adapter's tests run against a real server, named by
`SHADOW_HDK_TEST_POSTGRES_URL` — the desk's local Postgres, CI's service container — and are
skipped, saying so, where there is none. Every test starts from wiped tables."""

from __future__ import annotations

import os

import pytest

POSTGRES = os.environ.get("SHADOW_HDK_TEST_POSTGRES_URL")

TABLES = (
    "shadow_hdk_rows",
    "shadow_hdk_versions",
    "shadow_hdk_threads",
    "checkpoints",
    "checkpoint_blobs",
    "checkpoint_writes",
    "checkpoint_migrations",
)


async def wiped(url: str) -> None:
    """Drop what the adapter and the checkpointer make, so a test starts from nothing."""
    import psycopg

    async with await psycopg.AsyncConnection.connect(url, autocommit=True) as connection:
        for table in TABLES:
            await connection.execute(f"drop table if exists {table} cascade")


@pytest.fixture
def postgres_url() -> str:
    if not POSTGRES:
        pytest.skip("SHADOW_HDK_TEST_POSTGRES_URL is not set")
    return POSTGRES
