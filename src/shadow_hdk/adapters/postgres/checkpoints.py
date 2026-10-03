"""The checkpointer a Postgres url names: LangGraph's own, on a connection this module opens and
the caller closes — so a parked run sleeps in the same database as the record (D80)."""

from __future__ import annotations

from typing import Any

from shadow_hdk.adapters.postgres.connection import require_psycopg


async def postgres_checkpointer(url: str, *, prepared: bool = True) -> tuple[Any, Any]:
    """The saver and what closes it.

    `setup()` makes its tables the first time — **which is DDL**, so a restricted runtime role
    cannot run it (BUG-237). `prepared=True` skips it, on the understanding that `prepare(url)`
    already called it under an owner role. It is LangGraph's own function and cannot be made
    DDL-free here, so calling it from the one trusted place is the only honest arrangement.
    """
    require_psycopg()
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg import AsyncConnection
    from psycopg.rows import dict_row

    connection = await AsyncConnection.connect(
        url, autocommit=True, prepare_threshold=0, row_factory=dict_row
    )
    saver = AsyncPostgresSaver(connection)
    if not prepared:
        await saver.setup()
    return saver, connection


__all__ = ["postgres_checkpointer"]
