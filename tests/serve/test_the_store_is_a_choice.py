"""The record chooses its store (Phase 29 group 1, D79).

One url in `harness.toml` — `[store] url = "sqlite:///live.sqlite"` or `"postgresql://…"` —
fills the three things a record needs: the `Store` the registries read, the `ThreadStore` the
threads are kept in, and the checkpointer a parked run sleeps in. `[store] path` stays as the
sugar it always was. Nothing configured is memory, which lives as long as the process. A host
with its own tables hands the three in and the url is never read.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import anyio
import pytest

from shadow_hdk.adapters.basic import SqliteStore, SqliteThreads
from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    Ended,
    Floor,
    Invoke,
    Lease,
    Observed,
)
from shadow_hdk.kernel.ports import Allow, Ask, Context, Judgement
from shadow_hdk.runtime import Ports, RunOptions, resume, run
from shadow_hdk.runtime.store import InMemoryStore
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)
from shadow_hdk.runtime.threads import InMemoryThreads
from shadow_hdk.serve import ServeHost, load_settings
from shadow_hdk.serve.config import Settings
from shadow_hdk.serve.stores import Stores, stores_for

pytestmark = pytest.mark.anyio

POSTGRES = os.environ.get("SHADOW_HDK_TEST_POSTGRES_URL")
WORK = make_registration("work")
TWO = Composition((Invoke("first", WORK.id), Invoke("second", WORK.id)))


class AsksAtSecond:
    async def judge(self, _effects: Any, context: Context) -> Judgement:
        return Ask("may it?") if context.step == "second" else Allow()


async def work(_inputs: Any) -> Any:
    return Completed("done")


def _ports() -> Ports:
    return Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(WORK, work)]),),
        governance=AsksAtSecond(),
        sink=ListSink(),
        clock=FixedClock(),
    )


async def _park_then_resume_across(first: Stores, second: Stores) -> None:
    """A run parked through `first` finishes through `second`: the checkpoint is on the store the
    url names, not in either object."""
    options = RunOptions(
        lease=Lease(Ceiling(10, 60, None), Floor(0)),
        run_id="parked-across-stores",
        checkpointer=await first.checkpointer(),
    )
    parked = [e async for e in run(TWO, _ports(), options=options)]
    assert [e for e in parked if e.kind == "approval_requested"], "the run did not park"
    assert not [e for e in parked if isinstance(e, Ended)]
    await first.aclose()

    finished = [
        e
        async for e in resume(
            TWO,
            Allow(),
            _ports(),
            options=RunOptions(
                lease=options.lease,
                run_id=options.run_id,
                checkpointer=await second.checkpointer(),
            ),
        )
    ]
    done = [e for e in finished if isinstance(e, Observed) and e.step == "second"]
    assert done and done[0].observation == Completed("done"), finished
    assert "first" not in [e.step for e in finished if e.kind == "invoked"], "redone, not resumed"
    await second.aclose()


# ---------------------------------------------------------------- the file


def test_path_is_sugar_for_a_sqlite_url_and_url_is_kept(tmp_path: Path) -> None:
    (tmp_path / "harness.toml").write_text('[store]\npath = "live.sqlite"\n', encoding="utf-8")
    assert load_settings(tmp_path / "harness.toml").store == f"sqlite:///{tmp_path}/live.sqlite"
    (tmp_path / "harness.toml").write_text(
        '[store]\nurl = "postgresql://me@localhost/harness"\n', encoding="utf-8"
    )
    assert load_settings(tmp_path / "harness.toml").store == "postgresql://me@localhost/harness"
    (tmp_path / "harness.toml").write_text(
        '[store]\nurl = "sqlite:///data/live.sqlite"\n', encoding="utf-8"
    )
    # A relative sqlite path is relative to the file, like every path in it.
    assert (
        load_settings(tmp_path / "harness.toml").store == f"sqlite:///{tmp_path}/data/live.sqlite"
    )


def test_path_and_url_together_are_refused(tmp_path: Path) -> None:
    (tmp_path / "harness.toml").write_text(
        '[store]\npath = "live.sqlite"\nurl = "sqlite:///other.sqlite"\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="one of"):
        load_settings(tmp_path / "harness.toml")


def test_a_scheme_nobody_implements_is_refused_by_name() -> None:
    with pytest.raises(ValueError, match="mongodb") as refused:
        stores_for("mongodb://localhost/harness")
    assert "sqlite" in str(refused.value) and "postgresql" in str(refused.value)


def test_the_store_flag_takes_a_path_or_a_url(tmp_path: Path) -> None:
    from shadow_hdk.serve.__main__ import settings_from

    assert settings_from(["--store", str(tmp_path / "x.sqlite")]).store == (
        f"sqlite:///{tmp_path}/x.sqlite"
    )
    assert settings_from(["--store", "postgresql://a@b/c"]).store == "postgresql://a@b/c"


# ---------------------------------------------------------------- the choice


async def test_nothing_configured_is_memory_for_the_process() -> None:
    stores = stores_for(None)
    assert isinstance(stores.store, InMemoryStore)
    assert isinstance(stores.threads, InMemoryThreads)
    assert stores.url == "memory://"
    saver = await stores.checkpointer()
    assert saver is await stores.checkpointer(), "one checkpointer per stores, not per call"
    await stores.aclose()


async def test_a_sqlite_url_fills_all_three_and_a_park_outlives_the_stores(
    tmp_path: Path,
) -> None:
    url = f"sqlite:///{tmp_path}/live.sqlite"
    first = stores_for(url)
    assert isinstance(first.store, SqliteStore) and isinstance(first.threads, SqliteThreads)
    with anyio.fail_after(30):
        await _park_then_resume_across(first, stores_for(url))
    files = sorted(p.name for p in tmp_path.iterdir())
    assert files == ["live.checkpoints.sqlite", "live.sqlite", "live.threads.sqlite"], files


@pytest.mark.skipif(not POSTGRES, reason="SHADOW_HDK_TEST_POSTGRES_URL is not set")
async def test_a_postgres_url_fills_all_three_and_a_park_outlives_the_stores() -> None:
    from shadow_hdk.adapters.postgres import PostgresStore, PostgresThreads
    from tests.adapters.postgres.conftest import wiped

    assert POSTGRES is not None
    await wiped(POSTGRES)
    first = stores_for(POSTGRES)
    assert isinstance(first.store, PostgresStore) and isinstance(first.threads, PostgresThreads)
    with anyio.fail_after(60):
        await _park_then_resume_across(first, stores_for(POSTGRES))


async def test_a_postgres_url_without_the_extra_says_what_to_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    real = builtins.__import__

    def refusing(name: str, *rest: Any, **kw: Any) -> Any:
        if name.startswith("psycopg"):
            raise ImportError(name)
        return real(name, *rest, **kw)

    monkeypatch.setattr(builtins, "__import__", refusing)
    with pytest.raises(ImportError, match=r"shadow-hdk\[postgres\]"):
        stores_for("postgresql://me@localhost/harness")


# ---------------------------------------------------------------- the host


async def test_a_host_hands_its_own_three_in_and_the_url_is_not_read(tmp_path: Path) -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    store, threads, saver = InMemoryStore(), InMemoryThreads(), InMemorySaver()
    host = ServeHost(
        Settings(root=tmp_path, store="postgresql://nobody@nowhere/none"),
        store=store,
        threads=threads,
        checkpointer=saver,
    )
    assert host.store is store and host.threads is threads
    assert await host.checkpointer() is saver
    await host.aclose()


async def test_a_host_on_a_sqlite_url_opens_the_three_beside_the_file(tmp_path: Path) -> None:
    host = ServeHost(Settings(root=tmp_path, store=f"sqlite:///{tmp_path}/live.sqlite"))
    assert isinstance(host.store, SqliteStore) and isinstance(host.threads, SqliteThreads)
    saver = await host.checkpointer()
    assert type(saver).__name__ == "AsyncSqliteSaver"
    await host.aclose()
    assert (tmp_path / "live.checkpoints.sqlite").exists()


async def test_a_run_parked_in_one_wire_session_resumes_in_another(tmp_path: Path) -> None:
    """The wire's first shape (`run`/`resume`) on the host's checkpointer: a session is not the
    checkpoint's lifetime any more — a page reloaded is a new session, and its parked run is
    still there."""
    from shadow_hdk.wire import connect_to, served_over_http

    host = ServeHost(Settings(root=tmp_path, store=f"sqlite:///{tmp_path}/live.sqlite"))
    options = RunOptions(lease=Lease(Ceiling(10, 600, None), Floor(0)), run_id="across-sessions")
    with anyio.fail_after(60):
        async with served_over_http(threads=host) as address:
            async with connect_to(address, _ports()) as one:
                await one.initialize()
                await one.run(TWO, options)
                assert not [e for e in one.events if isinstance(e, Ended)], "the run parked"
            async with connect_to(address, _ports()) as two:
                await two.initialize()
                await two.resume(TWO, {"kind": "allow"}, options)
                ended = [e for e in two.events if isinstance(e, Ended)]
                assert ended and ended[-1].reason == "completed", two.events
    await host.aclose()
