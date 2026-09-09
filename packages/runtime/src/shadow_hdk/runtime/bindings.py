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

from shadow_hdk.kernel.events import RunId
from shadow_hdk.kernel.leases import Ceiling, Lease
from shadow_hdk.kernel.observations import Proposal
from shadow_hdk.kernel.ports import (
    ClockPort,
    ComponentPort,
    GovernancePort,
    ModelPort,
    ObserverPort,
    SinkPort,
)

if TYPE_CHECKING:
    from shadow_hdk.runtime.emit import Emitter
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


class RunContext:
    """What a component sees of the run it is inside. Returned by `current_run()`."""

    def __init__(self, session: Session, emitter: Emitter, ports: Ports) -> None:
        self._session = session
        self._emitter = emitter
        self._ports = ports

    @property
    def run_id(self) -> RunId:
        return self._session.run_id

    @property
    def ports(self) -> Ports:
        return self._ports

    def now(self) -> str:
        return self._ports.clock.now()

    def remaining(self) -> Lease:
        return self._session.meter.remaining()

    def floor_met(self) -> bool:
        return self._session.meter.floor_met()

    def spawn_options(self, ceiling: Ceiling, **overrides: Any) -> RunOptions:
        """A child's options, carved from what this run has left."""
        return RunOptions(lease=self._session.meter.carve(ceiling), parent=self, **overrides)

    async def propose(self, proposal: Proposal) -> None:
        """Hand something to the sink. The runtime never decides whether it is kept."""
        from shadow_hdk.kernel.events import Proposed

        await self._emitter.emit(lambda **k: Proposed(proposal=proposal, **k))
        await self._ports.sink.propose(proposal)


_CURRENT: ContextVar[RunContext | None] = ContextVar("shadow_hdk_current_run", default=None)


def current_run() -> RunContext | None:
    """The run this code is executing inside, or `None` if it is not inside one."""
    return _CURRENT.get()
