"""Own a pinned native SDK daemon; expose only host-built command envelopes."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, cast

from shadow_hdk.adapters.browser.agent_assets import native_binary
from shadow_hdk.adapters.browser.gateway import stop_process
from shadow_hdk.runtime.processes import start_held


class AgentClient:
    def __init__(self, process: asyncio.subprocess.Process, directory: Path) -> None:
        self.process, self.directory = process, directory
        self.timeout_ms = 10000

    @classmethod
    async def start(cls, directory: Path, endpoint: str) -> AgentClient:
        binary = await native_binary()
        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(directory),
            "TMPDIR": str(directory),
            "AGENT_BROWSER_DAEMON": "1",
            "AGENT_BROWSER_SOCKET_DIR": str(directory),
            "AGENT_BROWSER_SESSION": "owned",
            "AGENT_BROWSER_NO_WEBMCP": "1",
            "AGENT_BROWSER_IDLE_TIMEOUT_MS": "0",
        }
        process = await start_held(
            str(binary),
            env=environment,
            cwd=directory,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        client = cls(process, directory)
        try:
            async with asyncio.timeout(10):
                while not (directory / "owned.sock").exists():
                    if process.returncode is not None:
                        raise RuntimeError(f"browser interaction SDK exited {process.returncode}")
                    await asyncio.sleep(0.02)
            await client.call("launch", cdpUrl=endpoint, webmcp=False, plugins=[])
            return client
        except BaseException:
            await client.close()
            raise

    async def call(self, action: str, **fields: Any) -> dict[str, Any]:
        reader, writer = await asyncio.open_unix_connection(
            str(self.directory / "owned.sock"), limit=8 * 1024 * 1024
        )
        try:
            writer.write(
                (
                    json.dumps(
                        {"id": "hdk", "action": action, "timeout": self.timeout_ms, **fields}
                    )
                    + "\n"
                ).encode()
            )
            await writer.drain()
            async with asyncio.timeout(self.timeout_ms / 1000):
                response = json.loads(await reader.readline())
            if response.get("success") is not True or not isinstance(response.get("data"), dict):
                raise RuntimeError(
                    str(response.get("error", "invalid browser SDK response"))[:2000]
                )
            return cast(dict[str, Any], response["data"])
        finally:
            writer.close()
            await writer.wait_closed()

    async def close(self) -> None:
        await stop_process(self.process)
