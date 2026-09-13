"""One pool per store object, opened on first use — inside the running loop, which is where
psycopg's async pool wants to be opened — and closed by `aclose`."""

from __future__ import annotations

from typing import Any

INSTALL = "the `postgres` extra is not installed: pip install 'shadow-hdk[postgres]'"


def require_psycopg() -> None:
    """Raise, naming the extra, before anything is half-built."""
    try:
        import psycopg  # noqa: F401
        import psycopg_pool  # noqa: F401
    except ImportError as missing:
        raise ImportError(INSTALL) from missing


class Pooled:
    """The connection pool a Postgres adapter draws from."""

    def __init__(self, url: str, *, schema: str) -> None:
        require_psycopg()
        self._url = url
        self._schema = schema
        self._pool: Any = None
        self._ready = False

    async def pool(self) -> Any:
        from psycopg_pool import AsyncConnectionPool

        if self._pool is None:
            self._pool = AsyncConnectionPool(self._url, open=False, min_size=1, max_size=4)
            await self._pool.open()
        if not self._ready:
            async with self._pool.connection() as connection:
                await connection.execute(self._schema)
            self._ready = True
        return self._pool

    async def aclose(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            self._ready = False


__all__ = ["INSTALL", "Pooled", "require_psycopg"]
