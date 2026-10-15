"""Frames out of an owned tab, so a person can watch the page the agent is working on (ENH-053).

Three things decide whether a stream is usable rather than merely present. Frames must be
acknowledged or the browser stops sending them. Only the newest matters, because a viewer that
falls behind wants the current page and not a backlog of the past. And it must stop when the scope
that owns the tab closes, or a run ends with a browser still talking to nobody.

Driven against a stand-in for the debugging session rather than a real browser: these are the frame
mechanics, and a real Chromium is exercised by the browser gate.
"""

from typing import Any

import pytest

from shadow_hdk.adapters.browser.screencast import Screencast

pytestmark = pytest.mark.anyio


class Session:
    """A stand-in for the page's debugging session: records what was sent, replays handlers."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, Any]] = []
        self.handlers: dict[str, Any] = {}
        self.detached = False

    def on(self, event: str, handler: Any) -> None:
        self.handlers[event] = handler

    async def send(self, method: str, params: Any = None) -> Any:
        self.sent.append((method, params))
        return {}

    async def detach(self) -> None:
        self.detached = True

    def deliver(self, data: str, session_id: int = 1) -> None:
        self.handlers["Page.screencastFrame"](
            {"data": data, "sessionId": session_id, "metadata": {}}
        )

    def methods(self) -> list[str]:
        return [method for method, _ in self.sent]


async def test_starting_enables_the_page_and_asks_for_frames() -> None:
    session = Session()
    cast = Screencast(session)
    await cast.start()
    assert "Page.enable" in session.methods(), session.methods()
    assert "Page.startScreencast" in session.methods(), session.methods()


async def test_every_frame_is_acknowledged_or_the_browser_stops_sending() -> None:
    """The acknowledgement *is* the backpressure: without it the stream dries up after a few."""
    session = Session()
    cast = Screencast(session)
    await cast.start()
    session.deliver("aaa", session_id=7)
    await cast.next()
    acks = [params for method, params in session.sent if method == "Page.screencastFrameAck"]
    assert acks == [{"sessionId": 7}], session.sent


async def test_only_the_newest_frame_is_kept() -> None:
    """A viewer that falls behind wants the page as it is, not a backlog of how it was."""
    session = Session()
    cast = Screencast(session)
    await cast.start()
    for frame in ("first", "second", "third"):
        session.deliver(frame)
    held = await cast.next()
    assert held is not None and held.data == "third", held
    assert cast.dropped == 2, cast.dropped


async def test_stopping_tells_the_browser_and_lets_go_of_the_session() -> None:
    session = Session()
    cast = Screencast(session)
    await cast.start()
    await cast.stop()
    assert "Page.stopScreencast" in session.methods(), session.methods()
    assert session.detached, "the debugging session must be let go of, not left attached"


async def test_a_stopped_stream_yields_nothing_more() -> None:
    """What a closing scope relies on: no frame after the stream is done."""
    session = Session()
    cast = Screencast(session)
    await cast.start()
    await cast.stop()
    session.deliver("after")
    assert await cast.next() is None


async def test_stopping_twice_is_not_an_error() -> None:
    """A scope closing while a viewer is also leaving must not raise: teardown runs from both ends
    and the second one is the ordinary case, not a fault."""
    session = Session()
    cast = Screencast(session)
    await cast.start()
    await cast.stop()
    await cast.stop()
    assert session.methods().count("Page.stopScreencast") == 1, session.methods()


async def test_a_frame_is_handed_over_once() -> None:
    """Newest-only means the slot is consumed, not merely overwritten.

    Leaving it in place would hand a viewer the same frame until a new one arrived, which looks
    like a stalled page rather than an unchanged one — and the two want different reactions.
    """
    session = Session()
    cast = Screencast(session)
    await cast.start()
    session.deliver("only")
    assert (await cast.next()) is not None
    assert (await cast.next()) is None, "the same frame must not be handed over twice"


async def test_a_stopped_stream_acknowledges_nothing_further() -> None:
    """A frame that arrived and was never taken must not be acknowledged after the stop: the
    session is gone by then, and sending to it is how teardown turns into an error."""
    session = Session()
    cast = Screencast(session)
    await cast.start()
    session.deliver("pending", session_id=3)
    await cast.stop()
    before = session.methods().count("Page.screencastFrameAck")
    assert await cast.next() is None
    assert session.methods().count("Page.screencastFrameAck") == before == 0, session.sent
