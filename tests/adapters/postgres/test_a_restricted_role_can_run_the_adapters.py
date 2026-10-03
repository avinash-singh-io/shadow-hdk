"""The adapters run under a role that cannot create tables (BUG-237, Intent Studio BUG-280).

**This test is the defect.** Production runs the backend as a restricted role — one that reads and
writes data and cannot issue DDL, which is correct practice and not a misconfiguration. Every
PostgreSQL adapter executed its table DDL at open, so the application could not start: SQLSTATE
42501. Nothing here ever exercised a restricted role, which is exactly why nobody saw it.

Two things this pins that a privileged test cannot:

**`CREATE TABLE IF NOT EXISTS` is not DDL-free.** PostgreSQL checks the CREATE privilege on the
schema
*before* it checks whether the table exists, so the statement fails against a table that is already
there. That is why lane P's pre-provisioning did not help, and it is why the fix is *do not execute
the schema at runtime* rather than *make the DDL conditional*. There is a test below that holds this
property of the database itself, so a future reader does not have to take it on faith.

**The reopen path.** `aclose()` set `_ready = False`, so the DDL ran again on the next use. A fix
that only covered first use would pass a naive test and still fail in production on the second
connection. Every adapter below is opened, closed and reopened.

Needs two roles, so it runs where `SHADOW_HDK_TEST_POSTGRES_SUPERUSER_URL` is set — CI's
`postgres:16` service, or a local server. Without it the whole module skips, loudly.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

ADMIN = os.environ.get("SHADOW_HDK_TEST_POSTGRES_SUPERUSER_URL", "")

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.skipif(
        not ADMIN,
        reason=(
            "SHADOW_HDK_TEST_POSTGRES_SUPERUSER_URL is not set. This is the only test that can "
            "catch BUG-237's class, because it needs a role that cannot issue DDL — set it to a "
            "connection string with CREATEROLE rights."
        ),
    ),
]

OWNER = "shadow_hdk_t_owner"
RUNTIME = "shadow_hdk_t_runtime"
PASSWORD = "t_only_for_tests"  # noqa: S105 — a local test role, created and dropped in-process


def _one(cursor: Any) -> Any:
    """The first column of the one row a scalar query returns, asserted rather than indexed blindly:
    a query that unexpectedly returns nothing should say so here, not three lines later."""
    row = cursor.fetchone()
    assert row is not None, "a scalar query returned no row"
    return row[0]


def _url_as(role: str) -> str:
    """The admin URL with the role and password swapped in."""
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(ADMIN)
    host = parts.hostname or "localhost"
    port = f":{parts.port}" if parts.port else ""
    return urlunsplit(
        (parts.scheme, f"{role}:{PASSWORD}@{host}{port}", parts.path, parts.query, parts.fragment)
    )


@pytest.fixture
def two_roles() -> Any:
    """An owner role that may create, and a runtime role that may not. Torn down after."""
    import psycopg

    with psycopg.connect(ADMIN, autocommit=True) as connection:
        for table in (
            "shadow_hdk_schema_version",
            "shadow_hdk_effect_journal",
            "shadow_hdk_rows",
            "shadow_hdk_versions",
            "shadow_hdk_threads",
            "shadow_hdk_holds",
            "checkpoint_migrations",
            "checkpoint_writes",
            "checkpoint_blobs",
            "checkpoints",
        ):
            connection.execute(f"drop table if exists {table} cascade")
        for role in (OWNER, RUNTIME):
            connection.execute(f"drop role if exists {role}")
            connection.execute(f"create role {role} login password '{PASSWORD}'")
        database = _one(connection.execute("select current_database()"))
        connection.execute(f'grant connect on database "{database}" to {OWNER}, {RUNTIME}')
        # The owner may create; the runtime role may **not**. That one difference is the test.
        connection.execute(f"grant create, usage on schema public to {OWNER}")
        connection.execute(f"grant usage on schema public to {RUNTIME}")
    yield {"owner": _url_as(OWNER), "runtime": _url_as(RUNTIME)}
    with psycopg.connect(ADMIN, autocommit=True) as connection:
        # Terminate anything still connected as either role first. Without this a pool left open by
        # a failing test makes `drop role` wait forever, and a teardown that hangs turns a reported
        # failure into no result at all — which is the one outcome worse than a red test.
        connection.execute(
            "select pg_terminate_backend(pid) from pg_stat_activity "
            "where usename = any(%s) and pid <> pg_backend_pid()",
            ([OWNER, RUNTIME],),
        )
        connection.execute(f"reassign owned by {OWNER} to {connection.info.user}")
        for role in (OWNER, RUNTIME):
            connection.execute(f"drop owned by {role} cascade")
            connection.execute(f"drop role if exists {role}")


# ----------------------------------------- the property of the database that decides the fix


def test_create_table_if_not_exists_still_needs_the_privilege(two_roles: Any) -> None:
    """Held against the real server, because the whole fix turns on it and it is counter-intuitive.

    Lane P provisioned all nine tables with a trusted role and the adapters still failed. This is
    why: the privilege check comes before the existence check, so `IF NOT EXISTS` is no protection.
    """
    import psycopg

    with psycopg.connect(two_roles["owner"], autocommit=True) as owner:
        owner.execute("create table if not exists shadow_hdk_rows (k text primary key)")

    with (
        psycopg.connect(two_roles["runtime"], autocommit=True) as runtime,
        pytest.raises(psycopg.errors.InsufficientPrivilege),
    ):
        runtime.execute("create table if not exists shadow_hdk_rows (k text primary key)")


# ----------------------------------------- prepare, as the owner


async def test_prepare_makes_every_table_including_langgraphs(two_roles: Any) -> None:
    from shadow_hdk.adapters.postgres import prepare

    await prepare(two_roles["owner"])

    import psycopg

    with psycopg.connect(ADMIN, autocommit=True) as connection:
        present = {
            row[0]
            for row in connection.execute(
                "select tablename from pg_tables where schemaname = 'public'"
            ).fetchall()
        }
    for table in (
        "shadow_hdk_rows",
        "shadow_hdk_versions",
        "shadow_hdk_threads",
        "shadow_hdk_holds",
        "shadow_hdk_effect_journal",
        "shadow_hdk_schema_version",
    ):
        assert table in present, f"{table} missing: {sorted(present)}"
    assert any(t.startswith("checkpoint") for t in present), (
        f"LangGraph's tables are missing, so prepare did not call its setup(): {sorted(present)}"
    )


async def test_prepare_is_idempotent(two_roles: Any) -> None:
    """Lane P runs it on every deploy, unconditionally. Twice must be the same as once."""
    from shadow_hdk.adapters.postgres import prepare

    await prepare(two_roles["owner"])
    await prepare(two_roles["owner"])


async def test_prepare_records_the_version_it_applied(two_roles: Any) -> None:
    """Without this, *behind* has nothing to compare against and would be a claim with nothing
    behind it."""
    import psycopg

    from shadow_hdk.adapters.postgres import SCHEMA_VERSION, prepare

    await prepare(two_roles["owner"])

    with psycopg.connect(ADMIN, autocommit=True) as connection:
        found = connection.execute("select version from shadow_hdk_schema_version").fetchall()
    assert found == [(SCHEMA_VERSION,)], found


# ----------------------------------------- and the runtime role, which may not create


async def _exercise(url: str) -> None:
    """Every adapter: open, an operation, close, **reopen**, another operation. The reopen is the
    half that `aclose()` setting `_ready = False` broke.

    **Every pool is closed in a `finally`**, including on the failure path, and that is not
    tidiness: a left-open pool holds a connection as the runtime role, so the fixture cannot drop
    that role and the teardown hangs instead of reporting. A mutation run discovered that — the
    first version of this left pools open on failure, so the one run that proves the fix *matters*
    could not complete. That is TD-019's shape, in a test written to catch a different bug.
    """
    from shadow_hdk.adapters.postgres import PostgresEffectJournal, PostgresStore, PostgresThreads
    from shadow_hdk.kernel import ThreadRecord

    store = PostgresStore(url)
    try:
        await store.put("modes", "calm", {"id": "calm"})
        assert await store.get("modes", "calm") == {"id": "calm"}
        await store.aclose()
        await store.put("modes", "calm2", {"id": "calm2"})  # reopens the pool
        assert await store.get("modes", "calm2") == {"id": "calm2"}
    finally:
        await store.aclose()

    threads = PostgresThreads(url)
    try:
        made = ThreadRecord(id="t1", root="/w", created_at="2026-01-01T00:00:00+00:00")
        await threads.create(made)
        assert (await threads.get("t1")) is not None
        await threads.aclose()
        assert (await threads.get("t1")) is not None  # reopens
    finally:
        await threads.aclose()

    journal = PostgresEffectJournal(url)
    try:
        assert await journal.read("nothing") == ()
        await journal.aclose()
        assert await journal.read("nothing") == ()  # reopens
    finally:
        await journal.aclose()


async def test_every_adapter_opens_reopens_and_works_under_the_restricted_role(
    two_roles: Any,
) -> None:
    """**BUG-237 itself.** Prepared as the owner, then run as a role that cannot issue DDL."""
    from shadow_hdk.adapters.postgres import prepare, runtime_grants

    await prepare(two_roles["owner"])

    import psycopg

    with psycopg.connect(ADMIN, autocommit=True) as connection:
        for statement in runtime_grants(RUNTIME):
            connection.execute(statement)

    await _exercise(two_roles["runtime"])


async def test_the_restricted_role_is_given_only_what_the_manifest_says(two_roles: Any) -> None:
    """The manifest is the contract with a host's migration owner. If the test granted more than it
    publishes, the manifest would be a wish — which is the class of defect that produced this bug.
    """
    from shadow_hdk.adapters.postgres import prepare, runtime_grants

    await prepare(two_roles["owner"])

    import psycopg

    with psycopg.connect(ADMIN, autocommit=True) as connection:
        for statement in runtime_grants(RUNTIME):
            connection.execute(statement)
        # SELECT only on the version table, as promised to lane P.
        may_write = _one(
            connection.execute(
                "select has_table_privilege(%s, 'shadow_hdk_schema_version', 'INSERT')", (RUNTIME,)
            )
        )
        may_read = _one(
            connection.execute(
                "select has_table_privilege(%s, 'shadow_hdk_schema_version', 'SELECT')", (RUNTIME,)
            )
        )

    assert may_read is True, "runtime must read the version table to verify the schema"
    assert may_write is False, "the manifest promises SELECT only on the version table"


async def test_a_missing_schema_fails_named_rather_than_attempting_ddl(two_roles: Any) -> None:
    """`prepare` was never run. The runtime must say so, not try to fix it."""
    from shadow_hdk.adapters.postgres import PostgresStore, SchemaNotPrepared

    store = PostgresStore(two_roles["runtime"])
    try:
        with pytest.raises(SchemaNotPrepared) as refused:
            await store.get("modes", "calm")
    finally:
        await store.aclose()

    assert "prepare" in str(refused.value).lower(), refused.value


async def test_a_behind_schema_fails_named(two_roles: Any) -> None:
    """The reason the version table exists: *behind* is a fact, not a wish."""
    import psycopg

    from shadow_hdk.adapters.postgres import PostgresStore, SchemaBehind, prepare, runtime_grants

    await prepare(two_roles["owner"])
    with psycopg.connect(ADMIN, autocommit=True) as connection:
        for statement in runtime_grants(RUNTIME):
            connection.execute(statement)
        connection.execute("update shadow_hdk_schema_version set version = 0")

    store = PostgresStore(two_roles["runtime"])
    try:
        with pytest.raises(SchemaBehind) as refused:
            await store.get("modes", "calm")
    finally:
        await store.aclose()

    assert "prepare" in str(refused.value).lower(), refused.value


# ----------------------------------------- and nothing that works today changes


async def test_a_host_explicitly_requesting_self_preparation_can_still_do_so(
    two_roles: Any,
) -> None:
    """Legacy preparation remains an explicit choice for a role that may issue DDL."""
    from shadow_hdk.adapters.postgres import PostgresStore

    store = PostgresStore(two_roles["owner"], prepared=False)
    try:
        await store.put("modes", "calm", {"id": "calm"})
        assert await store.get("modes", "calm") == {"id": "calm"}
    finally:
        await store.aclose()
