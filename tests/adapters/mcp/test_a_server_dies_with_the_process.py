"""A battery's process dies with the process that started it (BUG-033, D35/D53): the MCP server
an `McpComponents` spawns is a session leader the runtime holds, so ending the harness — by
whichever door — ends it, even a server that ignores its stdin closing and its own SIGTERM.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest
from shadow_hdk.adapters.mcp import McpComponents, StdioServerParameters

from shadow_hdk.runtime.processes import held_now

STUBBORN = str(Path(__file__).with_name("stubborn_server.py"))
pytestmark = pytest.mark.anyio


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


async def test_the_server_is_a_held_session_leader_while_open_and_gone_after_close() -> None:
    components = McpComponents(
        StdioServerParameters(command=sys.executable, args=[STUBBORN]), source="stubborn"
    )
    before = held_now()
    await components.start()
    try:
        held = held_now() - before
        assert len(held) == 1, "the server's pid is held while the components are open"
        (pid,) = held
        assert os.getpgid(pid) == pid, "started as a session leader, so its group is its own"
        registrations = await components.registrations()
        assert [r.id for r in registrations] == ["hello"]
    finally:
        await components.stop()
    assert not (held_now() - before), "let go once closed"
    for _ in range(50):
        if not _alive(pid):
            break
        time.sleep(0.05)
    assert not _alive(pid), "a server that ignores EOF and SIGTERM is ended with its group"


def test_the_server_dies_when_the_host_process_is_ended_from_outside(tmp_path: Path) -> None:
    """The host — a process that opened the components — is sent SIGTERM from outside, the way a
    supervisor or a preview tool ends `serve`. The server must not outlive it."""
    host = textwrap.dedent(
        f"""
        import asyncio, sys
        from shadow_hdk.adapters.mcp import McpComponents, StdioServerParameters
        from shadow_hdk.runtime.processes import held_now

        async def main():
            c = McpComponents(StdioServerParameters(command=sys.executable, args=[{STUBBORN!r}]))
            await c.start()
            print(sorted(held_now())[-1], flush=True)
            await asyncio.sleep(60)

        asyncio.run(main())
        """
    )
    started = subprocess.Popen(
        [sys.executable, "-c", host], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        assert started.stdout is not None
        line = started.stdout.readline().strip()
        assert line.isdigit(), started.stderr.read() if started.stderr else line
        server_pid = int(line)
        assert _alive(server_pid)
        started.send_signal(signal.SIGTERM)
        started.wait(timeout=15)
        for _ in range(100):
            if not _alive(server_pid):
                break
            time.sleep(0.05)
        assert not _alive(server_pid), "the server outlived the host that was ended from outside"
    finally:
        if started.poll() is None:
            started.kill()
