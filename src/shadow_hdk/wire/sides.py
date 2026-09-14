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
from shadow_hdk.kernel.composition import Composition
from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import Event
from shadow_hdk.kernel.leases import Ceiling
from shadow_hdk.kernel.observations import Proposal
from shadow_hdk.kernel.ports import (
    Allow,
    Ask,
    Context,
    Judgement,
    ModelRequest,
    ModelResponse,
    Refuse,
)
from shadow_hdk.runtime import Approvals, Parked, Ports, RunOptions
from shadow_hdk.runtime.items import Fold, Item, as_json
from shadow_hdk.wire.channel import Channel, channel_pair
from shadow_hdk.wire.peer import Peer
from shadow_hdk.wire.protocol import (
    COMPLETE,
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
    EVENT,
    INITIALIZE,
    INVOKE,
    ITEM,
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
        observer: Any = None,
        threads: Any = None,
        admin: Any = None,
    ) -> None:
        self.peer = Peer(channel, name="runtime", timeout=timeout)
        self.initialized = False
        self._clock = clock
        self._observer = observer
        """The process serving the runtime may hand in an observer — an `ActivityObserver` hears
        what is happening (D63) on the runtime's side, which is where a crossed component's
        activity lands; Phase 26 puts it on the wire's own stream."""
        from langgraph.checkpoint.memory import InMemorySaver

        self.approvals = Approvals()
        """**A session owns a `Approvals` handle** (D58): a live question from a component on the
        host's side lands here, where the process serving the runtime can answer it — the same
        way it owns the checkpointer. A host in another language answers through its own process's
        surface on this object; the loopback tests reach it directly."""
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
        self.peer.serves(CONTEXT_REASONING, self._context_reasoning)
        self.peer.serves(CONTEXT_VISIBLE, self._context_visible)
        self.peer.serves(CONTEXT_FLOOR_MET, self._context_floor_met)
        self.peer.serves(CONTEXT_SPAWN, self._context_spawn)
        self.peer.serves(CONTEXT_SEND, self._context_send)
        self.peer.serves(CONTEXT_RELEASE, self._context_release)
        self.peer.serves(CONTEXT_IS_HELD, self._context_is_held)
        self.peer.serves(CONTEXT_KEEP, self._context_keep)
        self.peer.hears(CONTEXT_ACTIVITY, self._context_activity)
        self.peer.serves(CONTEXT_REQUEST_APPROVAL, self._context_request_approval)
        self.peer.serves(CONTEXT_REQUEST_INPUT, self._context_request_input)
        self.peer.serves(CONTEXT_RESUMED, self._context_resumed)
        from shadow_hdk.wire.threads import SoleSession, ThreadMethods

        self.threads = ThreadMethods(
            self.peer, threads, self._clock, admin=admin or SoleSession(self, clock=clock)
        )
        """The thread, crossed (D67): served when the process handed in a `ThreadHost`, refused
        with a reason when it did not. `admin` (D86) is what the process around this runtime
        knows of its sessions — the HTTP app's, or this one session alone over a pipe."""

    def ports(self) -> Ports:
        from shadow_hdk.runtime.clock import SystemClock

        return Ports(
            model=RemoteModel(self.peer),
            components=(RemoteComponents(self.peer, self),),
            governance=RemoteGovernance(self.peer),
            sink=RemoteSink(self.peer),
            clock=self._clock or SystemClock(),
            observer=self._observer,
        )

    async def _context_propose(self, params: dict[str, Any]) -> Any:
        if self.live is None:
            raise RuntimeError("nothing is running, so there is nothing to propose to")
        await self.live.propose(load(json.dumps(params["proposal"]), Proposal))
        return None

    async def _context_reasoning(self, params: dict[str, Any]) -> Any:
        if self.live is None:
            raise RuntimeError("nothing is running, so there is no record to think on")
        await self.live.reasoning(str(params.get("text", "")), step=params.get("step"))
        return None

    async def _context_visible(self, _params: dict[str, Any]) -> Any:
        if self.live is None:
            raise RuntimeError("nothing is running, so there is no registry to read")
        return {
            "registrations": [json.loads(dump(r, Registration)) for r in await self.live.visible()]
        }

    async def _context_request_approval(self, params: dict[str, Any]) -> Any:
        if self.live is None:
            raise RuntimeError("nothing is running, so there is nobody to ask")
        answer = await self.live.request_approval(
            str(params.get("question", "")),
            step=params.get("step"),
            about=(params.get("component"), params.get("inputs")),
        )
        if isinstance(answer, Allow | Ask | Refuse):
            answer = json.loads(dump(answer, Judgement))
        elif isinstance(answer, Parked):
            answer = {"kind": "park"}  # D88: kept for later, as the wire spells it
        return {"answer": answer}

    async def _context_request_input(self, params: dict[str, Any]) -> Any:
        """The agent's own question crosses and waits (D65); the text comes back, or `None` —
        or `{"kind": "park"}` when the host kept it for later (D88, BUG-044)."""
        if self.live is None:
            raise RuntimeError("nothing is running, so there is nobody to ask")
        answer = await self.live.request_input(
            str(params.get("question", "")), step=params.get("step")
        )
        if isinstance(answer, Parked):
            return {"answer": {"kind": "park"}}
        return {"answer": answer}

    async def _context_activity(self, params: dict[str, Any]) -> None:
        if self.live is None:
            return
        await self.live.activity(
            str(params.get("kind", "")), str(params.get("text", "")), step=params.get("step")
        )

    async def _context_keep(self, params: dict[str, Any]) -> Any:
        if self.live is None:
            raise RuntimeError("nothing is running, so there is nothing to keep this for")
        await self.live.keep(params.get("value"), step=params.get("step"))
        return None

    async def _context_resumed(self, params: dict[str, Any]) -> Any:
        if self.live is None:
            raise RuntimeError("nothing is running, so nothing was resumed")
        back = await self.live.resumed(step=params.get("step"))
        if back is None:
            return {"resumed": False}
        answer = back.answer
        if isinstance(answer, Allow | Ask | Refuse):
            answer = json.loads(dump(answer, Judgement))
        return {"resumed": True, "answer": answer, "kept": back.kept}

    async def _context_floor_met(self, _params: dict[str, Any]) -> Any:
        if self.live is None:
            raise RuntimeError("nothing is running, so there is no floor to meet")
        return {"floor_met": await self.live.floor_met_now()}

    async def _context_spawn(self, params: dict[str, Any]) -> Any:
        if self.live is None:
            raise RuntimeError("nothing is running, so there is nothing to spawn from")
        within = params.get("within")
        handle, events = await self.live.children.spawn(
            load(json.dumps(params["composition"]), Composition),
            load(json.dumps(params["ceiling"]), Ceiling),
            within=load(json.dumps(within), EffectProfile) if within is not None else None,
            within_name=str(params.get("within_name") or ""),
        )
        return {"handle": handle, "events": [json.loads(dump(e, Event)) for e in events]}

    async def _context_send(self, params: dict[str, Any]) -> Any:
        if self.live is None:
            raise RuntimeError("nothing is running")
        events = await self.live.children.send(str(params["handle"]), params.get("message"))
        return {"events": [json.loads(dump(e, Event)) for e in events]}

    async def _context_release(self, params: dict[str, Any]) -> Any:
        if self.live is None:
            raise RuntimeError("nothing is running")
        events = await self.live.children.release(str(params["handle"]))
        return {"events": [json.loads(dump(e, Event)) for e in events]}

    async def _context_is_held(self, params: dict[str, Any]) -> Any:
        if self.live is None:
            raise RuntimeError("nothing is running")
        return {"held": await self.live.children.is_held(str(params["handle"]))}

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
        from shadow_hdk import __version__

        return {"protocol_version": PROTOCOL_VERSION, "version": __version__}

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
            approvals=self.approvals,
        )
        ports = self.ports()
        stream = (
            resume_run(composition, params.get("answer"), ports, options=options)
            if resuming
            else run_once(composition, ports, options=options)
        )
        count = 0
        # **One fold, both sides of the wire** (D46). The events cross as they always did; the
        # steps cross already folded, so a host in another language renders them without porting
        # the fold — and parity with in-process is by construction, because this is the same
        # `Fold` that `steps()` and `run_items()` use.
        fold = Fold()
        async for event in stream:
            count += 1
            await self.peer.notify(EVENT, {"event": json.loads(dump(event, Event))})
            for done in fold.feed(event):
                await self.peer.notify(ITEM, {"item": as_json(done)})
        return {"events": count}


