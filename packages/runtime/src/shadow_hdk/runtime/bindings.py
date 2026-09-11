"""How a runtime is configured, and how a component reaches the run it is executing inside.

`Ports` and `RunOptions` are the runtime's, not the kernel's (D4): the kernel defines six protocols;
this is the bundle that wires them. `current_run()` is the ambient handle (D2) — how a component
proposes, reads what is left of its lease, and spawns children without any of those being a port.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final

from pydantic import JsonValue

from shadow_hdk.kernel.components import Registration
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import RunId
from shadow_hdk.kernel.leases import Ceiling, Lease
from shadow_hdk.kernel.observations import Proposal
from shadow_hdk.kernel.ports import (
    ClockPort,
    ComponentPort,
    Context,
    GovernancePort,
    Judgement,
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
    from shadow_hdk.runtime.trust import Trust

MISSING: Final = object()
"""`RunOptions.parent` default: *look for an ambient parent*. `None` means *be a root*."""


@dataclass(frozen=True)
class Ports:
    """The six, bundled. Only `observer` is optional — `run()` always yields events regardless.

    `trust` is not a port (D22 leaves the set open, but this is configuration, not a seam): the
    keys a deployment holds and the effects it requires proof for, checked at the registry on every
    refresh. `None` means no driver is asked to prove itself — the state of every deployment before
    ADR-1 says otherwise.
    """

    model: ModelPort | None = field(default=None, kw_only=True)
    """`None` is legitimate and common: the runtime is a governed workflow engine before it is an
    agent runner, and a composition of plain components needs no model at all (ENH-004).

    It was required, so the simplest possible program — a plan, some tools, a policy — ran fine and
    failed to type-check, and the README had to explain the discrepancy. `kw_only` so the field can
    take a default without reordering the five that follow it; every caller already names it.

    A provider driving through `AgentPort` also leaves this `None`: the reasoning is the provider's,
    and this runtime supplies no model to it (D39).
    """

    components: tuple[ComponentPort, ...]
    governance: GovernancePort
    sink: SinkPort
    clock: ClockPort
    observer: ObserverPort | None = None
    trust: Trust | None = None


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
        self,
        session: Session,
        emitter: Emitter,
        ports: Ports,
        registry: Registry,
        checkpointer: Any = None,
    ) -> None:
        self._session = session
        self._emitter = emitter
        self._ports = ports
        self._registry = registry
        self._checkpointer = checkpointer
        self._children: Children | None = None

    @property
    def checkpointer(self) -> Any:
        """The one this run was driven with. A child spawned here shares it by default (D37), so
        a parent that parks can reach that child again when it comes back."""
        return self._checkpointer

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
        shown = []
        for registration in self._registry.all():
            context = self.context("<catalogue>", registration)
            judgement = await self._judged(registration.component.effects, context)
            if not isinstance(judgement, Refuse):
                shown.append(registration)
        return shown

    async def _judged(self, effects: EffectProfile, context: Context) -> Judgement:
        """Ask the policy, and let a **port** failure be one (TD-006, D7).

        This ran unwrapped, inside whatever component asked for a catalogue — so a policy service
        that was down surfaced as *that component failed*, which is an agent's cue to try something
        else. The one thing that must stop a run became the one thing an agent routes around. The
        step has always wrapped `judge` this way; there is no reason the catalogue should not.
        """
        from shadow_hdk.runtime.errors import PortFailure, RuntimeStop

        try:
            return await self._ports.governance.judge(effects, context)
        except RuntimeStop:
            raise
        except Exception as exc:
            raise PortFailure("governance", exc) from exc

    @property
    def unreachable(self) -> tuple[str, ...]:
        """Component ports that would not list their components on the last refresh (TD-006).

        `refresh()` tolerates one deliberately — a catalogue that will not answer is empty, and one
        broken server should not end a run that never needed it. But it collected the failures into
        a list **nothing read**, so a vanished server was a catalogue that quietly shrank, which is
        indistinguishable from a policy that narrowed. A host can see it now.

        It is not yet on the **event stream**, which is where it belongs, because that needs a
        twelfth event kind and therefore a contract change. Filed rather than smuggled in.
        """
        return tuple(self._registry.unreachable)

    def context(
        self, step: str = "<catalogue>", registration: Registration | None = None
    ) -> Context:
        """What this run tells a policy about itself. An adapter that wants to know what the model
        may see asks the governance port with this."""
        return self._session.context_for(step, registration)

    def remaining(self) -> Lease:
        return self._session.meter.remaining()

    async def remaining_now(self) -> Lease:
        """`remaining()`, awaitable — the form an adapter uses if it means to run over a wire too.

        In-process the meter is here and the answer is immediate; across a wire the meter is on
        the other side and the question has to cross. An adapter that calls the synchronous form
        works in-process and raises the moment its ports invert, which is how `AgentComponent`
        turned out to be unable to run over the wire at all (Phase 21, found by a test).
        """
        return self.remaining()

    @property
    def step(self) -> str | None:
        """The step being executed, or `None` outside one — while the catalogue is read, say."""
        return _STEP.get()

    def idempotency_key(self) -> str:
        """What *we* call this act: the run and the step. A retry of the step — LangGraph re-runs a
        node on resume — carries the same key, so the world can tell it from a second act."""
        step = self.step
        if step is None:
            raise RuntimeError("no step is executing, so there is no act to name")
        return f"{self.run_id}/{step}"

    def floor_met(self) -> bool:
        return self._session.meter.floor_met()

    async def floor_met_now(self) -> bool:
        """`floor_met()`, awaitable — the form an adapter uses if it means to run over a wire too
        (D51). In-process the meter is here; across a wire the question crosses."""
        return self.floor_met()

    async def spawn_options_now(self, ceiling: Ceiling, **overrides: Any) -> RunOptions:
        """`spawn_options()`, awaitable. Across a wire the runtime's checkpointer and cancellation
        cannot travel, so the crossed form answers with plain options for a host-local nested run —
        see D51 for what that leaves on the host's side of the record."""
        return self.spawn_options(ceiling, **overrides)

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
        """Hand something to the sink, then say so. The runtime never decides whether it is kept.

        **The order is the point** (TD-006). `Proposed` used to go on the record first and the sink
        was called after, unwrapped — so a sink that raised left a record of a proposal that never
        arrived anywhere, and the exception surfaced as the proposing *component's* failure. That is
        the rule `FileSink` holds inside itself (BUG-014), one layer up: what was not kept is not
        reported as kept. A sink is a port, so its failure ends the run (D7).
        """
        from shadow_hdk.kernel.events import Proposed
        from shadow_hdk.runtime.errors import PortFailure, RuntimeStop

        try:
            await self._ports.sink.propose(proposal)
        except RuntimeStop:
            raise
        except Exception as exc:
            raise PortFailure("sink", exc) from exc
        await self._emitter.emit(lambda **k: Proposed(proposal=proposal, **k))

    async def reasoned(self, text: str, *, step: str | None = None) -> None:
        """Put thinking on the record, beside what it led to (D45).

        The step is the one executing — the agent's own, so a projection folds the thought under
        the step that was thinking rather than the tool it then reached for. Empty text emits
        nothing: a kind that appears when there is nothing to say is one readers learn to skip.

        `step` is for a caller that knows better than the contextvar: a thought that crossed a
        wire is answered on the peer's task, where nothing is executing, and the host-side context
        that sent it is the one that knows which step was thinking.
        """
        from shadow_hdk.kernel.events import Reasoned

        if not text:
            return
        where = step if step is not None else (self.step or "")
        await self._emitter.emit(lambda **k: Reasoned(step=where, text=text, **k))


_CURRENT: ContextVar[RunContext | None] = ContextVar("shadow_hdk_current_run", default=None)
_STEP: ContextVar[str | None] = ContextVar("shadow_hdk_current_step", default=None)


@contextmanager
def executing(step: str) -> Iterator[None]:
    """The scope within which `current_run().step` is this step: the component's invoke, only."""
    token = _STEP.set(step)
    try:
        yield
    finally:
        _STEP.reset(token)


def current_run() -> RunContext | None:
    """The run this code is executing inside, or `None` if it is not inside one."""
    return _CURRENT.get()
