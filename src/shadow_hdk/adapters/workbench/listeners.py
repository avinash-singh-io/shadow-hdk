"""Local listener inspection behind an optional engine; never infer an HTTP protocol from TCP."""

import asyncio
from typing import Protocol

from pydantic import JsonValue


class ProcessListeners(Protocol):
    async def inspect(self, pid: int) -> tuple[dict[str, JsonValue], ...]: ...


class LocalProcessListeners:
    """Supply only for locally owned process IDs. Remote environments use their own port."""

    async def inspect(self, pid: int) -> tuple[dict[str, JsonValue], ...]:
        return await asyncio.to_thread(self._inspect, pid)

    def _inspect(self, pid: int) -> tuple[dict[str, JsonValue], ...]:
        import psutil

        owner = psutil.Process(pid)
        try:
            processes = [owner, *owner.children(recursive=True)]
        except psutil.NoSuchProcess:
            return ()
        found: dict[tuple[str, int], dict[str, JsonValue]] = {}
        for process in processes:
            try:
                connections = process.net_connections(kind="tcp")
            except psutil.NoSuchProcess:
                continue
            for connection in connections:
                if connection.status == psutil.CONN_LISTEN and connection.laddr:
                    host, port = connection.laddr
                    found[host, port] = {
                        "host": host,
                        "port": port,
                        "protocol": "tcp",
                        "source": "listener",
                        "verified": True,
                    }
        return tuple(found[key] for key in sorted(found))