class HostSide:
    """The driver. Holds the real ports and answers the four callbacks out of them."""

    def __init__(self, channel: Channel, ports: Ports) -> None:
        self.peer = Peer(channel, name="host")
        self.ports = ports
        self.events: list[Event] = []
        self.items: list[Item] = []
        """The projection, as the runtime folded it — one entry per closed top-level step."""
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
        self.peer.hears(ITEM, self._item)

    async def initialize(self, *, protocol_version: str = PROTOCOL_VERSION) -> Agreed:
        from shadow_hdk.wire.peer import RemoteError

        try:
            answered = await self.peer.call(INITIALIZE, {"protocol_version": protocol_version})
        except RemoteError as refused:
            if isinstance(refused.data, dict) and refused.data.get("kind") == "version_mismatch":
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
        if self.ports.model is None:
            raise RuntimeError("this host holds no model port; a completion cannot be answered")
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
                    WireRunContext(
                        self.peer,
                        self.ports,
                        str(params.get("run_id", "")),
                        str(params.get("step") or wanted),
                    )
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

    async def _item(self, params: dict[str, Any]) -> None:
        self.items.append(load(json.dumps(params["item"]), Item))


@asynccontextmanager
async def loopback(
    ports: Ports | None = None,
    *,
    watching: Callable[[str], None] | None = None,
    timeout: float | None = 300.0,
    observer: Any = None,
    threads: Any = None,
) -> AsyncIterator[tuple[HostSide, RuntimeSide]]:
    """Both halves in one process, joined by a channel that carries JSON text."""
    from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

    real = ports or Ports(
        model=ScriptedModel(),
        components=(),
        governance=_AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    async with channel_pair(watching=watching) as (host_end, runtime_end):
        host = HostSide(host_end, real)
        runtime = RuntimeSide(
            runtime_end, clock=real.clock, timeout=timeout, observer=observer, threads=threads
        )
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
