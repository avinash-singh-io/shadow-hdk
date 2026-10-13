"""Pinned native SDK assets, optional and installed only on first browser use."""

from __future__ import annotations

import asyncio
import hashlib
import os
import platform
import sys
from pathlib import Path

from shadow_hdk.adapters.browser.gateway import stop_process
from shadow_hdk.runtime import current_run
from shadow_hdk.runtime.processes import start_held

VERSION = "0.39.0"
URL = f"https://registry.npmjs.org/agent-browser/-/agent-browser-{VERSION}.tgz"
INTEGRITY = (
    "VtImIqCpHC/xJFw91IAcLlBJzebCBjynOwIKnx4kuCeI2JicpPBMKykdjQ1wmnj2dL2voNKRv8iK+Joe6aHFtw=="
)
HASHES = {
    "darwin-arm64": "636fc9aa269e3819b539998aa5b87e1c3953556c19eeb9685053743283464faa",
    "darwin-x64": "c080b1c2c4f03c2690778d72f30a0f8807cea1a5946b71e0ab6d71498f2d573e",
    "linux-arm64": "54eedbcaedcbd8b49f840098ea85dda653af0a036e28609b526ece068de6c0ab",
    "linux-x64": "d258593db4899577748a4b2a671a315f76f07a4553ba7fbbeaa95f0d16a4aaa8",
    "linux-musl-arm64": "e63f7aa47bff381469e8c34c2f3c2fe317a607b1ce1a0a712a9896a8de07ac43",
    "linux-musl-x64": "6adeb7e2466f0d9ea4ef562222e221bfdd067f5545d7b052dc64fb13ba250f48",
}


def _asset() -> str:
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "amd64": "x64"}.get(
        platform.machine().lower(), ""
    )
    system = "darwin" if sys.platform == "darwin" else "linux" if sys.platform == "linux" else ""
    if system == "linux" and platform.libc_ver()[0] != "glibc":
        system = "linux-musl"
    key = f"{system}-{arch}"
    if key not in HASHES:
        raise RuntimeError("the browser pack supports Linux and macOS on arm64/x64")
    return key


async def native_binary() -> Path:
    asset = _asset()
    cache = (
        Path(
            os.environ.get(
                "SHADOW_HDK_AGENT_BROWSER_CACHE",
                str(Path.home() / ".cache/shadow-hdk/agent-browser"),
            )
        )
        / VERSION
    )
    binary = cache / f"agent-browser-{asset}"
    if binary.is_file() and hashlib.sha256(binary.read_bytes()).hexdigest() == HASHES[asset]:
        return binary
    context = current_run()
    if context is not None:
        await context.activity(
            "install", f"Preparing agent-browser {VERSION}; first use downloads its native SDK."
        )
    process = await start_held(
        sys.executable,
        "-I",
        str(Path(__file__).with_name("download_asset.py")),
        URL,
        INTEGRITY,
        f"package/bin/agent-browser-{asset}",
        str(binary),
        HASHES[asset],
        stdin=asyncio.subprocess.DEVNULL,
    )
    try:
        _, error = await asyncio.wait_for(process.communicate(), 180)
        if process.returncode:
            raise RuntimeError("agent-browser SDK installation failed: " + error.decode()[-2000:])
    finally:
        await stop_process(process)
    return binary
