"""Watching the stream: to the screen, or through a function of your own.

An observer never fails a run — the runtime swallows and counts what these raise — so neither of
these tries to be careful. Being careful is the host's job, in its own observer.
"""

from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable
from typing import TextIO

from shadow_hdk.kernel.contracts import dump
from shadow_hdk.kernel.events import Event
from shadow_hdk.kernel.ports import ObserverPort


class StdoutObserver(ObserverPort):
    """One JSON line per event — the whole run, in the order it happened."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream if stream is not None else sys.stdout

    async def on(self, event: Event) -> None:
        self._stream.write(dump(event, Event) + "\n")
        self._stream.flush()


class CallbackObserver(ObserverPort):
    def __init__(self, on_event: Callable[[Event], Awaitable[None] | None]) -> None:
        self._on = on_event

    async def on(self, event: Event) -> None:
        result = self._on(event)
        if result is not None:
            await result
