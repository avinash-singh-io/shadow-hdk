"""OpenSandbox as an isolation backend (D50) — consumed, not built.

Chosen from the survey: self-hosts with Docker on a laptop and with gVisor, Kata or Firecracker on
a cluster; a Python SDK; speaks MCP; Apache-2; CNCF-listed. What this file does is translate the
`Box` seam into that SDK and nothing more.

**It needs a server.** `present()` says so, and says how, when the connection is not configured —
never installs, never assumes (D41). Its live proof skips everywhere the server is not.

The SDK is imported inside the methods that use it, so a deployment that never opens a box never
pays for the import, and one without the extra installed gets a sentence rather than an
`ImportError` at module load.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.environment.backends import MOUNT, Box
from shadow_hdk.kernel.observations import Completed, Failed, Observation
from shadow_hdk.runtime.environment import Mode

DOMAIN = "OPENSANDBOX_DOMAIN"
API_KEY = "OPENSANDBOX_API_KEY"
IMAGE = "OPENSANDBOX_IMAGE"


class OpenSandboxBox:
    def __init__(self, sandbox: Any) -> None:
        self._sandbox = sandbox

    async def run(self, argv: list[str], *, timeout_s: float, output_limit: int) -> Observation:
        import shlex
        from datetime import timedelta

        from opensandbox.models.execd import RunCommandOpts

        try:
            done = await self._sandbox.commands.run(
                shlex.join(argv),
                opts=RunCommandOpts(working_directory=MOUNT, timeout=timedelta(seconds=timeout_s)),
            )
        except Exception as broken:  # noqa: BLE001 — a box is a component's world (D7)
            return Failed(f"{type(broken).__name__}: {broken}")
        logs = getattr(done, "logs", None)
        stdout = "".join(str(e.text) for e in getattr(logs, "stdout", []) or [])[:output_limit]
        stderr = "".join(str(e.text) for e in getattr(logs, "stderr", []) or [])[:output_limit]
        return Completed(
            {"exit_code": getattr(done, "exit_code", None), "stdout": stdout, "stderr": stderr}
        )

    async def read(self, path: str) -> str:
        text: str = await self._sandbox.files.read_file(f"{MOUNT}/{path}")
        return text

    async def write(self, path: str, content: str) -> int:
        await self._sandbox.files.write_file(f"{MOUNT}/{path}", content)
        return len(content.encode("utf-8"))

    async def delete(self, path: str) -> None:
        await self._sandbox.files.delete_files([f"{MOUNT}/{path}"])

    async def list(self, path: str) -> list[str]:
        entries = await self._sandbox.files.list_directory(f"{MOUNT}/{path}")
        return sorted(str(getattr(e, "name", e)) for e in entries)

    async def close(self) -> None:
        # A box that is already gone is gone; the point is that nothing is left running.
        with contextlib.suppress(Exception):
            await self._sandbox.kill()


class OpenSandboxBackend:
    name = "opensandbox"

    def __init__(
        self, *, domain: str | None, api_key: str | None, image: str = "python:3.12-slim"
    ) -> None:
        self._domain = domain
        self._api_key = api_key
        self._image = image

    @classmethod
    def from_environment(cls) -> OpenSandboxBackend:
        return cls(
            domain=os.environ.get(DOMAIN),
            api_key=os.environ.get(API_KEY),
            image=os.environ.get(IMAGE, "python:3.12-slim"),
        )

    def present(self) -> str | None:
        try:
            import opensandbox  # noqa: F401
        except ImportError:
            return "the `sandbox` extra is not installed: pip install 'shadow-hdk[sandbox]'"
        if not self._domain:
            return (
                f"no OpenSandbox server is configured: set {DOMAIN} (and {API_KEY} if it wants "
                "one) to a running server — `osb server` with Docker, or a cluster"
            )
        return None

    async def open(self, root: Path, mode: Mode) -> Box:
        from opensandbox import Sandbox
        from opensandbox.config.connection import ConnectionConfig
        from opensandbox.models.sandboxes import Host, NetworkPolicy, Volume

        # The SDK's own shapes (BUG-036): a host volume is a `Host(path=…)`, not a string, and the
        # fields are spelled as its models spell them. Found by type-checking against the
        # installed SDK — the live proof skips where there is no server, so nothing had run this.
        sandbox = await Sandbox.create(
            self._image,
            volumes=[
                Volume(
                    name="workspace",
                    host=Host(path=str(root)),
                    mountPath=MOUNT,
                    readOnly=mode == "read-only",
                )
            ],
            network_policy=NetworkPolicy(defaultAction="deny"),
            connection_config=ConnectionConfig(domain=self._domain, api_key=self._api_key),
        )
        return OpenSandboxBox(sandbox)


__all__ = ["OpenSandboxBackend", "OpenSandboxBox"]
