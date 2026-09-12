"""`shadow-hdk serve` — the composition the studio used to carry, as the harness's own, behind
the wire over HTTP/SSE or stdio (Phase 26 group 4).

`ServeHost` implements the wire's `ThreadHost` from the shipped adapters: the local environment
with a mode, the shipped skills, `ask_person`, the mode registry (files and a store), the act
rules, the authenticated socket offer, and a provider — by default whichever CLI is signed in here,
or one handed in. What a host in any language reaches is the same object the coder and the studio
compose.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import anyio
import pytest

from shadow_hdk.adapters.environment import local_sandbox
from shadow_hdk.kernel import Turn
from shadow_hdk.kernel.ports import AgentSession
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.environment import Mode
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel
from shadow_hdk.serve import ServeHost, load_settings
from shadow_hdk.serve.config import Settings

pytestmark = pytest.mark.anyio

ENFORCEABLE: Mode = "workspace-write" if local_sandbox() is not None else "full"
"""The composition is real: a confined mode is refused where no OS sandbox can enforce it (D49),
and CI's Linux runner has none — so these open the mode this machine can prove, which is not
what they are about."""


class ScriptedProvider:
    """An `AgentPort` that speaks without a CLI: what the live studio has is a real one."""

    def __init__(self) -> None:
        self.opened = 0

    async def open(self, *, tools: Any = (), workspace: Any = None, behaviour: Any = None) -> Any:
        self.opened += 1

        class _Session:
            async def turn(self, prompt: str) -> Turn:
                return Turn(text="scripted: " + prompt)

            async def close(self) -> None:
                pass

            async def stream(self, prompt: str) -> AsyncIterator[Any]:  # pragma: no cover
                raise NotImplementedError
                yield

        return cast(AgentSession, _Session())


def _ports() -> Ports:
    """A client's own ports — unused here: the thread's ports are the server's (D67)."""
    from shadow_hdk.adapters.basic import AllowAll

    return Ports(
        model=ScriptedModel([]),
        components=(),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )


async def test_serve_host_opens_a_thread_on_the_shipped_composition(tmp_path: Path) -> None:
    provider = ScriptedProvider()
    host = ServeHost(Settings(root=tmp_path, mode=ENFORCEABLE), agent=provider)

    thread = await host.open(
        root=str(tmp_path), mode=ENFORCEABLE, want=None, name="tools", observer=None
    )
    try:
        events = [e async for e in thread.turn("hello")]
    finally:
        await thread.close()

    assert provider.opened == 1
    assert thread.record.turns[-1].text == "scripted: hello"
    assert [e.kind for e in events][0] == "started"
    assert host.approvals is not None and host.modes is not None and host.rules is not None
    assert [m.id for m in await host.modes.all()] == ["read-only", "workspace-write", "full"]


async def test_the_studio_composition_is_the_harnesss_now() -> None:
    """The coder and the studio import the composition; nothing of it stays in the examples."""
    import examples.coder.thread as coder

    assert coder.a_thread.__module__.startswith("shadow_hdk.serve"), coder.a_thread.__module__
    assert not (Path("examples/coder/workshop.py")).exists(), "the workshop moved into the harness"


async def test_over_http_a_client_starts_a_thread_and_turns_it(tmp_path: Path) -> None:
    from shadow_hdk.wire import connect_to, served_over_http

    provider = ScriptedProvider()
    host = ServeHost(Settings(root=tmp_path, mode=ENFORCEABLE), agent=provider)
    heard: list[str] = []
    with anyio.fail_after(60):
        async with served_over_http(threads=host) as address:
            async with connect_to(address, _ports()) as client:
                await client.initialize()

                async def keep(params: dict[str, Any]) -> None:
                    heard.append(params["item"]["step"])

                client.peer.hears("item", keep)
                started = await client.peer.call(
                    "thread/start", {"root": str(tmp_path), "mode": ENFORCEABLE}
                )
                done = await client.peer.call(
                    "turn/start", {"thread_id": started["thread_id"], "text": "over http"}
                )
    assert done["turn"]["text"] == "scripted: over http"
    assert "turn-1" in heard


def test_settings_read_the_minimal_harness_toml(tmp_path: Path) -> None:
    (tmp_path / "harness.toml").write_text(
        '[environment]\nroot = "work"\nmode = "read-only"\n[provider]\nwant = "codex"\n'
        '[store]\npath = "live.sqlite"\n[modes]\ndir = "modes"\n[registry]\nname = "workspace"\n',
        encoding="utf-8",
    )
    settings = load_settings(tmp_path / "harness.toml")
    assert settings.root == (tmp_path / "work").resolve()
    assert settings.mode == "read-only" and settings.want == "codex"
    assert settings.store == (tmp_path / "live.sqlite").resolve()
    assert settings.modes_dir == (tmp_path / "modes").resolve()
    assert settings.registry_name == "workspace"


def test_settings_refuse_an_unknown_key(tmp_path: Path) -> None:
    (tmp_path / "harness.toml").write_text(
        '[environment]\nroot = "."\nmoode = "full"\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="moode"):
        load_settings(tmp_path / "harness.toml")


def test_serve_over_stdio_answers_initialize_and_names_a_missing_provider(tmp_path: Path) -> None:
    """The child process answers the handshake with nothing signed in; a thread on a provider
    that is not here is refused with the reason — the plumbing, without a live CLI."""
    (tmp_path / "harness.toml").write_text(
        '[environment]\nroot = "."\nmode = "read-only"\n', encoding="utf-8"
    )
    frames = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocol_version": "1"}},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "thread/start",
            "params": {"root": str(tmp_path), "mode": "read-only", "provider": "no-such-provider"},
        },
    ]
    finished = subprocess.run(
        [
            sys.executable,
            "-m",
            "shadow_hdk.serve",
            "serve",
            str(tmp_path / "harness.toml"),
            "--stdio",
        ],
        input="".join(json.dumps(f) + "\n" for f in frames),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    lines = [json.loads(line) for line in finished.stdout.splitlines() if line.strip()]
    by_id = {line.get("id"): line for line in lines if "id" in line}
    assert by_id[1]["result"]["protocol_version"] == "1", finished.stderr[-500:]
    assert "error" in by_id[2] and "no-such-provider" in json.dumps(by_id[2]["error"])


def test_a_sigterm_ends_serve_http_even_with_a_page_holding_the_stream(tmp_path: Path) -> None:
    """uvicorn's graceful shutdown waits for open connections for ever by default, and a page
    holds an SSE stream open — measured: `serve --http` outlived its SIGTERM until the tab was
    closed, and with it the provider's process and the batteries' (the studio learned this once
    already, on its own server). Two seconds of grace, then the process ends."""
    import os
    import signal
    import socket
    import time

    import httpx

    (tmp_path / "harness.toml").write_text(
        '[environment]\nroot = "."\nmode = "full"\n', encoding="utf-8"
    )
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    child = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "shadow_hdk.serve",
            "serve",
            str(tmp_path / "harness.toml"),
            "--http",
            f"--port={port}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"},
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                httpx.get(f"http://127.0.0.1:{port}/", timeout=1)
                break
            except httpx.HTTPError:
                time.sleep(0.1)
        else:
            raise AssertionError("serve did not come up")
        with httpx.Client(timeout=None) as web, web.stream("GET", f"http://127.0.0.1:{port}/rpc"):
            child.send_signal(signal.SIGTERM)
            started = time.monotonic()
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                raise AssertionError(
                    "serve outlived SIGTERM while a page held the stream"
                ) from None
            assert time.monotonic() - started < 8
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
