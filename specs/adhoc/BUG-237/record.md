---
type: Ad-hoc Record
---

# Ad-hoc Work Record: BUG-237

> **Type**: quick-task
> **Created**: 2026-10-03
> **Branch**: `fix/BUG-237-postgres-ddl-at-runtime`, from the **v0.44.0 tag** (`f693827`)
> **Backlog**: BUG-237 (P0)
> **Status**: shipped
> **Releases as**: 0.44.1

## Why this is a quick-task and not a phase (Rule 14, stated rather than skipped)

It meets **two** of Rule 14's escalation triggers: it **changes a public contract** (adds a `prepare`
function, a console script, a DDL-free constructor argument and a grants manifest) and it touches
about **seven** production files, against the "~5" guidance.

It stays a quick-task on the owner's decision of 2026-10-03, for two reasons worth recording so this
is not read later as ceremony skipped by accident:

- The owner scoped `shadow-hdk` to **maintenance and corrections only**. A phase for a correction is
  the ceremony that scope decision exists to avoid.
- The contract addition is **additive**, which D9 already has a mechanism for — a minor or patch plus
  a *Pins* row. Rule 14's trigger guards against a *redesign* arriving through the ad-hoc lane; this
  is a defect fix whose shape was settled with lane P before any code was written.

What that costs: no phase history, so **this record is the only place the reasoning lives**. It is
written accordingly.

## Current Behavior

`Pooled.pool()` (`src/shadow_hdk/adapters/postgres/connection.py`) executes its table DDL on **first
use and again after every `aclose()`**, because `aclose` sets `_ready = False`. A production runtime
role with no DDL rights fails with **SQLSTATE 42501** and the application cannot start.

Four adapters do it. Nine tables:

| adapter | tables |
|---|---|
| `postgres/store.py` | `shadow_hdk_rows`, `shadow_hdk_versions` |
| `postgres/threads.py` | `shadow_hdk_threads`, `shadow_hdk_holds` |
| `postgres/effects.py` | `shadow_hdk_effect_journal` |
| `postgres/checkpoints.py` | LangGraph's four, via `AsyncPostgresSaver.setup()` |

**Provisioning the tables in advance does not help**, which is the part that decides the fix:
`CREATE TABLE IF NOT EXISTS` is **not** DDL-free. PostgreSQL checks the CREATE privilege on the schema
*before* it checks whether the table exists, so the statement fails against a table that is already
there. So the fix cannot be *make the DDL conditional* — it must be *do not execute the schema at
runtime at all*.

Reported as Intent Studio's BUG-280 by lane P's Codex release lane; it blocks their 0.7.0.

## Expected Behavior

1. **`prepare(url)`** — a function and a console script, idempotent, run by a host's migration step
   under an **owner** role. It creates every table the PostgreSQL adapters use **and calls LangGraph's
   `AsyncPostgresSaver.setup()`**, which is third-party and cannot be made DDL-free from here. It
   records the applied version.
2. **A one-row schema-version table**, written by `prepare`. Without it *"migrate"* has nothing to
   migrate from and *"behind"* nothing to compare against; shipping either as a claim with nothing
   behind it is the defect class phases 65 and 66 existed to remove.
3. **A DDL-free runtime path, opt-in** in 0.44.1. It executes no schema, and **`aclose()` must not
   re-arm the schema execution on reopen** — that reopen path is the half lane P measured. The
   self-preparing behaviour stays the **default** in 0.44.1: a patch must not invert behaviour for
   users who are not lane P. The default flips in the first 0.45 release.
4. **A schema check per adapter open** — one catalogue query, no DDL — failing with a **named** error
   for *missing* and for *behind*.
5. **A runtime-grants manifest**, as data a host can read: the tables, their privileges, and
   **SELECT only** on the version table.
6. **A two-role test**: prepare as an owner role, then every adapter's **open, reopen and ordinary
   operations** as a role holding only the manifest's grants.

## Unchanged Behavior

The blast-radius guardrail. None of this may change:

- **A host that passes no flag behaves exactly as 0.44.0 did** — self-preparing, DDL at open. That is
  the whole reason the DDL-free path is opt-in here.
- **SQLite and in-memory stores are untouched.** This is a PostgreSQL-adapter correction.
- **No table's columns, names, indexes or semantics change.** `shadow_hdk_versions` in particular
  keeps its current meaning — per-collection row versions for the store's optimistic concurrency. It
  is **not** the new schema-version table and must not be confused with it.
- **No wire change, no protocol change.** Protocol 3 unchanged.
- Every existing PostgreSQL test keeps passing against a privileged role.

## Verification Evidence

Captured 2026-10-03 on `fix/BUG-237-postgres-ddl-at-runtime` (from the v0.44.0 tag), macOS 26
(Darwin 27.0.0), Python 3.14.6, **PostgreSQL 16.14** on a local server. Every exit code read from a
file; `pytest` never through a pipe.

