"""Schema preparation, separated from runtime access (BUG-237).

**Why this module exists.** A production deployment runs its application as a *restricted* role —
one that reads and writes data and may not issue DDL. That is correct practice, not a
misconfiguration. Every PostgreSQL adapter here used to execute its table DDL at open and again on
every reopen, so such a deployment could not start: SQLSTATE 42501.

**And provisioning the tables in advance did not help**, which is the part that decides the design:
`CREATE TABLE IF NOT EXISTS` is *not* DDL-free. PostgreSQL checks the CREATE privilege on the schema
before it checks whether the table exists, so the statement fails against a table that is already
there. There is a test holding that property of the server itself, because it is counter-intuitive
enough to be worth measuring rather than asserting.

So the split is **trusted preparation** here, run once per deploy by a migration step under an owner
role, and **DDL-free runtime** in the adapters. The host grants its runtime role exactly
`runtime_grants` and no more.
"""

from __future__ import annotations

import sys

from shadow_hdk.adapters.postgres.connection import (
    SCHEMA_VERSION,
    VERSION_SCHEMA,
    VERSION_TABLE,
    require_psycopg,
)
from shadow_hdk.adapters.postgres.effects import SCHEMA as EFFECTS_SCHEMA
from shadow_hdk.adapters.postgres.store import SCHEMA as STORE_SCHEMA
from shadow_hdk.adapters.postgres.threads import SCHEMA as THREADS_SCHEMA

OUR_TABLES = (
    "shadow_hdk_rows",
    "shadow_hdk_versions",
    "shadow_hdk_threads",
    "shadow_hdk_holds",
    "shadow_hdk_effect_journal",
)
"""The tables this kit's own adapters read and write. LangGraph's are its own and are not listed:
their names belong to that library and would go stale here the moment it changed them."""


async def prepare(url: str) -> None:
    """Create and record every table shadow-hdk's PostgreSQL adapters need. Idempotent.

    **Run this under a role that may create tables**, from a migration step, before the application
    starts — and run it **unconditionally on every deploy**, because it is cheap and because
    deciding whether it is needed is exactly the judgement that goes wrong.

    **Re-run it on every shadow-hdk *or LangGraph* upgrade**, not only on a first install.
    `AsyncPostgresSaver.setup()` is LangGraph's, which means its tables change when that library
    changes and nothing here can know that they did.
    """
    require_psycopg()
    import psycopg

    async with await psycopg.AsyncConnection.connect(url, autocommit=True) as connection:
        for schema in (STORE_SCHEMA, THREADS_SCHEMA, EFFECTS_SCHEMA, VERSION_SCHEMA):
            await connection.execute(schema)
        await connection.execute(
            f"insert into {VERSION_TABLE} (id, version) values (1, %s) "
            "on conflict (id) do update set version = excluded.version",
            (SCHEMA_VERSION,),
        )
    # LangGraph's own tables, under this same owner role — the whole point of one entry point.
    await _prepare_langgraph(url)


async def _prepare_langgraph(url: str) -> None:
    """LangGraph's checkpoint tables, through its own `setup()`.

    It is third-party, so it cannot be made DDL-free from here; the only honest arrangement is that
    **we** call it under the owner role and the runtime path never does.
    """
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg import AsyncConnection
    from psycopg.rows import dict_row

    async with await AsyncConnection.connect(
        url, autocommit=True, prepare_threshold=0, row_factory=dict_row
    ) as connection:
        await AsyncPostgresSaver(connection).setup()


def runtime_grants(role: str) -> tuple[str, ...]:
    """The grants a restricted runtime role needs, and no more (BUG-237).

    Data, not prose, so a host's migration owner can apply it rather than transcribe it — and so
    this kit's own test can grant exactly what it publishes. A manifest the tests do not use is a
    wish.

    **`SELECT` only on the version table.** The runtime reads it to verify the schema and has no
    business writing it; writing it is `prepare`'s job, under a different role.
    """
    tables = ", ".join(OUR_TABLES)
    return (
        f"grant usage on schema public to {role}",
        f"grant select, insert, update, delete on {tables} to {role}",
        f"grant select on {VERSION_TABLE} to {role}",
        f"grant usage, select on all sequences in schema public to {role}",
        # LangGraph owns these names, so they are granted by pattern rather than listed: a list here
        # would go stale the moment that library adds a table, and silently.
        f"grant select, insert, update, delete on all tables in schema public to {role}",
        f"revoke insert, update, delete on {VERSION_TABLE} from {role}",
    )


def main(argv: list[str] | None = None) -> int:
    """`shadow-hdk-prepare <url>` — what a migration step runs."""
    import asyncio

    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1 or args[0] in {"-h", "--help"}:
        print(
            "usage: shadow-hdk-prepare <postgres-url>\n\n"
            "Creates and records every table shadow-hdk's PostgreSQL adapters need, including\n"
            "LangGraph's checkpoint tables. Idempotent. Run it under a role that may create\n"
            "tables, before the application starts, on every deploy — and after any shadow-hdk\n"
            "or LangGraph upgrade.",
            file=sys.stderr,
        )
        return 2
    asyncio.run(prepare(args[0]))
    print(f"shadow-hdk: schema prepared at version {SCHEMA_VERSION}")
    return 0


__all__ = ["OUR_TABLES", "main", "prepare", "runtime_grants"]
