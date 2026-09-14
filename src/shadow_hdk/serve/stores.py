"""The record chooses its store (D79): one url, three things.

A record needs a `Store` (the registries' rows: modes, rules, skills, switches), a `ThreadStore`
(the threads and their turns) and a checkpointer (where a run sleeps when it parks). Every
product that hosts a runtime configures these as one choice — LangGraph Server's checkpointer,
ADK's session service, Mastra's storage — and so does this: `[store] url` names sqlite or
Postgres and `stores_for` answers all three; nothing named is memory, which lives as long as the
process. A host with its own tables hands its three to `ServeHost` and this module is not read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shadow_hdk.kernel import ThreadStore
from shadow_hdk.kernel.ports import Store

MEMORY = "memory://"
SCHEMES = ("memory", "sqlite", "postgresql", "postgres")


@dataclass
class Stores:
    """The three, from one url. The checkpointer is opened on first ask — its connection is an
    async one, and a host is built before any loop runs — and closed by `aclose`."""

    url: str
    store: Store
    threads: ThreadStore
    _open: Any = field(repr=False)
    _checkpointer: Any = field(default=None, repr=False)
    _closer: Any = field(default=None, repr=False)

    async def checkpointer(self) -> Any:
        if self._checkpointer is None:
            self._checkpointer, self._closer = await self._open()
        return self._checkpointer

    async def aclose(self) -> None:
        """Close what was opened: the checkpointer's connection, then the stores' pools."""
        if self._closer is not None:
            await self._closer.close()
        self._checkpointer, self._closer = None, None
        for each in (self.store, self.threads):
            close = getattr(each, "aclose", None)
            if close is not None:
                await close()


@dataclass(frozen=True)
class _Backend:
    """How one scheme makes each of the three — called only for the ones not handed in, so a
    host with its own tables never has a file made for the part it brought."""

    store: Any
    threads: Any
    checkpointer: Any


def stores_for(
    url: str | None,
    *,
    store: Any = None,
    threads: Any = None,
    checkpointer: Any = None,
    run_store: Any = None,
) -> Stores:
    """The three the url names, or the ones handed in — each handed-in part replaces the one the
    url would have made; `run_store` (D93) is a product's own `RunStore`, and the checkpointer is
    the library's saver over it. A scheme nobody implements is refused with the ones that are."""
    chosen = url or MEMORY
    scheme = chosen.split("://", 1)[0] if "://" in chosen else ""
    if scheme == "memory":
        backend = _memory()
    elif scheme == "sqlite":
        backend = _sqlite(chosen)
    elif scheme in ("postgresql", "postgres"):
        backend = _postgres(chosen)
    else:
        raise ValueError(
            f"no store answers {scheme or chosen!r}: a store url is one of "
            + ", ".join(f"{s}://" for s in SCHEMES)
        )

    async def opened() -> tuple[Any, Any]:
        if checkpointer is not None:
            return checkpointer, None  # the host that made it closes it
        if run_store is not None:
            from shadow_hdk.runtime.checkpoints import saver_over

            return saver_over(run_store), None  # the product's own tables, behind our port
        saver, closer = await backend.checkpointer()
        return saver, closer

    return Stores(
        chosen,
        store if store is not None else backend.store(),
        threads if threads is not None else backend.threads(),
        opened,
    )


def _memory() -> _Backend:
    from shadow_hdk.runtime.store import InMemoryStore
    from shadow_hdk.runtime.threads import InMemoryThreads

    async def opened() -> tuple[Any, Any]:
        from langgraph.checkpoint.memory import InMemorySaver

        return InMemorySaver(), None

    return _Backend(InMemoryStore, InMemoryThreads, opened)


def _sqlite(url: str) -> _Backend:
    """Three files beside each other: `live.sqlite`, `live.threads.sqlite`,
    `live.checkpoints.sqlite` — the first two are what `[store] path` always made."""
    from shadow_hdk.adapters.basic import SqliteStore, SqliteThreads

    path = Path(url[len("sqlite:///") :])
    path.parent.mkdir(parents=True, exist_ok=True)

    async def opened() -> tuple[Any, Any]:
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        connection = await aiosqlite.connect(str(path.with_suffix(".checkpoints.sqlite")))
        saver = AsyncSqliteSaver(connection)
        await saver.setup()
        return saver, connection

    return _Backend(
        lambda: SqliteStore(path),
        lambda: SqliteThreads(path.with_suffix(".threads.sqlite")),
        opened,
    )


def _postgres(url: str) -> _Backend:
    from shadow_hdk.adapters.postgres import PostgresStore, PostgresThreads, postgres_checkpointer

    async def opened() -> tuple[Any, Any]:
        return await postgres_checkpointer(url)

    return _Backend(lambda: PostgresStore(url), lambda: PostgresThreads(url), opened)


__all__ = ["MEMORY", "SCHEMES", "Stores", "stores_for"]
