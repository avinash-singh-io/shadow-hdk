"""The facade (D71): three lines for a product that wants defaults, every port underneath what it
always was, and one step deeper without leaving it.

    async with Harness.load("harness.toml") as h:
        async for part in h.turn("add a .gitignore and run the tests"):
            ...  # events, items and activity in order; the turn's record last

`Harness(root, mode=..., ...)` is the file without the file. `governance=`, `sink=`, `observer=`
and `agent=` hand a product's own port in for the shipped one; `.thread`, `.host`, `.approvals`,
`.modes`, `.rules`, `.store` are the objects underneath, for everything else. The facade imports
only public names of the packages it composes — an invariant walks it — so nothing a product
does through it is closed to a product that goes deeper.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shadow_hdk.kernel import Activity, Event, TurnRecord
from shadow_hdk.runtime.environment import Mode
from shadow_hdk.runtime.items import Fold, Item
from shadow_hdk.serve.config import Budget, Settings, load_settings
from shadow_hdk.serve.host import ServeHost


@dataclass(frozen=True)
class Part:
    """One thing a turn yields, in the order it happened.

    `kind` is the event's own kind for an event (`started`, `invoked`, `reasoning`, …),
    `activity` for what is happening beside the record (D63), `item` for a step folded closed
    (D46), and `turn` — last — for the turn's record.
    """

    kind: str
    event: Event | None = None
    activity: Activity | None = None
    item: Item | None = None
    turn: TurnRecord | None = None


class _Parts:
    """The observer a harness hands its thread: activity goes into the turn in flight, and on to
    a product's own observer when one was handed in."""

    def __init__(self, forward: Any = None) -> None:
        self._forward = forward
        self._queue: asyncio.Queue[Part | None] | None = None

    def attach(self, queue: asyncio.Queue[Part | None]) -> None:
        self._queue = queue

    def detach(self) -> None:
        self._queue = None

    async def on(self, event: Event) -> None:
        if self._forward is not None:
            await self._forward.on(event)

    async def on_activity(self, activity: Activity) -> None:
        if self._queue is not None:
            self._queue.put_nowait(Part(kind="activity", activity=activity))
        forward = getattr(self._forward, "on_activity", None)
        if forward is not None:
            await forward(activity)


class Harness:
    """A product's front door — in-process here, the same composition `shadow-hdk serve`
    puts behind the wire."""

    def __init__(
        self,
        root: Path | str = ".",
        *,
        mode: Mode = "workspace-write",
        provider: str | None = None,
        store: Path | str | None = None,
        modes_dir: Path | str | None = None,
        batteries: Sequence[str] = (),
        batteries_dir: Path | str | None = None,
        budget: Budget | None = None,
        registry_name: str = "tools",
        agent: Any = None,
        governance: Any = None,
        sink: Any = None,
        observer: Any = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or Settings(
            root=Path(root).resolve(),
            mode=mode,
            want=provider,
            store=Path(store) if store else None,
            modes_dir=Path(modes_dir) if modes_dir else None,
            registry_name=registry_name,
            batteries=tuple(batteries),
            batteries_dir=Path(batteries_dir) if batteries_dir else None,
            budget=budget or Budget(),
        )
        self.host = ServeHost(self.settings, agent=agent, governance=governance, sink=sink)
        self._parts = _Parts(observer)
        self._thread: Any = None
        self._open = False

    @classmethod
    def load(cls, path: Path | str, **handed: Any) -> Harness:
        """The file, and anything a product hands in beside it."""
        return cls(settings=load_settings(path), **handed)

    # ------------------------------------------------------------------ the lifetime

    async def __aenter__(self) -> Harness:
        await self.open()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def open(self) -> None:
        self._thread = await self.host.open(
            root="", mode="", want=None, name="", observer=self._parts
        )
        self._open = True

    async def close(self) -> None:
        """Close the thread and what the host holds; the thread's record stays readable."""
        if self._open:
            self._open = False
            await self._thread.close()
        await self.host.aclose()

    # ------------------------------------------------------------------ the turn

    async def turn(self, text: str) -> AsyncIterator[Part]:
        """Say something; get every part of what happens, in order, the turn's record last."""
        thread = self.thread
        queue: asyncio.Queue[Part | None] = asyncio.Queue()
        fold = Fold()

        async def pump() -> None:
            try:
                async for event in thread.turn(text):
                    queue.put_nowait(Part(kind=event.kind, event=event))
                    fold.feed(event)  # one fold, the runtime's (D46)
                    for item in fold.closed_now:
                        queue.put_nowait(Part(kind="item", item=item))
                queue.put_nowait(Part(kind="turn", turn=thread.record.turns[-1]))
            finally:
                queue.put_nowait(None)

        self._parts.attach(queue)
        pumping = asyncio.create_task(pump())
        try:
            while (part := await queue.get()) is not None:
                yield part
            await pumping
        finally:
            self._parts.detach()
            if not pumping.done():
                pumping.cancel()

    async def set_mode(self, mode: str) -> Sequence[Event]:
        return await self.thread.set_mode(mode)

    async def steer(self, text: str) -> bool:
        return bool(await self.thread.steer(text))

    async def interrupt(self) -> None:
        await self.thread.interrupt()

    # ------------------------------------------------------------------ underneath

    @property
    def thread(self) -> Any:
        """The thread underneath — its record, registry, lease; readable after close too."""
        if self._thread is None:
            raise RuntimeError("the harness is not open: `async with Harness(...) as h:`")
        return self._thread

    @property
    def approvals(self) -> Any:
        return self.host.approvals

    @property
    def modes(self) -> Any:
        return self.host.modes

    @property
    def rules(self) -> Any:
        return self.host.rules

    @property
    def store(self) -> Any:
        return self.host.store

    @property
    def problems(self) -> tuple[str, ...]:
        """What was wanted and could not be had — a battery that will not run here, a document
        that will not load — in the words that say what would fix it."""
        return tuple(self.host.battery_problems.values())


__all__ = ["Harness", "Part"]
