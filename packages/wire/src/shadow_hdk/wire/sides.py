"""The two halves, and the loopback that puts them in one process.

`RuntimeSide` answers `initialize` / `run` / `resume` and holds `Remote*` ports pointing back at
whoever asked. `HostSide` does the mirror: it drives, and it answers the four callbacks out of the
real `Ports` it was given.

So a host with ordinary in-process ports gets a runtime on the far side of a wire without writing
anything new — which is what *the wire is a composition root over the same package, not a redesign*
has to mean if it means anything.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

import anyio

from shadow_hdk.kernel.components import Registration
from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import Event
from shadow_hdk.kernel.observations import Proposal
from shadow_hdk.kernel.ports import Context, Judgement, ModelRequest, ModelResponse
from shadow_hdk.runtime import Ports, RunOptions
from shadow_hdk.wire.channel import Channel, channel_pair
from shadow_hdk.wire.peer import Peer
from shadow_hdk.wire.protocol import (
    COMPLETE,
    CONTEXT_PROPOSE,
    CONTEXT_REMAINING,
    EVENT,
    INITIALIZE,
    INVOKE,
    JUDGE,
    PROPOSE,
    PROTOCOL_VERSION,
    REGISTRATIONS,
    RESUME,
    RUN,
    Agreed,
    VersionMismatch,
    WireError,
)
from shadow_hdk.wire.remote import (
    RemoteComponents,
    RemoteGovernance,
    RemoteModel,
    RemoteSink,
)


class RuntimeSide:
    """The served runtime. Answers `run`, and asks the host for what a port would have given."""

    def __init__(
        self,
        channel: Channel,
        *,
        clock: Any = None,
        checkpointer: Any = None,
        timeout: float | None = 300.0,
    ) -> None:
        self.peer = Peer(channel, name="runtime", timeout=timeout)
        self.initialized = False
        self._clock = clock
        from langgraph.checkpoint.memory import InMemorySaver

        self._checkpointer = checkpointer if checkpointer is not None else InMemorySaver()
        """**A session owns a checkpointer** (BUG-006). Without one every `resume` over the wire
        raised, so an Ask that crossed the wire could never be answered. The default lives as long
        as this session; a host that wants a parked run to outlive the process passes its own —
        the same checkpointer it would hand `run()`, and the same one Phase 6 proved on a file."""
        self.live: Any = None
        """The run currently in flight, so a component the host is executing can reach back to
        the meter and the event stream that actually belong to it."""
        self.peer.serves(INITIALIZE, self._initialize)
        self.peer.serves(RUN, self._run)
        self.peer.serves(RESUME, self._resume)
        self.peer.serves(CONTEXT_PROPOSE, self._context_propose)
        self.peer.serves(CONTEXT_REMAINING, self._context_remaining)

    def ports(self) -> Ports:
        from shadow_hdk.adapters.basic import SystemClock

        return Ports(
            model=RemoteModel(self.peer),  # type: ignore[arg-type]
            components=(RemoteComponents(self.peer, self),),  # type: ignore[arg-type]
            governance=RemoteGovernance(self.peer),  # type: ignore[arg-type]
            sink=RemoteSink(self.peer),  # type: ignore[arg-type]
            clock=self._clock or SystemClock(),
        )

    async def _context_propose(self, params: dict[str, Any]) -> Any:
        if self.live is None:
            raise RuntimeError("nothing is running, so there is nothing to propose to")
        await self.live.propose(load(json.dumps(params["proposal"]), Proposal))
        return None

    async def _context_remaining(self, _params: dict[str, Any]) -> Any:
        if self.live is None:
            raise RuntimeError("nothing is running, so there is no lease to report")
        from shadow_hdk.kernel.leases import Lease as _Lease

        return json.loads(dump(self.live.remaining(), _Lease))

    async def _initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        # An **omitted** version used to default to this build's own, so a peer that said nothing
        # counted as agreeing. Silence is not agreement: refuse, never degrade (wire.md).
        offered = str(params.get("protocol_version", "<none offered>"))
        if offered != PROTOCOL_VERSION:
            # Refuse, never degrade (wire.md). Both numbers are in the message because a mismatch
            # is somebody's deployment problem and they need to know which end to move.
            raise VersionMismatch(
                f"this runtime speaks protocol {PROTOCOL_VERSION!r}, not {offered!r}"
            )
        self.initialized = True
        return {"protocol_version": PROTOCOL_VERSION}

    async def _run(self, params: dict[str, Any]) -> dict[str, Any]:
        self._agreed()
        return await self._drive(params, resuming=False)

    async def _resume(self, params: dict[str, Any]) -> dict[str, Any]:
        self._agreed()
        return await self._drive(params, resuming=True)

    def _agreed(self) -> None:
        """`initialized` was set and never read. Two peers that have not agreed a version are two
        peers that do not yet know what a message means, so nothing runs before they have."""
        if not self.initialized:
            raise WireError("initialize first: this runtime and its host have agreed no version")

    async def _drive(self, params: dict[str, Any], *, resuming: bool) -> dict[str, Any]:
        from shadow_hdk.kernel.composition import Composition
        from shadow_hdk.kernel.leases import Lease
        from shadow_hdk.runtime import resume as resume_run
        from shadow_hdk.runtime import run as run_once

        composition = load(json.dumps(params["composition"]), Composition)
        options = RunOptions(
            lease=load(json.dumps(params["lease"]), Lease),
            context=params.get("context") or {},
            principal=params.get("principal"),
            run_id=params.get("run_id"),
            checkpointer=self._checkpointer,
        )
        ports = self.ports()
        stream = (
            resume_run(composition, params.get("answer"), ports, options=options)
            if resuming
            else run_once(composition, ports, options=options)
        )
        count = 0
        async for event in stream:
            count += 1
            await self.peer.notify(EVENT, {"event": json.loads(dump(event, Event))})
        return {"events": count}


class HostSide:
    """The driver. Holds the real ports and answers the four callbacks out of them."""

    def __init__(self, channel: Channel, ports: Ports) -> None:
        self.peer = Peer(channel, name="host")
        self.ports = ports
        self.events: list[Event] = []
        self.child_pid: int | None = None
        self.session_id: str | None = None
        """Set when the runtime is listening and this host connected to it."""
        self.watching: Callable[[Event], None] | None = None
        """Called as each event arrives, so a caller can see the stream rather than the total."""
        """Set when the runtime is a process rather than a task, so a test can prove it is one."""
        self.peer.serves(JUDGE, self._judge)
        self.peer.serves(COMPLETE, self._complete)
        self.peer.serves(REGISTRATIONS, self._registrations)
        self.peer.serves(INVOKE, self._invoke)
        self.peer.serves(PROPOSE, self._propose)
        self.peer.hears(EVENT, self._event)

    async def initialize(self, *, protocol_version: str = PROTOCOL_VERSION) -> Agreed:
        from shadow_hdk.wire.peer import RemoteError

        try:
            answered = await self.peer.call(INITIALIZE, {"protocol_version": protocol_version})
        except RemoteError as refused:
            if refused.data == "VersionMismatch":
                raise VersionMismatch(str(refused)) from refused
            raise
        return Agreed(protocol_version=str(answered["protocol_version"]))

    async def run(self, composition: Any, options: RunOptions) -> None:
        from shadow_hdk.kernel.composition import Composition
        from shadow_hdk.kernel.leases import Lease

        await self.peer.call(
            RUN,
            {
                "composition": json.loads(dump(composition, Composition)),
                "lease": json.loads(dump(options.lease, Lease)),
                "context": dict(options.context),
                "principal": options.principal,
                "run_id": options.run_id,
            },
        )

    async def resume(self, composition: Any, answer: Any, options: RunOptions) -> None:
        """Answer a run that parked. The composition comes back with it, as `resume()` requires:
        the runtime owns nothing durable, so it cannot remember the shape of a run it parked."""
        from shadow_hdk.kernel.composition import Composition
        from shadow_hdk.kernel.leases import Lease

        await self.peer.call(
            RESUME,
            {
                "composition": json.loads(dump(composition, Composition)),
                "lease": json.loads(dump(options.lease, Lease)),
                "context": dict(options.context),
                "principal": options.principal,
                "run_id": options.run_id,
                "answer": answer,
            },
        )

    # ---------------------------------------------------------------- the callbacks

    async def _judge(self, params: dict[str, Any]) -> Any:
        effects = load(json.dumps(params["effects"]), EffectProfile)
        context = load(json.dumps(params["context"]), Context)
        judgement = await self.ports.governance.judge(effects, context)
        return json.loads(dump(judgement, Judgement))

    async def _complete(self, params: dict[str, Any]) -> Any:
        request = load(json.dumps(params["request"]), ModelRequest)
        response = await self.ports.model.complete(request)
        return json.loads(dump(response, ModelResponse))

    async def _registrations(self, _params: dict[str, Any]) -> Any:
        listed: list[Any] = []
        for port in self.ports.components:
            for registration in await port.registrations():
                listed.append(json.loads(dump(registration, Registration)))
        return listed

    async def _invoke(self, params: dict[str, Any]) -> Any:
        """Run one of the host's components, **with a context bound** (D21).

        A component executes here, not in the runtime, so `current_run()` would otherwise be `None`
        and every idiom built on it would break — starting with `propose`, which is how `09`'s
        principle 3 says a component records anything at all.
        """
        from shadow_hdk.kernel.observations import Failed, Observation
        from shadow_hdk.runtime.bindings import _CURRENT
        from shadow_hdk.wire.context import WireRunContext

        wanted = str(params["registration"])
        for port in self.ports.components:
            known = {r.id for r in await port.registrations()}
            if wanted in known:
                token = _CURRENT.set(
                    WireRunContext(self.peer, self.ports, str(params.get("run_id", "")), wanted)
                )
                try:
                    observation = await port.invoke(wanted, params.get("inputs"))
                finally:
                    _CURRENT.reset(token)
                return json.loads(dump(observation, Observation))
        return json.loads(dump(Failed(f"no component registered as {wanted!r}"), Observation))

    async def _propose(self, params: dict[str, Any]) -> Any:
        await self.ports.sink.propose(load(json.dumps(params["proposal"]), Proposal))
        return None

    async def _event(self, params: dict[str, Any]) -> None:
        event: Event = load(json.dumps(params["event"]), Event)
        self.events.append(event)
        if self.watching is not None:
            self.watching(event)


@asynccontextmanager
async def loopback(
    ports: Ports | None = None,
    *,
    watching: Callable[[str], None] | None = None,
    timeout: float | None = 300.0,
) -> AsyncIterator[tuple[HostSide, RuntimeSide]]:
    """Both halves in one process, joined by a channel that carries JSON text."""
    from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

    real = ports or Ports(
        model=ScriptedModel(),
        components=(),
        governance=_AllowAll(),  # type: ignore[arg-type]
        sink=ListSink(),
        clock=FixedClock(),
    )
    async with channel_pair(watching=watching) as (host_end, runtime_end):
        host = HostSide(host_end, real)
        runtime = RuntimeSide(runtime_end, clock=real.clock, timeout=timeout)
        async with anyio.create_task_group() as group:
            group.start_soon(host.peer.serve_forever, group)
            group.start_soon(runtime.peer.serve_forever, group)
            try:
                yield host, runtime
            finally:
                group.cancel_scope.cancel()


class _AllowAll:
    async def judge(self, _effects: EffectProfile, _context: Context) -> Judgement:
        from shadow_hdk.kernel.ports import Allow

        return Allow()


async def drive(
    composition: Any,
    ports: Ports,
    *,
    options: RunOptions,
    watching: Callable[[str], None] | None = None,
) -> AsyncIterator[Event]:
    """Run a composition **over a loopback wire** and yield the events that came back.

    The same signature a host already uses, so a test that ran in-process runs over the wire by
    changing one word — which is what makes "the same suite runs both ways" a thing you can do
    rather than a thing you say.
    """
    async with loopback(ports, watching=watching) as (host, _runtime):
        await host.initialize()
        with anyio.fail_after(60):
            await host.run(composition, options)
        for event in host.events:
            yield event


__all__ = ["HostSide", "RuntimeSide", "drive", "loopback"]
