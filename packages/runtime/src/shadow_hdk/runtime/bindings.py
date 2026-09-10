"""How a runtime is configured, and how a component reaches the run it is executing inside.

`Ports` and `RunOptions` are the runtime's, not the kernel's (D4): the kernel defines six protocols;
this is the bundle that wires them. `current_run()` is the ambient handle (D2) — how a component
proposes, reads what is left of its lease, and spawns children without any of those being a port.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final

from pydantic import JsonValue

from shadow_hdk.kernel.components import Registration
from shadow_hdk.kernel.events import RunId
from shadow_hdk.kernel.leases import Ceiling, Lease
from shadow_hdk.kernel.observations import Proposal
from shadow_hdk.kernel.ports import (
    ClockPort,
    ComponentPort,
    Context,
    GovernancePort,
    ModelPort,
    ObserverPort,
    Refuse,
    SinkPort,
)

if TYPE_CHECKING:
    from shadow_hdk.runtime.cancel import Cancellation
    from shadow_hdk.runtime.children import Children
    from shadow_hdk.runtime.emit import Emitter
    from shadow_hdk.runtime.registry import Registry
    from shadow_hdk.runtime.session import Session

MISSING: Final = object()
"""`RunOptions.parent` default: *look for an ambient parent*. `None` means *be a root*."""


@dataclass(frozen=True)
class Ports:
    """The six, bundled. Only `observer` is optional — `run()` always yields events regardless."""

    model: ModelPort
    components: tuple[ComponentPort, ...]
    governance: GovernancePort
    sink: SinkPort
    clock: ClockPort
    observer: ObserverPort | None = None


@dataclass(frozen=True)
class RunOptions:
    lease: Lease
    context: Mapping[str, JsonValue] = field(default_factory=dict)
    principal: str | None = None
    checkpointer: Any = None
    run_id: RunId | None = None
    parent: Any = MISSING
    cancellation: Cancellation | None = None
    """The host's handle on this run (D15). A child inherits its parent's unless handed its own."""


class RunContext:
    """What a component sees of the run it is inside. Returned by `current_run()`."""

    def __init__(
        self, session: Session, emitter: Emitter, ports: Ports, registry: Registry
    ) -> None:
        self._session = session
        self._emitter = emitter
        self._ports = ports
        self._registry = registry
        self._children: Children | None = None

    @property
    def run_id(self) -> RunId:
        return self._session.run_id

    @property
    def ports(self) -> Ports:
        return self._ports

    def now(self) -> str:
        return self._ports.clock.now()

    async def visible(self) -> list[Registration]:
        """What this run may see, as the policy leaves it.

        The same registry the executor resolves against, so *what the model was offered* and *what
        the runtime will let it invoke* cannot drift apart. A component the policy would refuse for
        every input is absent rather than greyed out (`09` §4).
        """
        await self._registry.refresh()
        context = self.context("<catalogue>")
        shown = []
        for registration in self._registry.all():
            judgement = await self._ports.governance.judge(registration.component.effects, context)
            if not isinstance(judgement, Refuse):
                shown.append(registration)
        return shown

    def context(self, step: str = "<catalogue>") -> Context:
        """What this run tells a policy about itself. An adapter that wants to know what the model
        may see asks the governance port with this."""
        return self._session.context_for(step)

    def remaining(self) -> Lease:
        return self._session.meter.remaining()

    def floor_met(self) -> bool:
        return self._session.meter.floor_met()

    def spawn_options(self, ceiling: Ceiling, **overrides: Any) -> RunOptions:
        """A child's options. The ceiling is a *request*: the drive carves it from what this run has
        left, so a child can never be promised more than its parent still holds — whoever asked."""
        from shadow_hdk.kernel.leases import Floor

        floor = Floor(min(self._session.meter.lease.floor.min_steps, ceiling.max_steps))
        # The parent's handle by default: a child that outlived the run which spawned it is a leak
        # with a budget. `cancellation=` in the overrides makes the child its own to stop (D15).
        overrides.setdefault("cancellation", self._session.cancellation)
        return RunOptions(lease=Lease(ceiling, floor), parent=self, **overrides)

    def reserve(self, ceiling: Ceiling) -> Lease:
        """Hold a child's worst case against this run's remaining budget."""
        return self._session.meter.carve(ceiling)

    def settle(self, reserved: Ceiling, *, steps: int, cost_cents: int, cost_known: bool) -> None:
        """Release that hold and charge what the child really spent."""
        self._session.meter.settle(
            reserved, steps=steps, cost_cents=cost_cents, cost_known=cost_known
        )

    @property
    def children(self) -> Children:
        """This run's children — spawn, send, release (D16). Built on first use, because most runs
        never have one."""
        from shadow_hdk.runtime.children import Children as _Children

        if self._children is None:
            self._children = _Children(self)
        return self._children

    async def announce_held(self, handle: str, steps_spent: int) -> None:
        """Say on this run's stream that a child parked and is being kept."""
        from shadow_hdk.kernel.events import Held

        await self._emitter.emit(
            lambda **k: Held(child_run_id=handle, handle=handle, steps_spent=steps_spent, **k)
        )

    async def announce_child(self, child_run_id: RunId, lease: Lease) -> None:
        """Say on this run's stream that a child began. The child's own events arrive by forward."""
        from shadow_hdk.kernel.events import Spawned

        await self._emitter.emit(lambda **k: Spawned(child_run_id=child_run_id, lease=lease, **k))

    async def forward(self, event: Any) -> None:
        """Pass a child's event into this run's stream, unstamped: it keeps the child's run id and
        the child's own sequence, so one consumer sees the whole tree and every event says whose."""
        await self._emitter.forward(event)

    async def propose(self, proposal: Proposal) -> None:
        """Hand something to the sink. The runtime never decides whether it is kept."""
        from shadow_hdk.kernel.events import Proposed

        await self._emitter.emit(lambda **k: Proposed(proposal=proposal, **k))
        await self._ports.sink.propose(proposal)


_CURRENT: ContextVar[RunContext | None] = ContextVar("shadow_hdk_current_run", default=None)


def current_run() -> RunContext | None:
    """The run this code is executing inside, or `None` if it is not inside one."""
    return _CURRENT.get()
