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


def error_data(failed: BaseException) -> dict[str, Any]:
    """`error.data` for a handler's refusal (D92): a `kind` from the published vocabulary and
    the detail a client acts on. The classes are named here rather than imported, so the wire's
    core reaches into no package above it."""
    name = type(failed).__name__
    if name == "ThreadHeld":
        return {
            "kind": "thread_held",
            "thread_id": getattr(failed, "thread_id", ""),
            "holder": getattr(failed, "holder", ""),
        }
    if name == "TurnRunning":
        return {
            "kind": "turn_running",
            "thread_id": getattr(failed, "thread_id", ""),
            "turn_id": getattr(failed, "turn_id", ""),
        }
    if name == "IncompatibleCapabilities":
        compatibility = getattr(failed, "compatibility", None)
        mismatches = getattr(compatibility, "mismatches", ())
        return {
            "kind": "capability_mismatch",
            "mismatches": [
                {
                    "subject": gap.subject,
                    "axis": gap.axis,
                    "required": gap.required,
                    "available": gap.available,
                    "evidence": {
                        "axis": gap.evidence.axis,
                        "kind": gap.evidence.kind,
                        "source": gap.evidence.source,
                        "at": gap.evidence.at,
                    },
                }
                for gap in mismatches
            ],
        }
    if name == "PlanNotAdmitted":
        refusal = getattr(failed, "refusal", None)
        return {
            "kind": "plan_refused",
            "amendment": bool(getattr(failed, "amendment", False)),
            "mismatches": [
                {"axis": m.axis, "step": m.step, "required": m.required, "found": m.found}
                for m in getattr(refusal, "mismatches", ())
            ],
        }
    if name == "VersionMismatch":
        return {"kind": "version_mismatch"}
    if isinstance(failed, KeyError | FileNotFoundError):
        return {"kind": "not_found"}
    if isinstance(failed, ValueError | TypeError):
        return {"kind": "invalid"}
    return {"kind": "refused"}


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

    def __init__(
        self, channel: Channel, *, name: str = "peer", timeout: float | None = None
    ) -> None:
        self.timeout = timeout
        """How long to wait for an answer, or `None` for as long as it takes. The runtime sets it
        for its callbacks; the host does not, because a host waiting for a run to finish is
        waiting for exactly as long as the run's own lease allows."""
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
        """Ask, and give up if the answer never comes.

        The lease bounds a **run**, and a run waiting on a peer is not running — so a host that
        hangs in `judge` would otherwise hold a step open past its own wall ceiling forever. The
        bound belongs to the wire, and the message names the method so the record says which end
        stopped answering (BUG-006).
        """
        self._next_id += 1
        message_id = f"{self.name}-{self._next_id}"
        waiting = anyio.Event()
        self._waiting[message_id] = waiting
        await self._write(
            {"jsonrpc": "2.0", "id": message_id, "method": method, "params": params or {}}
        )
        try:
            if self.timeout is None:
                await waiting.wait()
            else:
                with anyio.fail_after(self.timeout):
                    await waiting.wait()
        except TimeoutError:
            self._waiting.pop(message_id, None)
            self._replies.pop(message_id, None)
            raise TimeoutError(
                f"the other side did not answer {method!r} within {self.timeout}s"
            ) from None
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
                "error": {
                    "code": GONE,
                    "message": "the other end closed",
                    "data": {"kind": "gone"},
                },
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
                    "error": {
                        "code": -32601,
                        "message": f"no method {method!r}",
                        "data": {"kind": "unknown_method"},
                    },
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
                        "data": error_data(failed),
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
            raise RemoteError(GONE, "the other end closed", {"kind": "gone"}) from gone


__all__ = ["GONE", "REFUSED", "Peer", "RemoteError"]
