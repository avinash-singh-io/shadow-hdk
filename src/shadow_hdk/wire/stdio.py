"""JSON-RPC over a pipe — the shape MCP and ACP already use.

`wire.md` puts the **runtime** in the child: the host spawns it and keeps the real ports, so the
child writes its callbacks and its events up the pipe and the host answers back down it. That is the
same inversion the loopback proves, with an operating system in the middle.

**Newline-delimited JSON**, not `Content-Length` framing. MCP's stdio transport and ACP both use
newline-delimited, so a host that already speaks to one of those speaks to this without a second
framing to get wrong. The cost is that a frame may not contain a raw newline — which `json.dumps`
guarantees, since it escapes them.

**stdout is the wire, so nothing else may write to it.** A stray `print` in a component would be
read as a frame and would corrupt the session, which is why the child's own diagnostics go to
stderr and why this module never prints.
"""

from __future__ import annotations

from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import anyio

from shadow_hdk.runtime.lines import LineBuffer


@dataclass
class StdioChannel:
    """One end of a pipe pair, framed by newlines.

    **The two ends are not the same shape**, which is the one awkward fact here. The parent holds
    `process.stdout` / `process.stdin` — anyio byte *streams*, with `receive` and `send`. The child
    holds its own `sys.stdin.buffer` / `sys.stdout.buffer` — files, with `read` and `write`, and
    needing an explicit flush or nothing ever leaves. So this reads and writes through two small
    adapters rather than pretending one interface covers both.
    """

    inbound: Any
    outbound: Any
    _frames: LineBuffer = field(default_factory=LineBuffer)
    _ready: deque[bytes] = field(default_factory=deque)

    async def send(self, frame: str) -> None:
        await _write(self.outbound, frame.encode("utf-8") + b"\n")

    async def receive(self) -> str:
        # One framing, the runtime's (`LineBuffer`): the same rule the recording adapter's pipes
        # read by, so a blank line or a stray carriage return means the same on every peer.
        while not self._ready:
            chunk = await _read(self.inbound)
            if not chunk:
                # End of stream with nothing pending is the other end closing, which is how a
                # stdio peer says goodbye. With something pending it is a truncated frame, and
                # either way there is no next message.
                raise anyio.EndOfStream
            self._ready.extend(self._frames.feed(chunk))
        return self._ready.popleft().decode("utf-8")

    async def aclose(self) -> None:
        with anyio.CancelScope(shield=True):
            try:
                await _close(self.outbound)
            except (OSError, anyio.ClosedResourceError, anyio.BrokenResourceError):
                return


async def _read(stream: Any) -> bytes:
    """A chunk, from either a byte stream or an async file.

    **`readline`, never `read(n)`, on the file side.** `BufferedReader.read(n)` blocks until it has
    all n bytes or the pipe closes — so a child reading its own stdin that way answers nothing until
    its parent hangs up, which looks exactly like a hung child and took an hour to see. Piping one
    frame in from a shell hides it completely, because the shell closes the pipe immediately and the
    read returns at end-of-file.
    """
    if hasattr(stream, "receive"):
        try:
            chunk: bytes = await stream.receive()
        except anyio.EndOfStream:
            return b""
        return chunk
    line: bytes = await stream.readline()
    return line


async def _write(stream: Any, data: bytes) -> None:
    if hasattr(stream, "send"):
        await stream.send(data)
        return
    await stream.write(data)
    # Files buffer; the wire does not tolerate it. Without this the child answers nothing and the
    # host waits for a frame that is sitting in memory a few bytes away.
    await stream.flush()


async def _close(stream: Any) -> None:
    if hasattr(stream, "aclose"):
        await stream.aclose()


async def serve_stdio(threads: Any = None) -> None:
    """Be the runtime on the far end of somebody's pipe. This is what `--stdio` runs. With a
    `ThreadHost` (D67) the thread methods are served too; without one, `run`/`resume`."""
    import sys

    from shadow_hdk.wire.sides import RuntimeSide

    channel = StdioChannel(
        inbound=anyio.wrap_file(sys.stdin.buffer),
        outbound=anyio.wrap_file(sys.stdout.buffer),
    )
    runtime = RuntimeSide(channel, threads=threads)
    try:
        async with anyio.create_task_group() as group:
            await runtime.peer.serve_forever(group)
    finally:
        # The pipe closed: what it opened closes with it (D69), before the process ends and a
        # provider is left to notice on its own.
        with anyio.CancelScope(shield=True):
            await runtime.threads.close_all()
            closer = getattr(threads, "aclose", None)
            if closer is not None:
                await closer()


@asynccontextmanager
async def over_a_child_process(
    ports: Any, *, command: list[str] | None = None
) -> AsyncIterator[Any]:
    """Spawn a runtime in another process and drive it, holding the real ports here.

    The default command starts this same interpreter, so a test proves the transport rather than a
    packaging step. A deployment would name the installed console script instead.
    """
    import sys

    from shadow_hdk.wire.sides import HostSide

    argv = command or [sys.executable, "-m", "shadow_hdk.wire", "--stdio"]
    process = await anyio.open_process(argv, stdin=-1, stdout=-1, stderr=None)
    assert process.stdin is not None and process.stdout is not None
    channel = StdioChannel(inbound=process.stdout, outbound=process.stdin)
    host = HostSide(channel, ports)
    host.child_pid = process.pid
    try:
        async with anyio.create_task_group() as group:
            group.start_soon(host.peer.serve_forever, group)
            try:
                yield host
            finally:
                group.cancel_scope.cancel()
    finally:
        # Closing stdin is how a stdio peer is told to stop: its reader sees end-of-stream and
        # returns. `terminate` is the fallback for a child that does not take the hint.
        with anyio.CancelScope(shield=True):
            try:
                await process.stdin.aclose()
                with anyio.fail_after(10):
                    await process.wait()
            except (TimeoutError, OSError):
                process.terminate()


__all__ = ["StdioChannel", "over_a_child_process", "serve_stdio"]
