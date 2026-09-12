"""The context a component sees when the runtime running it is on the other side of a wire.

**The problem this solves, found by a test rather than by reading.** When the ports invert, a
component *executes on the host* — that is the whole point of `components.invoke`. But
`current_run()` is a contextvar set by the runtime's own loop, in the runtime's own task, so a
component that crossed found `None` there and every idiom built on it broke at once: `09`'s
principle 3 is *act through components; record through the sink*, and the way a component records is
`current_run().propose(...)`.

So the host binds one of these for the duration of the call. What it can answer locally it answers
locally — `ports` is the host's own bundle, and the model and sink genuinely live there. What
belongs to the run it **crosses back for**, because there is exactly one meter and exactly one event
stream and neither is the host's.

`propose` is the interesting case. It could have written straight to the host's sink, one crossing
cheaper. It does not: `RunContext.propose` emits `Proposed` *and* calls the sink, and an event
emitted host-side would land on a stream nobody reads. Crossing back keeps one record with one
author.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from pydantic import JsonValue

from shadow_hdk.kernel.components import Registration
from shadow_hdk.kernel.composition import Composition
from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import Event
from shadow_hdk.kernel.leases import Ceiling, Lease
from shadow_hdk.kernel.observations import Proposal
from shadow_hdk.runtime import Ports, Resumed, RunContext, RunOptions
from shadow_hdk.wire.peer import Peer
from shadow_hdk.wire.protocol import (
    CONTEXT_ACTIVITY,
    CONTEXT_FLOOR_MET,
    CONTEXT_IS_HELD,
    CONTEXT_KEEP,
    CONTEXT_PROPOSE,
    CONTEXT_REASONING,
    CONTEXT_RELEASE,
    CONTEXT_REMAINING,
    CONTEXT_REQUEST_APPROVAL,
    CONTEXT_REQUEST_INPUT,
    CONTEXT_RESUMED,
    CONTEXT_SEND,
    CONTEXT_SPAWN,
    CONTEXT_VISIBLE,
)


def _as_answer(raw: Any) -> Any:
    """A judgement arrives as JSON and is loaded back; anything else is what the host said."""
    from shadow_hdk.kernel.contracts import load
    from shadow_hdk.kernel.ports import Judgement

    if isinstance(raw, dict) and raw.get("kind") in ("allow", "ask", "refuse"):
        return load(json.dumps(raw), Judgement)
    return raw


class WireRunContext(RunContext):
    """`current_run()` for a component the host is running on the runtime's behalf."""

    def __init__(self, peer: Peer, ports: Ports, run_id: str, step: str) -> None:
        # Deliberately not calling `RunContext.__init__`: it wants a session, an emitter and a
        # registry, and all three belong to the run — which is on the other side. Everything this
        # class can honestly answer is overridden below, and everything it cannot says so.
        self._peer = peer
        self._ports = ports
        self._run_id = run_id
        self._step = step

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def ports(self) -> Ports:
        """The **host's** ports. The model and the sink already live here; reaching back for them
        would cross the wire twice to arrive where we started."""
        return self._ports

    def now(self) -> str:
        return self._ports.clock.now()

    async def propose(self, proposal: Proposal) -> None:
        await self._peer.call(
            CONTEXT_PROPOSE,
            {"proposal": json.loads(dump(proposal, Proposal))},
        )

    async def reasoning(self, text: str, *, step: str | None = None) -> None:
        """Crosses back for the same reason `propose` does: there is one record with one author,
        and a thought emitted host-side would land on a stream nobody reads."""
        if text:
            await self._peer.call(CONTEXT_REASONING, {"text": text, "step": step or self._step})

    def remaining(self) -> Lease:
        raise WireOnlyAsync(
            "remaining() is synchronous in-process and cannot be over a wire; "
            "await context.remaining_now() instead"
        )

    async def remaining_now(self) -> Lease:
        """What the run has left, asked of the runtime that owns the meter."""
        answered = await self._peer.call(CONTEXT_REMAINING, {})
        return load(json.dumps(answered), Lease)

    # ------------------------------------------------------------------ not across a wire, yet

    def _across(self, what: str) -> Any:
        raise NotAcrossTheWire(
            f"{what} is not available to a component running over the wire — "
            "it belongs to the run, which is in another process"
        )

    async def visible(self) -> Sequence[Registration]:
        """The registry's visible registrations, asked of the runtime that holds the registry
        (D51). A catalogue built on the host from this is built from what the run says is
        visible — governed — and not from what the host happens to have."""
        answered = await self._peer.call(CONTEXT_VISIBLE, {})
        return [load(json.dumps(r), Registration) for r in answered["registrations"]]

    async def floor_met_now(self) -> bool:
        answered = await self._peer.call(CONTEXT_FLOOR_MET, {})
        return bool(answered["floor_met"])

    async def request_approval(
        self,
        question: str,
        *,
        step: str | None = None,
        about: tuple[str | None, JsonValue | None] = (None, None),
    ) -> Any:
        """A live question crosses and waits: the host's `Approvals` handle is on the runtime's
        side, where the record is (D58). The judgement comes back as JSON. What the question is
        about crosses with it (BUG-026)."""
        component, inputs = about
        answered = await self._peer.call(
            CONTEXT_REQUEST_APPROVAL,
            {
                "question": question,
                "step": step or self._step,
                "component": component,
                "inputs": inputs,
            },
        )
        return _as_answer(answered.get("answer"))

    async def request_input(self, question: str, *, step: str | None = None) -> str | None:
        """The agent's own question crosses and waits on the runtime side's handle (D65)."""
        answered = await self._peer.call(
            CONTEXT_REQUEST_INPUT, {"question": question, "step": step or self._step}
        )
        answer = answered.get("answer") if isinstance(answered, dict) else None
        return str(answer) if answer is not None else None

    async def activity(self, kind: str, text: str, *, step: str | None = None) -> None:
        """What is happening crosses as a notification (D63): fire-and-forget, because activity is
        never required for correctness, and an answer would make it wait on the wire."""
        if not text:
            return
        await self._peer.notify(
            CONTEXT_ACTIVITY, {"kind": kind, "text": text, "step": step or self._step}
        )

    async def keep(self, value: JsonValue, *, step: str | None = None) -> None:
        """Crosses for the same reason `reasoned` does (D57): the interrupt that will carry this
        is raised runtime-side, where the record and the checkpointer are."""
        await self._peer.call(CONTEXT_KEEP, {"value": value, "step": step or self._step})

    async def resumed(self, *, step: str | None = None) -> Resumed | None:
        answered = await self._peer.call(CONTEXT_RESUMED, {"step": step or self._step})
        if not answered.get("resumed"):
            return None
        return Resumed(answer=_as_answer(answered.get("answer")), kept=answered.get("kept"))

    def floor_met(self) -> bool:
        raise WireOnlyAsync(
            "floor_met() is synchronous in-process and cannot be over a wire; "
            "await context.floor_met_now() instead"
        )

    async def spawn_options_now(self, ceiling: Ceiling, **overrides: Any) -> RunOptions:
        """Plain options for a **host-local** nested run. The runtime's checkpointer and
        cancellation cannot cross, so a composition the agent authors runs on the host with these
        and its events stay on the host's side of the record — D51 names this as the one residual
        of parity, and what closes it."""
        from shadow_hdk.kernel.leases import Floor, Lease

        return RunOptions(lease=Lease(ceiling, Floor(0)), **overrides)

    def spawn_options(self, *_args: Any, **_kw: Any) -> Any:
        raise WireOnlyAsync(
            "spawn_options() is synchronous in-process and cannot be over a wire; "
            "await context.spawn_options_now() instead"
        )

    @property
    def children(self) -> Any:
        return WireChildren(self._peer)


