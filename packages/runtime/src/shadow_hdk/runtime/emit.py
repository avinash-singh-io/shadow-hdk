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

from shadow_hdk.kernel.activity import Activity
from shadow_hdk.kernel.events import Event, RunId
from shadow_hdk.kernel.ports import ActivityObserver, ClockPort, ObserverPort

_CLOSED: Final = object()

MakeEvent = Callable[..., Event]
"""A partially-built event: the emitter supplies ``run_id``, ``seq`` and ``at``."""

OBSERVER_BACKLOG_MAX = 4096
"""How far the observer may fall behind before events are dropped (TD-005).

**Bounded because it grows with traffic**, unlike the plan cache's sibling argument: measured, an
observer that never returned handled one event while 49,999 queued behind it.

**Dropped, never blocked.** D11 puts the observer off the critical path, so a bound that made the
run wait would turn a wedged exporter into a wedged runtime — the failure would move from the thing
that is broken to the thing that is not. This is the shape TD-002 already chose for the MQTT
witness, for the same reason.

**The oldest goes.** An observer this far behind is more use with the recent events than the
ancient ones, and dropping the newest would freeze its record at the moment the queue filled.
Four thousand is minutes of a busy run, so a healthy exporter never sees it.
"""


class Emitter:
    def __init__(
        self,
        run_id: RunId,
        clock: ClockPort,
        observer: ObserverPort | None,
        *,
        activity_to: Callable[[Activity], None] | None = None,
    ) -> None:
        self._run_id = run_id
        self._clock = clock
        self._observer = observer
        self._activity_to = activity_to
        """Where a child's activity goes: its parent's emitter, which forwards up to the root's
        observer — the same path its events take (D63)."""
        self._seq = 0
        self._stream: asyncio.Queue[Any] = asyncio.Queue()
        """**Unbounded, and it must be.** Filled and drained by the same task — a step emits, the
        `async for` in `run` yields — so a bound would deadlock the run against itself the moment a
        step emitted more events than the bound allowed. Nothing here grows with traffic that the
        caller is not already consuming."""
        self._to_observer: asyncio.Queue[Any] = asyncio.Queue(maxsize=OBSERVER_BACKLOG_MAX)
        self._pump: asyncio.Task[None] | None = None
        self.observer_failures = 0
        self.observer_dropped = 0
        """Events the observer never saw because it had fallen `OBSERVER_BACKLOG_MAX` behind. A
        record with a hole in it and no count reads as complete."""

    @property
    def observer_backlog(self) -> int:
        """How far behind the observer is right now — nothing when there is no observer."""
        return self._to_observer.qsize()

    @property
    def seq(self) -> int:
        """The next sequence number this emitter will stamp."""
        return self._seq

    def restore(self, seq: int) -> None:
        """Continue a run's numbering rather than starting it again (D33). Two events sharing a
        `(run_id, seq)` are two different events on one record, which no reader can order."""
        self._seq = max(self._seq, seq)

    async def emit(self, make: MakeEvent) -> Event:
        """Stamp an event and put it on both queues. Returns the event it built."""
        event = make(run_id=self._run_id, seq=self._seq, at=self._clock.now())
        self._seq += 1
        self._stream.put_nowait(event)
        self._offer(event)
        return event

    async def forward(self, event: Event) -> None:
        """Put an event that was stamped elsewhere — a child's — onto this stream unchanged."""
        self._stream.put_nowait(event)
        self._offer(event)

    def activity(self, kind: str, text: str, *, step: str) -> Activity:
        """What is happening, beside the record (D63): to the observer if there is one, up to the
        parent if this is a child, dropped if nobody listens. Never on the stream `run` yields."""
        item = Activity(run_id=self._run_id, step=step, kind=kind, text=text, at=self._clock.now())
        self.forward_activity(item)
        return item

    def forward_activity(self, item: Activity) -> None:
        if self._observer is not None:
            self._offer(item)
        elif self._activity_to is not None:
            self._activity_to(item)

    def _offer(self, event: Event | Activity) -> None:
        """Hand the observer an event, dropping the oldest rather than waiting (TD-005)."""
        if self._observer is None:
            return
        if self._pump is None:
            self._pump = asyncio.create_task(self._drain_to_observer())
        if self._to_observer.full():
            with contextlib.suppress(asyncio.QueueEmpty):
                self._to_observer.get_nowait()
                self.observer_dropped += 1
        self._to_observer.put_nowait(event)

    async def _drain_to_observer(self) -> None:
        assert self._observer is not None
        while True:
            item = await self._to_observer.get()
            if item is _CLOSED:
                return
            try:
                if isinstance(item, Activity):
                    if isinstance(self._observer, ActivityObserver):
                        await self._observer.on_activity(item)
                else:
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
            # The sentinel must land even when the observer is `OBSERVER_BACKLOG_MAX` behind — a
            # flood of activity filled the queue and `put_nowait` raised `QueueFull` at close,
            # which the activity tests found. The oldest goes, as it would for any item.
            if self._to_observer.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    self._to_observer.get_nowait()
                    self.observer_dropped += 1
            self._to_observer.put_nowait(_CLOSED)
        elif self._pump is not None:
            self._pump.cancel()

    async def drained(self) -> None:
        """Wait for the observer to have seen everything. Only meaningful after `close()`."""
        if self._pump is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await self._pump
