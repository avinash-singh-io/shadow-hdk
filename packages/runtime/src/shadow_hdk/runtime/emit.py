"""The only channel out of the runtime, and the one place `seq` and `at` are decided.

Two consumers, one order (D6): `run()` yields from the stream queue, and — if a host bound an
observer — a second queue is drained by a task of its own. `emit()` puts and returns; it never
awaits the observer, so a slow or broken observer cannot slow or fail a step (D11).
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable
from typing import Any, Final

from shadow_hdk.kernel.events import Event, RunId
from shadow_hdk.kernel.ports import ClockPort, ObserverPort

_CLOSED: Final = object()

MakeEvent = Callable[..., Event]
"""A partially-built event: the emitter supplies ``run_id``, ``seq`` and ``at``."""


class Emitter:
    def __init__(self, run_id: RunId, clock: ClockPort, observer: ObserverPort | None) -> None:
        self._run_id = run_id
        self._clock = clock
        self._observer = observer
        self._seq = 0
        self._stream: asyncio.Queue[Any] = asyncio.Queue()
        self._to_observer: asyncio.Queue[Any] = asyncio.Queue()
        self._pump: asyncio.Task[None] | None = None
        self.observer_failures = 0

    async def emit(self, make: MakeEvent) -> Event:
        """Stamp an event and put it on both queues. Returns the event it built."""
        event = make(run_id=self._run_id, seq=self._seq, at=self._clock.now())
        self._seq += 1
        self._stream.put_nowait(event)
        if self._observer is not None:
            if self._pump is None:
                self._pump = asyncio.create_task(self._drain_to_observer())
            self._to_observer.put_nowait(event)
        return event

    async def _drain_to_observer(self) -> None:
        assert self._observer is not None
        while True:
            item = await self._to_observer.get()
            if item is _CLOSED:
                return
            try:
                await self._observer.on(item)
            except Exception:  # noqa: BLE001 — an observer never fails a run (D6)
                self.observer_failures += 1

    async def stream(self) -> AsyncIterator[Event]:
        """Every event, in order, until `close()`."""
        while True:
            item = await self._stream.get()
            if item is _CLOSED:
                return
            yield item

    def close(self, *, wait: bool = True) -> None:
        """End the stream. `wait=False` abandons an observer that is not coming back."""
        self._stream.put_nowait(_CLOSED)
        if self._observer is None:
            return
        if wait:
            self._to_observer.put_nowait(_CLOSED)
        elif self._pump is not None:
            self._pump.cancel()

    async def drained(self) -> None:
        """Wait for the observer to have seen everything. Only meaningful after `close()`."""
        if self._pump is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await self._pump
