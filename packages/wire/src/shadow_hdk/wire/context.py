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
from typing import Any

from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.kernel.leases import Lease
from shadow_hdk.kernel.observations import Proposal
from shadow_hdk.runtime import Ports, RunContext
from shadow_hdk.wire.peer import Peer
from shadow_hdk.wire.protocol import CONTEXT_PROPOSE, CONTEXT_REMAINING


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

    async def visible(self) -> Any:
        return self._across("visible()")

    @property
    def children(self) -> Any:
        return self._across("children")

    def spawn_options(self, *_args: Any, **_kw: Any) -> Any:
        return self._across("spawn_options()")

    def floor_met(self) -> bool:
        return self._across("floor_met()")


class NotAcrossTheWire(NotImplementedError):
    """Something that belongs to the run, asked for from the wrong side of the wire."""


class WireOnlyAsync(NotImplementedError):
    """A method that is synchronous in-process and cannot be, over a wire."""


__all__ = ["NotAcrossTheWire", "WireOnlyAsync", "WireRunContext"]