Two databases and two roles: `prepare` as an owner role that may create tables, then every adapter
exercised as a role that may not.

### `uv run ruff check .` · `ruff format --check .` · `mypy`

```
All checks passed!
540 files already formatted
Success: no issues found in 509 source files
exit 0, 0, 0
```

### `uv run pytest -q` — with both PostgreSQL URLs set

```
2167 passed, 8 skipped, 23 deselected, 85 warnings
exit=0
```

Skips fell from 20 to 8: the PostgreSQL suites now run rather than reporting an unset variable.

### The new test, against two real roles

```
tests/adapters/postgres/test_a_restricted_role_can_run_the_adapters.py
9 passed
```

Including the one that holds the property the whole fix turns on — that
`CREATE TABLE IF NOT EXISTS` is refused to a role without CREATE **even when the table exists** —
measured against the server rather than asserted.

### `shadow-hdk-prepare`, end to end

```
$ uv run shadow-hdk-prepare "postgresql:///shadow_hdk_cli?host=/tmp"
shadow-hdk: schema prepared at version 1
$ psql -d shadow_hdk_cli -tAc "select tablename from pg_tables where schemaname='public' order by 1;"
checkpoint_blobs checkpoint_migrations checkpoint_writes checkpoints
shadow_hdk_effect_journal shadow_hdk_holds shadow_hdk_rows shadow_hdk_schema_version
shadow_hdk_threads shadow_hdk_versions
$ uv run shadow-hdk-prepare "postgresql:///shadow_hdk_cli?host=/tmp"   # idempotent
shadow-hdk: schema prepared at version 1
$ uv run shadow-hdk-prepare ; echo $?                                  # usage
2
```

Ten tables: five of ours, the version table, and LangGraph's four.

### Mutations — five, all biting

| mutation | caught by |
|---|---|
| `if self._prepared:` → `if False:` (the flag accepted and ignored) | 3 tests |
| `prepare` stops calling LangGraph's `setup()` | the table-presence test |
| the manifest grants INSERT on the version table instead of revoking it | the manifest test |
| `SchemaNotPrepared` never raised | the missing-schema test |
| `SchemaBehind` never raised | the behind-schema test |

### CI

`SHADOW_HDK_TEST_POSTGRES_SUPERUSER_URL` added to `.github/workflows/ci.yml`, so the two-role test
runs there and not only on one desk. Without it the test skips saying so, and the defect it exists to
catch would be invisible again.

## What went wrong on the way, and is worth knowing

**The `prepared` flag was accepted and ignored for a while, and a test passed anyway.** The branch in
`Pooled.pool()` did not land on the first edit; the signature took the argument, nothing read it, and
nine tests reported green. That is **BUG-230's exact shape** — a field parsed and honoured nowhere —
inside the fix for a different bug. It was caught by noticing the branch missing while setting up a
mutation, not by the suite. The mutation now exists and bites on three tests, which is the only reason
to believe the flag does anything.

**A killed mutation run left `if False:` in the source.** `mutate-one.py` restores in a `finally`,
which `pkill` skips. Checking `git diff` after an interrupted run is not optional, and the script's own
docstring says so.

**My own test had TD-019's shape.** On the failure path it left connection pools open, so the fixture
could not drop the roles and teardown hung — meaning the one run that proves the fix matters could not
complete. Pools now close in `finally` and the fixture terminates stray backends before dropping
roles.

**A line-reflow helper corrupted source twice** — once joining a string concatenation, once merging
three statements into one line — and has been **removed from the repository**. A tool that silently
breaks code is worse than the tedium it saves.

## Shipped

**v0.44.1, 2026-10-03.** Merged to `staging` and `main`, tagged, and released. Published to PyPI:
`shadow-hdk==0.44.1` (2 files) and `shadow-hdk-linux-sandbox==0.44.1` (5), **7 between them**, as
every release of this pair should have. Publish workflow green on nine of ten jobs with the
fresh-install smoke still running at the time of writing; verified independently of it from a clean
virtualenv **outside CI**, which is this project's habit because the pair has shipped half-published
before:

```
installed: 0.44.1
schema version: 1
prepared= on the store: True
pool() has the DDL-free branch: True
grants: 6 | version table SELECT-only: True
named errors present: SchemaNotPrepared SchemaBehind
shadow-hdk-prepare exit=2   (usage, so the console script shipped)
```

`pool() has the DDL-free branch` is asserted against the **installed wheel** on purpose: the flag was
accepted and ignored at one point during this work, so *"the published artifact actually honours it"*
is the claim worth checking rather than assuming.

One note for whoever next reads the release-tag hook: it looks for the newest **retrospective's**
`## Verification Evidence`, and an ad-hoc release's evidence lives in this record instead. The push
passed on phase 65's retrospective, which is in this tree — so the gate was satisfied by the right
kind of document but not by *this* change's. Worth tightening if ad-hoc releases become common.
