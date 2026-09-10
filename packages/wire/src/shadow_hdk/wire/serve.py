"""A runtime you connect to rather than launch.

Phase 5 found the gap this closes: the RecordingServer can only be *connected to*, never launched,
because a server holding a live `RunContext` cannot be started fresh by somebody else. A child on
another machine therefore had no way in. This is that way in.

**The direction is the awkward part.** The ports invert — the runtime calls the host — but an HTTP
server cannot call its client. So the two directions take different paths, the same split MCP's
streamable HTTP uses:

    host  ──POST /rpc──►  runtime     its own calls, and its replies to the runtime's callbacks
    host  ◄──SSE /rpc───  runtime     the runtime's callbacks, and the run's events

`Channel` already hides both from the protocol, so `RuntimeSide` and `HostSide` are untouched — the
wire grew a transport rather than a second implementation.

**A session per connection.** Each client gets its own id, its own channel and its own
`RuntimeSide`. Without that a second connection would join the first's session and answer its
callbacks, which is a confused deputy with a tidy error message.
"""

from __future__ import annotations

import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

SESSION_HEADER = "x-shadow-hdk-session"


@dataclass
class QueueChannel:
    """One end of a link whose two directions are different transports."""

    outbound: MemoryObjectSendStream[str]
    inbound: MemoryObjectReceiveStream[str]

    async def send(self, frame: str) -> None:
        await self.outbound.send(frame)

    async def receive(self) -> str:
        return await self.inbound.receive()

    async def aclose(self) -> None:
        with anyio.CancelScope(shield=True):
            await self.outbound.aclose()


@dataclass
class Session:
    """One connected host. Its own id, its own queues, its own runtime."""

    id: str
    to_host: MemoryObjectSendStream[str]
    from_host: MemoryObjectSendStream[str]
    runtime: Any = None
    events: MemoryObjectReceiveStream[str] | None = field(default=None)


def build_app(clock: Any = None, *, token: str | None = None) -> Any:
    """A Starlette app serving one runtime per connected host.

    Imported lazily and kept in one place, so the wire package's core has no web dependency: a host
    embedding the runtime in-process, or driving it over a pipe, installs nothing extra.
    """
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse, Response, StreamingResponse
    from starlette.routing import Route

    from shadow_hdk.wire.sides import RuntimeSide

    sessions: dict[str, Session] = {}

    def unauthorised(request: Request) -> Response | None:
        """A session was issued to whoever asked (BUG-006). `wire.md` listed a run token under
        *rules already fixed* and it was never built; until it is, a deployment that binds
        anything but loopback must set a token, and this is what checks it."""
        if token is None:
            return None
        offered = request.headers.get("authorization", "")
        if offered != f"Bearer {token}":
            return JSONResponse({"error": "unauthorised"}, status_code=401)
        return None

    async def open_session(request: Request) -> Response:
        """The SSE stream. Opening it *is* opening a session — the id comes back in a header, and
        every frame the runtime sends travels down this response."""
        if refused := unauthorised(request):
            return refused
        session_id = secrets.token_urlsafe(16)
        to_host_send, to_host_receive = anyio.create_memory_object_stream[str](float("inf"))
        from_host_send, from_host_receive = anyio.create_memory_object_stream[str](float("inf"))
        session = Session(id=session_id, to_host=to_host_send, from_host=from_host_send)
        # The runtime reads what the host POSTs and writes into the SSE stream.
        channel = QueueChannel(outbound=to_host_send, inbound=from_host_receive)
        session.runtime = RuntimeSide(channel, clock=clock)
        sessions[session_id] = session

        async def frames() -> AsyncIterator[bytes]:
            async with anyio.create_task_group() as group:
                group.start_soon(session.runtime.peer.serve_forever, group)
                try:
                    async for frame in to_host_receive:
                        # SSE framing: `data:` line, blank line. The payload is one JSON message,
                        # and `json.dumps` escapes newlines, so a frame never spans two events.
                        yield f"data: {frame}\n\n".encode()
                finally:
                    sessions.pop(session_id, None)
                    group.cancel_scope.cancel()

        return StreamingResponse(
            frames(),
            media_type="text/event-stream",
            headers={SESSION_HEADER: session_id, "cache-control": "no-store"},
        )

    async def post_frame(request: Request) -> Response:
        if refused := unauthorised(request):
            return refused
        session_id = request.headers.get(SESSION_HEADER)
        if not session_id:
            # 400 rather than 404: the request is malformed, not aimed at something missing.
            return JSONResponse({"error": f"missing {SESSION_HEADER}"}, status_code=400)
        session = sessions.get(session_id)
        if session is None:
            return JSONResponse({"error": "no such session"}, status_code=404)
        await session.from_host.send(json.dumps(await request.json()))
        # Accepted, not answered. The reply travels down the SSE stream like everything else, so
        # there is exactly one path for runtime-to-host traffic rather than two to keep in step.
        return Response(status_code=202)

    return Starlette(
        routes=[
            Route("/rpc", open_session, methods=["GET"]),
            Route("/rpc", post_frame, methods=["POST"]),
        ]
    )


LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


@asynccontextmanager
async def served_over_http(
    *, host: str = "127.0.0.1", clock: Any = None, token: str | None = None
) -> AsyncIterator[str]:
    """Listen on an ephemeral localhost port, and yield the address to connect to.

    **Localhost and port 0.** A test that bound a routable interface would be a service; a test
    that picked a fixed port would fight the next one.

    **Anything but loopback needs a token.** `wire.md` lists a run token under *rules already
    fixed*; it is not built, so until it is, this refuses to become a service that anyone on the
    network can open a session on (BUG-006). A token here is a stop-gap a deployment sets, not the
    per-run credential the design asks for.
    """
    import uvicorn

    if host not in LOOPBACK and token is None:
        raise ValueError(
            f"{host!r} is not loopback and no token was given: the run token wire.md describes is "
            "not built, so serving beyond localhost would issue a session to anyone who asked"
        )
    config = uvicorn.Config(
        build_app(clock=clock, token=token), host=host, port=0, log_level="warning"
    )
    server = uvicorn.Server(config)
    async with anyio.create_task_group() as group:
        group.start_soon(server.serve)
        with anyio.fail_after(30):
            while not server.started:
                await anyio.sleep(0.01)
        port = server.servers[0].sockets[0].getsockname()[1]
        try:
            yield f"http://{host}:{port}"
        finally:
            server.should_exit = True
            group.cancel_scope.cancel()


@asynccontextmanager
async def connect_to(address: str, ports: Any) -> AsyncIterator[Any]:
    """Drive a runtime that is already listening, holding the real ports here."""
    import httpx

    from shadow_hdk.wire.sides import HostSide

    to_runtime_send, to_runtime_receive = anyio.create_memory_object_stream[str](float("inf"))
    from_runtime_send, from_runtime_receive = anyio.create_memory_object_stream[str](float("inf"))
    channel = QueueChannel(outbound=to_runtime_send, inbound=from_runtime_receive)
    host = HostSide(channel, ports)

    async with (
        httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client,
        anyio.create_task_group() as group,
    ):
        opened = anyio.Event()

        async def read_stream() -> None:
            async with client.stream("GET", f"{address}/rpc") as response:
                host.session_id = response.headers.get(SESSION_HEADER)
                opened.set()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        await from_runtime_send.send(line[len("data: ") :])

        async def write_frames() -> None:
            async for frame in to_runtime_receive:
                await client.post(
                    f"{address}/rpc",
                    headers={
                        SESSION_HEADER: host.session_id or "",
                        "content-type": "application/json",
                    },
                    content=frame,
                )

        group.start_soon(read_stream)
        with anyio.fail_after(30):
            await opened.wait()
        group.start_soon(write_frames)
        group.start_soon(host.peer.serve_forever, group)
        try:
            yield host
        finally:
            group.cancel_scope.cancel()


__all__ = ["SESSION_HEADER", "QueueChannel", "build_app", "connect_to", "served_over_http"]
