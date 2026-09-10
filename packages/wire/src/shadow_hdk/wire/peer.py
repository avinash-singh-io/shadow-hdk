"""One JSON-RPC peer, because both halves both ask and answer.

The temptation is a client class and a server class. This protocol does not have those: the host
asks `run` and answers `judge`; the runtime answers `run` and asks `judge`. A peer that could only
do one of the two would need its opposite bolted on within the hour, so there is one class and each
side registers the methods it serves.

**Re-entrancy is the whole difficulty.** While the host is waiting for its `run` to return, the
runtime is asking it to judge a step — so a peer that read one reply at a time would deadlock
immediately. The reader is therefore a task of its own, dispatching every inbound frame to either a
waiting caller or a handler, and never blocking on the other.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import anyio
from anyio.abc import TaskGroup

from shadow_hdk.wire.channel import Channel

Handler = Callable[[dict[str, Any]], Awaitable[Any]]


class RemoteError(Exception):
    """The other end refused or failed. Carries its code so a caller can tell one from the other."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = data


REFUSED = -32000
"""Application-level *no*. Distinct from a malformed message, because a refusal is an answer."""

GONE = -32003
"""The other end went away. Distinct from a refusal: nobody decided anything."""


class Peer:
    """A JSON-RPC 2.0 peer over a text channel."""

    def __init__(self, channel: Channel, *, name: str = "peer") -> None:
        self.channel = channel
        self.name = name
        self.handlers: dict[str, Handler] = {}
        self.notifiers: dict[str, Handler] = {}
        self._next_id = 0
        self._waiting: dict[str, anyio.Event] = {}
        self._replies: dict[str, dict[str, Any]] = {}
        self._group: TaskGroup | None = None

    # ---------------------------------------------------------------- wiring

    def serves(self, method: str, handler: Handler) -> None:
        self.handlers[method] = handler

    def hears(self, method: str, handler: Handler) -> None:
        """A notification — no reply is sent, and none is expected."""
        self.notifiers[method] = handler

    # ---------------------------------------------------------------- asking

    async def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self._next_id += 1
        message_id = f"{self.name}-{self._next_id}"
        waiting = anyio.Event()
        self._waiting[message_id] = waiting
        await self._write(
            {"jsonrpc": "2.0", "id": message_id, "method": method, "params": params or {}}
        )
        await waiting.wait()
        reply = self._replies.pop(message_id)
        if "error" in reply:
            error = reply["error"]
            raise RemoteError(
                error.get("code", REFUSED), error.get("message", ""), error.get("data")
            )
        return reply.get("result")

    async def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        await self._write({"jsonrpc": "2.0", "method": method, "params": params or {}})

    # ---------------------------------------------------------------- running

    async def serve_forever(self, group: TaskGroup) -> None:
        """Read frames until the channel closes, dispatching each without blocking the next."""
        self._group = group
        try:
            while True:
                frame = await self.channel.receive()
                message = json.loads(frame)
                if "method" in message:
                    # Handled in its own task: a handler that itself calls back would otherwise
                    # stop this reader, and stopping this reader is exactly the deadlock.
                    group.start_soon(self._handle, message)
                else:
                    self._answer(message)
        except (anyio.EndOfStream, anyio.ClosedResourceError):
            return
        finally:
            self._hang_up()

    def _hang_up(self) -> None:
        """Wake everyone still waiting, because nothing is coming.

        Without this a peer whose other end died mid-call waits for a reply for ever — and over a
        pipe that means a host blocked on `run` while the child it was talking to is already a
        zombie. A dead peer is a failure the caller can act on; a hang is not.
        """
        for message_id, waiting in list(self._waiting.items()):
            self._replies[message_id] = {
                "id": message_id,
                "error": {"code": GONE, "message": "the other end closed", "data": "Gone"},
            }
            waiting.set()
        self._waiting.clear()

    async def _handle(self, message: dict[str, Any]) -> None:
        method = str(message.get("method"))
        params = message.get("params") or {}
        if "id" not in message:
            listener = self.notifiers.get(method)
            if listener is not None:
                await listener(params)
            return
        handler = self.handlers.get(method)
        if handler is None:
            await self._write(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "error": {"code": -32601, "message": f"no method {method!r}"},
                }
            )
            return
        try:
            result = await handler(params)
        except Exception as failed:  # noqa: BLE001 — a handler's raising is the other end's answer
            await self._write(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "error": {
                        "code": REFUSED,
                        "message": f"{type(failed).__name__}: {failed}",
                        "data": type(failed).__name__,
                    },
                }
            )
            return
        await self._write({"jsonrpc": "2.0", "id": message["id"], "result": result})

    def _answer(self, message: dict[str, Any]) -> None:
        message_id = str(message.get("id"))
        waiting = self._waiting.pop(message_id, None)
        if waiting is None:
            return
        self._replies[message_id] = message
        waiting.set()

    async def _write(self, message: dict[str, Any]) -> None:
        """One frame out, or one error type saying the other end is gone.

        A broken pipe and a reply that never comes are the same condition to a caller, so they are
        the same exception. Leaving the transport's own error to escape would make every call site
        catch two unrelated types to handle one situation.
        """
        try:
            await self.channel.send(json.dumps(message))
        except (anyio.BrokenResourceError, anyio.ClosedResourceError) as gone:
            raise RemoteError(GONE, "the other end closed", "Gone") from gone


__all__ = ["GONE", "REFUSED", "Peer", "RemoteError"]
