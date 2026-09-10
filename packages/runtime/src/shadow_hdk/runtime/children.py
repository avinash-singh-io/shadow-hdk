"""Spawn, send, release — the three operations `09` §6 names, over parked runs (D16).

A held child is **a parked run, not a resident object**. `spawn` starts it and lets it go until it
parks or ends; `send` is a `resume` with the message as the answer; `release` cancels it and settles
its lease. `09` §6 says the runtime owns nothing durable and is disposable by design, and a resident
child with an inbox is durable runtime state under another name — it would need a lifetime, its own
supervision, and an answer for what happens when the host restarts. A checkpoint answers all three.

What this registry holds is the little a resume needs and a checkpoint cannot supply: the
composition, because `resume` takes the plan back in (`09` §6); the checkpointer the child parked
with; and the child's own `Cancellation`, which is what makes *branch* granularity mean anything —
releasing one child says nothing about its siblings.

**Holding is not a reservation.** A parked run settles what it did not spend back to its parent on
the way out, so what a parent gives up by holding a child is the steps that child actually took.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import JsonValue

from shadow_hdk.kernel.composition import Composition
from shadow_hdk.kernel.events import Ended, Event
from shadow_hdk.kernel.leases import Ceiling
from shadow_hdk.runtime.cancel import Cancellation

if TYPE_CHECKING:
    from shadow_hdk.runtime.bindings import RunContext

RELEASED = "released"
"""What a child is sent when it is let go. Never read — see `Children.release`."""


@dataclass(frozen=True)
class HeldChild:
    """What a parent keeps about a held child. Ephemeral, like all the runtime owns."""

    handle: str
    run_id: str
    composition: Composition
    ceiling: Ceiling
    checkpointer: Any
    cancellation: Cancellation


class Children:
    """A run's children, and the three things a parent may do with one."""

    def __init__(self, context: RunContext) -> None:
        self._context = context
        self._held: dict[str, HeldChild] = {}

    @property
    def held(self) -> tuple[str, ...]:
        """The handles of children parked and waiting. In the order they were spawned."""
        return tuple(self._held)

    def __contains__(self, handle: str) -> bool:
        return handle in self._held

    async def spawn(
        self, composition: Composition, ceiling: Ceiling, *, checkpointer: Any = None
    ) -> tuple[str, list[Event]]:
        """Start a child and let it run. If it parks rather than ending, this parent holds it.

        The checkpointer defaults to one of ours, which makes a held child live exactly as long as
        this process. A host that wants a child to outlive a restart passes its own — the same
        checkpointer it would hand `run()`, and the same one Phase 6 proved on a file.
        """
        from langgraph.checkpoint.memory import InMemorySaver

        from shadow_hdk.runtime.loop import run

        saver = checkpointer if checkpointer is not None else InMemorySaver()
        # Its own handle, not the parent's: releasing one child must say nothing about its siblings.
        cancellation = Cancellation()
        handle = self._context.ports.clock.new_id()
        options = self._context.spawn_options(
            ceiling, run_id=handle, checkpointer=saver, cancellation=cancellation
        )
        events = [event async for event in run(composition, self._context.ports, options=options)]
        if not any(isinstance(event, Ended) for event in events):
            self._held[handle] = HeldChild(
                handle=handle,
                run_id=handle,
                composition=composition,
                ceiling=ceiling,
                checkpointer=saver,
                cancellation=cancellation,
            )
            await self._context.announce_held(handle, _steps_in(events))
        return handle, events

    async def send(self, handle: str, message: JsonValue) -> list[Event]:
        """Wake a held child with a message. It answers where it slept, not from the beginning."""
        from shadow_hdk.runtime.loop import resume

        child = self._held[handle]
        events = [
            event
            async for event in resume(
                child.composition, message, self._context.ports, options=self._options_for(child)
            )
        ]
        if any(isinstance(event, Ended) for event in events):
            del self._held[handle]
        return events

    async def release(self, handle: str) -> list[Event]:
        """Let a child go. It is cancelled, its lease settles, and the parent forgets it.

        The cancellation is set *before* the resume so the child stops at its first step boundary
        rather than doing one more piece of work on its way out. The child is woken only so that it
        can end: LangGraph re-runs the parked node from the top, the cancellation check is the first
        thing there, and the run ends `cancelled` without ever consuming what it was sent.

        Which is why the value below is a word rather than `None`. It is never read — but
        `Command(resume=None)` raises inside LangGraph 1.2 (`cannot access local variable
        'resume_is_map'`), so a run released that way would end `failed` and say something about a
        variable instead of saying it was let go.
        """
        from shadow_hdk.runtime.loop import resume

        child = self._held.pop(handle)
        child.cancellation.cancel(f"released by {self._context.run_id}")
        return [
            event
            async for event in resume(
                child.composition, RELEASED, self._context.ports, options=self._options_for(child)
            )
        ]

    def _options_for(self, child: HeldChild) -> Any:
        return self._context.spawn_options(
            child.ceiling,
            run_id=child.run_id,
            checkpointer=child.checkpointer,
            cancellation=child.cancellation,
        )


def _steps_in(events: list[Event]) -> int:
    return sum(1 for event in events if event.kind == "invoked")


__all__ = ["Children", "HeldChild"]
