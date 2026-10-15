"""Frames out of an owned tab, so a person can watch the page the agent is working on (ENH-053).

**A screencast of the owned target, not a virtual desktop**, and the deciding reason is governance
rather than weight: a whole desktop would let a person step outside the governed browser and
discard the origin boundary ADR 0001 spent three amendments earning, where a screencast-driven page
still passes through the gateway. It also costs no new dependency, arrives per tab — which is the
identity the engine already keeps — and works on both platforms the gate runs, where a virtual
display stack is Linux-only.

Two limits of the mechanism, designed around rather than discovered. Frames must be acknowledged or
the browser stops sending them, so the acknowledgement *is* the backpressure. And the stream reaches
only the window's real device scale factor, so a page under viewport emulation arrives blurred —
which is a thing to tell a person, not a thing to fix here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FORMAT = "jpeg"
QUALITY = 60
"""Enough to read a page by, and small enough that a slow viewer falls behind by frames rather than
by seconds. Only the newest is ever held, so quality costs bytes and never latency."""


@dataclass(frozen=True)
class Frame:
    """One rendering of the page, as the browser encoded it."""

    data: str
    """The image, base64 as the protocol sends it — handed on unchanged, never re-encoded here."""
    metadata: dict[str, Any]
    """The browser's own account of what this frame shows: offset, scale, device dimensions."""


class Screencast:
    """The newest frame from one owned tab, acknowledged as it arrives.

    Deliberately not a queue. A viewer that falls behind wants the page as it is, not a backlog of
    how it was, so there is one slot and a count of what was passed over — a product that wants to
    say *you are seeing the current page* has the number to say it with.
    """

    def __init__(self, session: Any) -> None:
        self._session = session
        self._latest: Frame | None = None
        self._pending_ack: int | None = None
        self.dropped = 0
        """Frames superseded before anyone looked. Not a failure: it is what newest-only means."""
        self._running = False

    async def start(self) -> None:
        self._session.on("Page.screencastFrame", self._arrived)
        await self._session.send("Page.enable")
        await self._session.send(
            "Page.startScreencast", {"format": FORMAT, "quality": QUALITY, "everyNthFrame": 1}
        )
        self._running = True

    def _arrived(self, frame: dict[str, Any]) -> None:
        """The browser's handler: synchronous, so it keeps the frame and defers the acknowledgement.

        Acknowledging from here would mean awaiting inside a callback the protocol client calls
        synchronously. The frame is held with the session id it must be acknowledged against, and
        `next` sends it — which is also the moment a viewer has actually taken the frame, so the
        browser is told to continue exactly when somebody is ready for more.
        """
        if not self._running:
            return
        if self._latest is not None:
            self.dropped += 1
        self._latest = Frame(
            data=str(frame.get("data", "")), metadata=dict(frame.get("metadata", {}))
        )
        session_id = frame.get("sessionId")
        if session_id is not None:
            self._pending_ack = int(session_id)

    async def next(self) -> Frame | None:
        """The newest frame, or `None` when there is nothing new or the stream has stopped.

        No guard on whether the stream is running: `stop` empties the slot and the pending
        acknowledgement, so a stopped stream has nothing to hand over by construction. A guard here
        as well could not be made to fail, and unprovable code is the kind that is believed.
        """
        frame, self._latest = self._latest, None
        if self._pending_ack is not None:
            ack, self._pending_ack = self._pending_ack, None
            await self._session.send("Page.screencastFrameAck", {"sessionId": ack})
        return frame

    async def stop(self) -> None:
        """Tell the browser to stop and let go of the session.

        Idempotent, because teardown runs from both ends — a viewer leaving and the scope that owns
        the tab closing — and the second one is the ordinary case rather than a fault.
        """
        if not self._running:
            return
        self._running = False
        self._latest = None
        self._pending_ack = None
        await self._session.send("Page.stopScreencast")
        await self._session.detach()


__all__ = ["FORMAT", "QUALITY", "Frame", "Screencast"]
