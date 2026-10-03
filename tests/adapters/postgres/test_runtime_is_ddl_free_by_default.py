"""The first 0.45 release makes trusted preparation the default boundary."""

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("kind", ["store", "threads", "effects"])
async def test_default_open_and_reopen_verify_without_ddl(monkeypatch: Any, kind: str) -> None:
    import psycopg_pool

    from shadow_hdk.adapters.postgres import (
        PostgresEffectJournal,
        PostgresStore,
        PostgresThreads,
        connection,
    )

    queries: list[str] = []
    verified: list[str] = []

    class Connection:
        async def execute(self, sql: str) -> None:
            queries.append(sql)

    class Pool:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def open(self) -> None:
            pass

        async def close(self) -> None:
            pass

        @asynccontextmanager
        async def connection(self) -> Any:
            yield Connection()

    async def verify(opened: Any) -> None:
        verified.append("verified")

    monkeypatch.setattr(psycopg_pool, "AsyncConnectionPool", Pool)
    monkeypatch.setattr(connection, "_verify", verify)
    constructors: dict[str, Any] = {
        "store": PostgresStore,
        "threads": PostgresThreads,
        "effects": PostgresEffectJournal,
    }
    adapter = constructors[kind]("postgresql://unused")
    await adapter._pooled.pool()
    await adapter.aclose()
    await adapter._pooled.pool()
    await adapter.aclose()
    assert (queries, verified) == ([], ["verified", "verified"])


async def test_self_preparation_remains_explicit(monkeypatch: Any) -> None:
    from shadow_hdk.adapters.postgres.connection import Pooled

    pool = Pooled("postgresql://unused", schema="DDL-SENTINEL", prepared=False)
    execute = AsyncMock()

    @asynccontextmanager
    async def connection() -> Any:
        yield type("Connection", (), {"execute": execute})()

    pool._pool = type("Pool", (), {"connection": staticmethod(connection)})()
    await pool.pool()
    execute.assert_awaited_once_with("DDL-SENTINEL")


@pytest.mark.parametrize("options, setups", [({}, 0), ({"prepared": False}, 1)])
async def test_checkpointer_does_not_setup_by_default(
    monkeypatch: Any, options: dict[str, bool], setups: int
) -> None:
    import psycopg
    from langgraph.checkpoint.postgres import aio

    from shadow_hdk.adapters.postgres.checkpoints import postgres_checkpointer

    setup = AsyncMock()
    monkeypatch.setattr(psycopg.AsyncConnection, "connect", AsyncMock(return_value=object()))
    monkeypatch.setattr(aio.AsyncPostgresSaver, "setup", setup)
    await postgres_checkpointer("postgresql://unused", **options)
    assert setup.await_count == setups
