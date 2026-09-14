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

import asyncio
import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from shadow_hdk.runtime.streams import (
    AlreadyAttached,
    CursorExpired,
    StreamAttachment,
    StreamExpired,
    StreamSession,
)

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


KEPT_FRAMES = 5000
"""How many frames a session keeps for a reconnect (D94): what a turn in flight produces while
nobody listens, several times over. Older frames fall off the front; a reconnect from before
them starts from what is kept."""

GRACE_SECONDS = 60.0
"""How long a session outlives its stream (D94): a page on a train reconnects within it and
misses nothing; past it the session's threads are closed and the id is gone."""


@dataclass
class Session:
    """One host's session (D94): its runtime runs in a task of its own, its frames go into an
    outbox with ids, and a stream attaches to the outbox — or detaches and reattaches within
    the grace, replaying what it missed. The stream is a view; the session is the thing."""

    id: str
    to_host: MemoryObjectSendStream[str]
    from_host: MemoryObjectSendStream[str]
    stream: StreamSession[str]
    runtime: Any = None
    events: MemoryObjectReceiveStream[str] | None = field(default=None)
    opened_at: str = ""
    ended: bool = False


class Sessions:
    """What the app knows of its sessions (D86): the admin view a runtime answers with."""

    def __init__(self) -> None:
        self.by_id: dict[str, Session] = {}

    async def sessions(self) -> list[dict[str, Any]]:
        return [
            {
                "id": session.id,
                "opened_at": session.opened_at,
                "attached": session.stream.attached,
                "threads": sorted(session.runtime.threads.threads)
                if session.runtime is not None
                else [],
            }
            for session in self.by_id.values()
        ]

    async def take_over(self, thread_id: str, by: Any) -> None:
        """A thread open in another session of this process (D94): closed there when that
        session's stream is gone — a page reloaded resumes its thread; refused, naming the
        session, when its stream is attached — two pages cannot drive one thread."""
        from shadow_hdk.runtime.threads import ThreadHeld

        for session in list(self.by_id.values()):
            methods = session.runtime.threads if session.runtime is not None else None
            if methods is None or methods is by or thread_id not in methods.threads:
                continue
            if session.stream.attached:
                raise ThreadHeld(thread_id, f"session {session.id}")
            await methods.close_one(thread_id)

    def open_threads(self) -> int:
        return sum(len(s["threads"]) for s in self._sync_sessions())

    def _sync_sessions(self) -> list[dict[str, Any]]:
        return [
            {"threads": list(s.runtime.threads.threads) if s.runtime is not None else []}
            for s in self.by_id.values()
        ]


