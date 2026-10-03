"""One pool per store object, opened on first use — inside the running loop, which is where
psycopg's async pool wants to be opened — and closed by `aclose`."""

from __future__ import annotations

from typing import Any

INSTALL = "the `postgres` extra is not installed: pip install 'shadow-hdk[postgres]'"

VERSION_TABLE = "shadow_hdk_schema_version"
"""Where `prepare` records the schema it applied (BUG-237).

Without it *"migrates"* has nothing to migrate from and *"behind"* has nothing to compare against,
and shipping either as a claim with nothing behind it is the class of defect this kit has spent two
phases removing. `shadow_hdk_versions` is **not** this table — that one holds per-collection row
versions for the store's optimistic concurrency, and the names being similar is a trap worth naming.
"""

SCHEMA_VERSION = 1
"""The schema this code expects. Bumped when a table changes shape, never for a data change."""

VERSION_SCHEMA = f"""
create table if not exists {VERSION_TABLE} (
    id integer primary key default 1,
    version integer not null,
    constraint {VERSION_TABLE}_one_row check (id = 1)
);
"""


class SchemaNotPrepared(RuntimeError):
    """A DDL-free adapter opened against a database nobody prepared (BUG-237).

    Named rather than attempted. A runtime role has no business issuing DDL, and a database with no
    tables is a deployment that skipped a step — so the honest answer is to say which step.
    """


class SchemaBehind(RuntimeError):
    """The schema is older than this code expects (BUG-237).

    The reason `VERSION_TABLE` exists: without a recorded version this condition cannot be detected
    and *"fails named when the schema is behind"* would be a promise with nothing behind it.
    """


def require_psycopg() -> None:
    """Raise, naming the extra, before anything is half-built."""
    try:
        import psycopg  # noqa: F401
        import psycopg_pool  # noqa: F401
    except ImportError as missing:
        raise ImportError(INSTALL) from missing


async def _verify(connection: Any) -> None:
    """Is the schema there, and is it current (BUG-237)? No DDL, and no DML either.

    **Two statements rather than one join.** PostgreSQL parses a whole statement before running it,
    so a query that joins the version table in order to discover whether the version table exists
    raises `UndefinedTable` instead of answering — which is what the first version of this did. The
    catalogue lookup has to stand alone.

    Cheap, and it turns *the schema is behind* into a named error at startup rather than a confusing
    failure on whichever statement first meets a missing column.
    """
    found = await connection.execute(
        "select 1 from pg_catalog.pg_class "
        "join pg_catalog.pg_namespace on pg_namespace.oid = pg_class.relnamespace "
        "where pg_class.relname = %s and pg_namespace.nspname = current_schema()",
        (VERSION_TABLE,),
    )
    if await found.fetchone() is None:
        raise SchemaNotPrepared(
            f"this database has no {VERSION_TABLE!r}, so shadow-hdk's schema was never prepared: "
            "run `shadow-hdk-prepare <url>` under a role that may create tables, "
            "before starting the application"
        )
    found = await connection.execute(f"select version from {VERSION_TABLE}")
    row = await found.fetchone()
    at = None if row is None else int(row[0])
    if at is None or at < SCHEMA_VERSION:
        raise SchemaBehind(
            f"shadow-hdk's schema is at version {at} and this code expects {SCHEMA_VERSION}: "
            "run `shadow-hdk-prepare <url>` under a role that may create tables. It is re-run on "
            "every shadow-hdk or LangGraph upgrade, not only on a first install"
        )


class Pooled:
    """The connection pool a Postgres adapter draws from."""

    def __init__(self, url: str, *, schema: str, prepared: bool) -> None:
        require_psycopg()
        self._url = url
        self._schema = schema
        self._prepared = prepared
        """Whether a trusted `prepare` already made the tables (BUG-237).

        `True` means **this pool issues no DDL at all** — not conditional DDL, because `CREATE TABLE
        IF NOT EXISTS` is not DDL-free: PostgreSQL checks the CREATE privilege on the schema
        *before* it checks whether the table exists, so the statement fails with 42501 against a
        table that is already there. That is why a host provisioning its tables in advance did not
        help, and why this is a separate path rather than a smarter statement.

        Public adapters pass `True` by default from 0.45.0: prepare before runtime use.
        `prepared=False` explicitly opts into legacy self-preparation under a DDL-capable role.
        """
        self._pool: Any = None
        self._ready = False

    async def pool(self) -> Any:
        from psycopg_pool import AsyncConnectionPool

        if self._pool is None:
            self._pool = AsyncConnectionPool(self._url, open=False, min_size=1, max_size=4)
            await self._pool.open()
        if not self._ready:
            async with self._pool.connection() as connection:
                if self._prepared:
                    # No DDL, ever, on this path (BUG-237) — not even `IF NOT EXISTS`, which still
                    # needs the CREATE privilege. A reopen comes back through here and re-verifies,
                    # which is one cheap catalogue query rather than the DDL that used to re-run.
                    await _verify(connection)
                else:
                    await connection.execute(self._schema)
            self._ready = True
        return self._pool

    async def aclose(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            self._ready = False


__all__ = [
    "INSTALL",
    "SCHEMA_VERSION",
    "VERSION_SCHEMA",
    "VERSION_TABLE",
    "Pooled",
    "SchemaBehind",
    "SchemaNotPrepared",
    "require_psycopg",
]