class WireChildren:
    """A run's children, driven from the host: spawn, send, release and is_held cross back (D51).

    The child run lives in the runtime, is held by the runtime across a park (D37), and the
    component it invokes crosses to the host like any other. What comes back is the handle and the
    child's events, which the runtime also put on the parent's stream — one record, one author.
    """

    def __init__(self, peer: Peer) -> None:
        self._peer = peer

    async def spawn(
        self,
        composition: Composition,
        ceiling: Ceiling,
        *,
        checkpointer: Any = None,
        within: EffectProfile | None = None,
        within_name: str = "",
    ) -> tuple[str, list[Event]]:
        answered = await self._peer.call(
            CONTEXT_SPAWN,
            {
                "composition": json.loads(dump(composition, Composition)),
                "ceiling": json.loads(dump(ceiling, Ceiling)),
                # The pattern's ceiling, as data: applied on the runtime's side as a second gate.
                "within": json.loads(dump(within, EffectProfile)) if within is not None else None,
                "within_name": within_name,
            },
        )
        return str(answered["handle"]), _events(answered["events"])

    async def send(self, handle: str, message: JsonValue) -> list[Event]:
        answered = await self._peer.call(CONTEXT_SEND, {"handle": handle, "message": message})
        return _events(answered["events"])

    async def release(self, handle: str) -> list[Event]:
        answered = await self._peer.call(CONTEXT_RELEASE, {"handle": handle})
        return _events(answered["events"])

    async def is_held(self, handle: str) -> bool:
        answered = await self._peer.call(CONTEXT_IS_HELD, {"handle": handle})
        return bool(answered["held"])


def _events(raw: Any) -> list[Event]:
    return [load(json.dumps(e), Event) for e in raw]


class NotAcrossTheWire(NotImplementedError):
    """Something that belongs to the run, asked for from the wrong side of the wire."""


class WireOnlyAsync(NotImplementedError):
    """A method that is synchronous in-process and cannot be, over a wire."""


__all__ = ["NotAcrossTheWire", "WireOnlyAsync", "WireRunContext"]