def build_app(
    clock: Any = None,
    *,
    token: str | None = None,
    threads: Any = None,
    page: Path | None = None,
    grace_seconds: float = GRACE_SECONDS,
) -> Any:
    """A Starlette app serving one runtime per connected host.

    Imported lazily and kept in one place, so the wire package's core has no web dependency: a host
    embedding the runtime in-process, or driving it over a pipe, installs nothing extra.

    `threads` is a `ThreadHost` (D67), shared by every session this app serves — one process, one
    composition. `page` is a file served at `/`, so a browser client needs no second server.
    """
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
    from starlette.routing import Route

    from shadow_hdk import __version__
    from shadow_hdk.wire.sides import RuntimeSide
    from shadow_hdk.wire.threads import host_checkpointer

    known = Sessions()
    sessions: dict[str, Session] = known.by_id

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

    running: dict[str, asyncio.Task[None]] = {}

    async def end_session(session: Session) -> None:
        """The session's threads go with it (D69), its runtime stops, its id is forgotten."""
        if session.ended:
            return
        session.ended = True
        sessions.pop(session.id, None)
        session.stream.expire()
        with anyio.CancelScope(shield=True):
            await session.runtime.threads.close_all()
        task = running.pop(session.id, None)
        if task is not None:
            task.cancel()

    async def serve_session(session: Session, to_host_receive: Any) -> None:
        """The session's runtime and its outbox, in a task of their own — not the stream's, so
        the session outlives the stream (D94)."""
        async with anyio.create_task_group() as group:
            group.start_soon(session.runtime.peer.serve_forever, group)
            async for frame in to_host_receive:
                session.stream.keep(frame)

    def stream_of(session: Session, last_seen: int | None) -> AsyncIterator[bytes]:
        attached: StreamAttachment[str] = session.stream.attach(after=last_seen)

        async def frames() -> AsyncIterator[bytes]:
            # The stream opens with a comment frame, as SSE has it: a Node front (a dev proxy,
            # a product's backend) holds the response's headers — the session id among them —
            # until the first body byte, and the first frame was a reply to a call the client
            # cannot make without the id. A client ignores a line that is not `data:`.
            yield b": session open\n\n"
            # **Replay, then live** (D94): what the outbox holds after the last frame this
            # stream saw, then everything from now on — each frame once, in order, by its id.
            try:
                while True:
                    frame = await attached.receive()
                    if frame.heartbeat:
                        yield b": heartbeat\n\n"
                    elif frame.id is not None and frame.value is not None:
                        yield _sse(frame.id, frame.value)
            finally:
                attached.detach()

        return frames()

    async def open_session(request: Request) -> Response:
        """The SSE stream. Opening it *is* opening a session — the id comes back in a header, and
        every frame the runtime sends travels down this response. With the session header it is
        a **reattach** (D94): the stream a page lost, picked up where `Last-Event-ID` left it."""
        if refused := unauthorised(request):
            return refused
        wanted = request.headers.get(SESSION_HEADER)
        if wanted:
            session = sessions.get(wanted)
            if session is None or session.ended:
                return JSONResponse({"error": "no such session"}, status_code=404)
            last = request.headers.get("last-event-id")
            last_seen = int(last) if last and last.isdigit() else None
            try:
                stream = stream_of(session, last_seen)
            except AlreadyAttached:
                return JSONResponse({"error": "the session has a stream attached"}, status_code=409)
            except CursorExpired as stale:
                return JSONResponse(
                    {
                        "error": "the replay cursor expired",
                        "after": stale.after,
                        "oldest": stale.oldest,
                        "latest": stale.latest,
                    },
                    status_code=410,
                )
            except StreamExpired:
                return JSONResponse({"error": "no such session"}, status_code=404)
            return StreamingResponse(
                stream,
                media_type="text/event-stream",
                headers={SESSION_HEADER: session.id, "cache-control": "no-store"},
            )
        session_id = secrets.token_urlsafe(16)
        to_host_send, to_host_receive = anyio.create_memory_object_stream[str](float("inf"))
        from_host_send, from_host_receive = anyio.create_memory_object_stream[str](float("inf"))
        session_stream = StreamSession[str](capacity=KEPT_FRAMES, grace_seconds=grace_seconds)
        session = Session(
            id=session_id,
            to_host=to_host_send,
            from_host=from_host_send,
            stream=session_stream,
            opened_at=_stamp(clock),
        )
        session_stream.on_expire = lambda: end_session(session)
        # The runtime reads what the host POSTs and writes into the outbox.
        channel = QueueChannel(outbound=to_host_send, inbound=from_host_receive)
        session.runtime = RuntimeSide(
            channel,
            clock=clock,
            threads=threads,
            checkpointer=await host_checkpointer(threads),
            admin=known,
        )
        sessions[session_id] = session
        running[session_id] = asyncio.create_task(serve_session(session, to_host_receive))
        return StreamingResponse(
            stream_of(session, None),
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
        if session is None or session.ended:
            return JSONResponse({"error": "no such session"}, status_code=404)
        await session.from_host.send(json.dumps(await request.json()))
        # Accepted, not answered. The reply travels down the SSE stream like everything else, so
        # there is exactly one path for runtime-to-host traffic rather than two to keep in step.
        return Response(status_code=202)

    async def healthz(_request: Request) -> Response:
        """A load balancer's question, not a person's (D86): answered without a bearer, saying
        nothing a stranger could use — the kit's version and two counts."""
        return JSONResponse(
            {
                "ok": True,
                "version": __version__,
                "sessions": len(sessions),
                "threads": known.open_threads(),
            }
        )

    async def the_page(_request: Request) -> Response:
        if page is None:
            return JSONResponse({"error": "no page is served here; talk to /rpc"}, status_code=404)
        return HTMLResponse(page.read_text(encoding="utf-8"))

    async def end_all() -> None:
        """Every session ended — the process is stopping: its threads closed, nothing held."""
        for session in list(sessions.values()):
            await end_session(session)

    app = Starlette(
        routes=[
            Route("/", the_page),
            Route("/healthz", healthz, methods=["GET"]),
            Route("/rpc", open_session, methods=["GET"]),
            Route("/rpc", post_frame, methods=["POST"]),
        ]
    )
    app.state.end_sessions = end_all
    return app


def _sse(fid: int, frame: str) -> bytes:
    """SSE framing: an `id:` line, a `data:` line, a blank line. The payload is one JSON message,
    and `json.dumps` escapes newlines, so a frame never spans two events."""
    return f"id: {fid}\ndata: {frame}\n\n".encode()


def _stamp(clock: Any) -> str:
    if clock is not None:
        return str(clock.now())
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


@asynccontextmanager
async def served_over_http(
    *,
    host: str = "127.0.0.1",
    clock: Any = None,
    token: str | None = None,
    threads: Any = None,
    page: Path | None = None,
    grace_seconds: float = GRACE_SECONDS,
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
    app = build_app(
        clock=clock, token=token, threads=threads, page=page, grace_seconds=grace_seconds
    )
    config = uvicorn.Config(app, host=host, port=0, log_level="warning")
    server = uvicorn.Server(config)
    finished = anyio.Event()

    async def serve_until_it_is_done() -> None:
        try:
            await server.serve()
        finally:
            finished.set()

    async with anyio.create_task_group() as group:
        group.start_soon(serve_until_it_is_done)
        with anyio.fail_after(30):
            while not server.started:
                await anyio.sleep(0.01)
        port = server.servers[0].sockets[0].getsockname()[1]
        try:
            yield f"http://{host}:{port}"
        finally:
            # **Ask it to stop, then wait for it to have stopped, then insist.** Cancelling
            # uvicorn mid-`serve` leaves its own tasks to be torn down by force, and one of them
            # surfaces the cancellation as an unretrieved exception — harmless, and the first thing
            # anyone driving the wire sees. `should_exit` lets it close its sockets and finish its
            # own shutdown first.
            #
            # **Waited on `serve` returning, not on a flag.** The first version of this watched
            # `server.started`, which uvicorn sets once and never clears, so the loop was a five
            # second sleep that happened to outlast the shutdown. It passed for the wrong reason
            # and charged every caller five seconds to leave. The cancel scope stays as the
            # backstop for a shutdown that never finishes.
            server.should_exit = True
            with anyio.move_on_after(5):
                await finished.wait()
            # The sessions that outlived their streams (D94) end with the server.
            with anyio.CancelScope(shield=True):
                await app.state.end_sessions()
            group.cancel_scope.cancel()


async def serve_http_forever(
    threads: Any, port: int = 8765, token: str | None = None, page: Path | None = None
) -> None:
    """Listen on loopback at `port` until stopped — what `shadow-hdk serve --http` runs."""
    import uvicorn

    app = build_app(None, token=token, threads=threads, page=page)
    # A page holds an SSE stream open, and uvicorn's graceful shutdown waits for open connections
    # for ever by default — which kept this process, the provider's and the batteries' alive
    # after a SIGTERM until the tab was closed (measured, twice). Two seconds, then it ends.
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="warning", timeout_graceful_shutdown=2
    )
    server = uvicorn.Server(config)
    try:
        await server.serve()
    finally:
        # The sessions that outlived their streams (D94) end with the server, then what the host
        # holds for the process — a battery's server (D70).
        await app.state.end_sessions()
        closer = getattr(threads, "aclose", None)
        if closer is not None:
            await closer()


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
