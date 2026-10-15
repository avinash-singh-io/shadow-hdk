"""A person's clicks and keys into the page they are watching (ENH-053).

Sent through the page's own debugging session, which is what keeps a person inside the governed
browser: the page they type into is the page whose traffic passes the origin gateway. A virtual
desktop would have let them step outside it, which is why the pane is a screencast.

Nothing here decides *whether* a person may drive — that is the lease, held per resource scope by
the engine, and it is checked before any of this is reached.
"""

from __future__ import annotations

from typing import Any

MOUSE = "Input.dispatchMouseEvent"
KEY = "Input.dispatchKeyEvent"


class PersonInput:
    """What a person does to the page, in the protocol's words."""

    def __init__(self, session: Any) -> None:
        self._session = session

    async def click(self, x: float, y: float, *, button: str = "left") -> None:
        """A press and a release, because the protocol has no single click and a press without its
        release leaves the page holding a button down that nobody is pressing."""
        for kind in ("mousePressed", "mouseReleased"):
            await self._session.send(
                MOUSE, {"type": kind, "x": x, "y": y, "button": button, "clickCount": 1}
            )

    async def move(self, x: float, y: float) -> None:
        await self._session.send(MOUSE, {"type": "mouseMoved", "x": x, "y": y, "button": "none"})

    async def type(self, text: str) -> None:
        """Character by character, as typing rather than as a paste: a page that reacts per
        keystroke — a search box, a validated field — behaves the way it would under real hands."""
        for character in text:
            await self._session.send(KEY, {"type": "char", "text": character})

    async def key(self, name: str) -> None:
        """One named key down and up: Enter, Tab, Escape, an arrow."""
        for kind in ("keyDown", "keyUp"):
            await self._session.send(KEY, {"type": kind, "key": name})


__all__ = ["KEY", "MOUSE", "PersonInput"]
