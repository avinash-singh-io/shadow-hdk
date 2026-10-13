"""An owned local proxy process; its SDK dependencies live outside the host's interpreter."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from shadow_hdk.adapters.browser.policy import OriginPolicy
from shadow_hdk.runtime import current_run
from shadow_hdk.runtime.processes import end_the_group, let_go, start_held, stop_or_kill

MITMPROXY_VERSION = "12.2.3"


async def stop_process(process: asyncio.subprocess.Process) -> None:
    if os.name == "posix":
        try:
            await stop_or_kill(process, grace_s=5)
        finally:
            end_the_group(process)
    else:
        try:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), 5)
                except TimeoutError:
                    process.kill()
                    await process.wait()
        finally:
            let_go(process)


async def _sdk_python() -> str:
    import uv

    context = current_run()
    if context is not None:
        await context.activity(
            "install",
            f"Preparing isolated mitmproxy {MITMPROXY_VERSION}; first use may download it.",
        )
    environment = {k: v for k, v in os.environ.items() if not k.startswith(("UV_", "PYTHON"))}
    process = await start_held(
        uv.find_uv_bin(),
        "tool",
        "run",
        "--no-config",
        "--no-env-file",
        "--isolated",
        "--no-python-downloads",
        "--python",
        sys.executable,
        "--from",
        f"mitmproxy=={MITMPROXY_VERSION}",
        "python",
        "-I",
        "-c",
        "import sys; print(sys.executable)",
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        output, errors = await asyncio.wait_for(process.communicate(), 180)
        if process.returncode:
            raise RuntimeError("browser proxy SDK installation failed: " + errors.decode()[-8000:])
        return output.decode().strip()
    finally:
        await stop_process(process)


class Gateway:
    def __init__(self, process: asyncio.subprocess.Process, port: int, spki: str) -> None:
        self.process, self.port, self.spki = process, port, spki
        self._errors = bytearray()
        self._draining = asyncio.create_task(self._drain())

    async def _drain(self) -> None:
        assert self.process.stderr is not None
        while chunk := await self.process.stderr.read(4096):
            self._errors.extend(chunk)
            del self._errors[:-32768]

    @classmethod
    async def start(
        cls,
        directory: Path,
        policy: OriginPolicy,
        *,
        sdk_python: str | None = None,
        upstream_ca: Path | None = None,
    ) -> Gateway:
        python = sdk_python or await _sdk_python()
        source = Path(__file__).parent
        (directory / "policy.py").write_bytes((source / "policy.py").read_bytes())
        script = directory / "guard.py"
        script.write_bytes((source / "mitm_addon.py.template").read_bytes())
        environment = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
        environment["SHADOW_HDK_BROWSER_POLICY"] = json.dumps(asdict(policy))
        args = [
            python,
            "-I",
            "-c",
            "from mitmproxy.tools.main import mitmdump; mitmdump()",
            "--quiet",
            "--listen-host",
            "127.0.0.1",
            "--listen-port",
            "0",
            "--set",
            f"confdir={directory}",
            "--set",
            "connection_strategy=lazy",
            "--set",
            "upstream_cert=false",
            "-s",
            str(script),
        ]
        if upstream_ca is not None:
            args.extend(("--set", f"ssl_verify_upstream_trusted_ca={upstream_ca}"))
        process = await start_held(
            *args,
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert process.stdout is not None
        gateway = cls(process, 0, "")
        try:
            raw = await asyncio.wait_for(process.stdout.readline(), 30)
            ready = json.loads(raw)
            gateway.port, gateway.spki = int(ready["port"]), str(ready["spki"])
            return gateway
        except Exception as error:
            await gateway.close()
            raise RuntimeError(
                "browser origin gateway failed to start: "
                + gateway._errors.decode(errors="replace")[-8000:]
            ) from error
        except BaseException:
            await gateway.close()
            raise

    async def close(self) -> None:
        try:
            await stop_process(self.process)
        finally:
            await self._draining
