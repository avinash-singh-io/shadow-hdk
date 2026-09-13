"""A thread of turns, each turn a run (D62).

The container every product has — thread (Codex, OpenAI, LangGraph), session (ACP, Claude Code)
— as the harness's own primitive: a provider session opened once and held across turns, the
run's registry offered to it for the thread's lifetime under the host's name, each turn its own
run under a ceiling carved from the thread's lease, and the record kept through a `ThreadStore`
the host may implement over its own tables or not use at all.

**A turn is a run.** The plan (`planning/the-substrate.md` §1.8) first said "a step of the
thread's run"; a composition is fixed when compiled and a run parks between turns only by
grammar the person would have to answer, so the truthful unit is what the loop already has: one
execution under a lease, with its own record — which is exactly the OpenAI Assistants API's
thread → run → step. Thread → Turn → Item is Thread → Run → Step, and nothing is invented.

**Fork and rollback are honest.** A provider's own transcript cannot be rewound. A fork copies
the record; a rollback is a fork of the first N turns, and the new thread says `seeded_turns=N`
so its first turn can be seeded with what was kept rather than the runtime pretending the
provider remembers.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

from pydantic import JsonValue

from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Completed,
    Component,
    Composition,
    EffectProfile,
    Ended,
    Failed,
    Floor,
    Interface,
    Invoke,
    Lease,
    Observation,
    Observed,
    PendingQuestion,
    Provenance,
    Registration,
    ScopeSet,
    Spent,
    ThreadRecord,
    TurnRecord,
)
from shadow_hdk.kernel.contracts import dump
from shadow_hdk.kernel.events import (
    ApprovalRequested,
    Event,
    InputRequested,
    ModeChanged,
    WorkspaceChanged,
)
from shadow_hdk.kernel.events import Refused as RefusedEvent
from shadow_hdk.kernel.ports import (
    AgentPort,
    AgentSession,
    ComponentPort,
    Context,
    ThreadStore,
)
from shadow_hdk.kernel.usage import Usage
from shadow_hdk.kernel.workspace import Root, Workspace
from shadow_hdk.runtime.bindings import Ports, RunOptions, current_run
from shadow_hdk.runtime.cancel import Cancellation
from shadow_hdk.runtime.environment import Environment
from shadow_hdk.runtime.loop import resume as resume_run
from shadow_hdk.runtime.loop import run
from shadow_hdk.runtime.offer import InProcessOffer, Offer
from shadow_hdk.runtime.session import RESERVED_ATTRIBUTES, LeaseMeter

TURN = "turn"

HOLD_SECONDS = 30.0
"""How long a hold on a thread lives without renewal (D81): a host that died is out of the way
within half a minute; a live one renews every third of it."""

When = Literal["enqueue", "reject", "interrupt"]
"""What a second turn does while one runs (D81): wait its turn, be refused, or stop the first."""


class ThreadHeld(RuntimeError):
    """The thread is open in another process (D81): the store says who holds it."""

    def __init__(self, thread_id: str, holder: str) -> None:
        super().__init__(f"thread {thread_id!r} is held by {holder!r}")
        self.thread_id = thread_id
        self.holder = holder


class TurnRunning(RuntimeError):
    """A turn is running and the caller asked not to wait (`when="reject"`, D81)."""

    def __init__(self, thread_id: str, turn_id: str) -> None:
        super().__init__(f"thread {thread_id!r} is running {turn_id}")
        self.thread_id = thread_id
        self.turn_id = turn_id


TURN_EFFECTS = EffectProfile(
    reads=ScopeSet(everything=True),
    # What holding a turn *itself* writes: the provider's own state — a transcript under its
    # home, never the root, because every write to the root goes through the run's environment
    # and is judged there. And a turn cannot be un-had.
    writes=ScopeSet.of("provider-state"),
    reaches=True,
    reversible=False,
    costs=True,
)


@dataclass(frozen=True)
class Offered:
    """One registration as the agent would be offered it now, and which port carried it."""

    registration: Registration
    judgement: str
    """`allow` · `ask` · `refuse` — what the current mode says of its effects."""
    source: str
    """Who registered it — the registration's own provenance (`environment`, `agent`, a battery's
    id) — and the port's class name after a colon where that adds something
    (`environment:LocalEnvironment`). A wrapper such as `Switched` is looked through: it carries
    a port, it is not the source."""


def _unwrapped(port: Any) -> Any:
    inner = port
    while (wrapped := getattr(inner, "_inner", None)) is not None:  # `Switched`, or the next
        inner = wrapped
    return inner


def _environment_of(ports: Ports) -> Environment | None:
    """The environment among the ports, if one is there — the runtime's own base class, so no
    adapter is named here; a host that composes something else gets `None` and no re-opening."""
    for port in ports.components:
        inner = _unwrapped(port)
        if isinstance(inner, Environment):
            return inner
    return None


def _environment_mode_of(ports: Ports) -> str:
    environment = _environment_of(ports)
    return environment.mode if environment is not None else ""


def _source_of(port: ComponentPort, registration: Registration) -> str:
    inner = _unwrapped(port)
    who = registration.component.provenance.registered_by
    kind = type(inner).__name__
    return who if who.lower() == kind.lower() else f"{who}:{kind}"


class _TurnComponents(ComponentPort):
    """The one component a turn's run has of its own: the step that drives the provider."""

    def __init__(self, registration: Registration, handler: Any, at: str) -> None:
        self._registration = registration
        self._handler = handler

    async def registrations(self) -> Sequence[Registration]:
        return [self._registration]

    async def invoke(self, registration: str, inputs: JsonValue) -> Observation:
        if registration != self._registration.id:
            return Failed(f"no component registered as {registration!r}")
        answered: Observation = await self._handler(inputs)
        return answered


def _turn_registration(at: str) -> Registration:
    return Registration(
        id=TURN,
        component=Component(
            interface=Interface(
                name=TURN,
                description="One turn of the conversation with the provider.",
                input_schema={"type": "object", "properties": {"prompt": {"type": "string"}}},
                output_schema={"type": "object"},
            ),
            effects=TURN_EFFECTS,
            provenance=Provenance(registered_by="thread", adapter="runtime", at=at),
            labels=frozenset({"conversation"}),
        ),
    )


class InMemoryThreads(ThreadStore):
    """A `ThreadStore` that lives as long as the process — tests and a host that keeps its own."""

    def __init__(self) -> None:
        self._threads: dict[str, ThreadRecord] = {}
        self._holds: dict[str, tuple[str, float]] = {}
        """thread id → (holder, until) on the process's monotonic clock (D81)."""

    def _holder(self, thread_id: str) -> str | None:
        held = self._holds.get(thread_id)
        if held is None or held[1] <= time.monotonic():
            return None
        return held[0]

    async def hold(self, thread_id: str, holder: str, *, ttl_seconds: float) -> bool:
        current = self._holder(thread_id)
        if current is not None and current != holder:
            return False
        self._holds[thread_id] = (holder, time.monotonic() + ttl_seconds)
        return True

    async def renew(self, thread_id: str, holder: str, *, ttl_seconds: float) -> bool:
        if self._holder(thread_id) != holder:
            return False
        self._holds[thread_id] = (holder, time.monotonic() + ttl_seconds)
        return True

    async def release(self, thread_id: str, holder: str) -> None:
        if self._holder(thread_id) == holder:
            del self._holds[thread_id]

    async def held_by(self, thread_id: str) -> str | None:
        return self._holder(thread_id)

    async def create(self, thread: ThreadRecord) -> None:
        self._threads[thread.id] = thread

    async def get(self, thread_id: str) -> ThreadRecord | None:
        return self._threads.get(thread_id)

    async def save(self, thread: ThreadRecord) -> None:
        self._threads[thread.id] = thread

    async def list(self, *, include_archived: bool = False) -> tuple[ThreadRecord, ...]:
        return tuple(t for t in self._threads.values() if include_archived or not t.archived)

    async def archive(self, thread_id: str) -> None:
        found = self._threads.get(thread_id)
        if found is not None:
            self._threads[thread_id] = _replace(found, archived=True)


def _replace(record: ThreadRecord, **changes: Any) -> ThreadRecord:
    return replace(record, **changes)


class Thread:
    """The conversation, held: open once, turn many times, close."""

    def __init__(
        self,
        record: ThreadRecord,
        *,
        agent: AgentPort,
        ports: Ports,
        store: ThreadStore,
        lease: Lease,
        registry: Offer,
        approvals: Any = None,
        checkpointer: Any = None,
        modes: Any = None,
        rules: Any = None,
        holder: str = "",
        hold_seconds: float = HOLD_SECONDS,
    ) -> None:
        self._record = record
        self.holder = holder
        """Who holds this thread (D81) — the process's name on the store's lease; empty when the
        thread was opened without one, which takes no hold."""
        self._hold_seconds = hold_seconds
        self._renewing: asyncio.Task[None] | None = None
        self._rules = rules
        """The host's act-rule registry (D65), handed to every turn's run."""
        self._agent = agent
        self._ports = ports
        self._store = store
        # **The thread's own budget over the host's default, from what it already spent** (D84).
        # The meter was per opening before: a resumed thread spent its whole budget again.
        own = Lease(record.budget, lease.floor) if record.budget is not None else lease
        self._meter = LeaseMeter(own, ports.clock)
        self._meter.restore(
            {
                "steps": record.spent.steps,
                "cost_cents": record.spent.cents,
                "unpriced": 1 if record.spent.unpriced else 0,
                "elapsed_seconds": record.spent.seconds,
            }
        )
        self.registry = registry
        self._approvals = approvals
        self._checkpointer = checkpointer
        self._session: AgentSession | None = None
        self._holder: asyncio.Task[None] | None = None
        self._let_go: asyncio.Event = asyncio.Event()
        self._turning: asyncio.Lock = asyncio.Lock()
        self._sources: tuple[Any, ...] = ()
        self._modes = modes
        """A `ModeRegistry`, structurally (`get(id) -> ModeSpec`): the runtime never imports the
        modes adapter, so a host hands in its own. `None` means the thread has no behaviours to
        apply and `set_mode` only flips the policy the governance selects by."""
        self._behaviour: Any = None
        self._options: dict[str, JsonValue] = {}
        self._current: Cancellation | None = None
        """The running turn's handle to stop it (D15), while one runs."""
        self._interrupted = False
        self._kept: list[str] = []
        """Steering the provider could not take mid-turn, and what became of a call settled after
        the host that heard it died (D80): folded into the next prompt."""
        self._parked: list[PendingQuestion] = []
        """Children parked during the running turn, by step — so the turn's question can name
        the run to wake. Only the running turn's; cleared as it starts."""

    # ------------------------------------------------------------------ opening and closing

    @classmethod
    async def open(
        cls,
        *,
        agent: AgentPort,
        ports: Ports,
        store: ThreadStore,
        root: Path | str,
        lease: Lease,
        registry: Offer | None = None,
        name: str = "tools",
        approvals: Any = None,
        checkpointer: Any = None,
        modes: Any = None,
        rules: Any = None,
        mode: str = "",
        provider: str = "",
        thread_id: str | None = None,
        workspace: Workspace | None = None,
        holder: str = "",
        hold_seconds: float = HOLD_SECONDS,
        principal: str = "",
        attributes: Mapping[str, JsonValue] | None = None,
        budget: Ceiling | None = None,
    ) -> Thread:
        """Start a thread: the record created, the registry served, the provider opened.

        `budget` (D84) is this thread's own ceiling over `lease`, the host's default; what the
        thread spends is on its record after every turn, and a resume starts from it.

        `holder` names this process on the thread's hold (D81): taken here, renewed while the
        thread is open, released at close; `ThreadHeld` when another process has it.

        `principal` and `attributes` (D82) are who the thread is for and the product's words
        about it — on the record, and on every judgement's context from now on. A reserved
        attribute name (`component`, `inputs`, `posture`) is refused here, as it is on a run.

        `workspace` names the roots (D76) — one or many; `root` alone is the one-root workspace.
        The record carries both: `root` the primary for a one-root reader, `roots` the whole.

        `mode` is the **policy's** mode id — what `ModeGovernance` selects by at every step of
        every turn (the context key `mode`) — not the environment's; a thread opened with the
        environment's word was refused at its first turn (*'workspace-write' is not a mode here*)
        because two vocabularies were one key. Until modes are one thing (group 4), a host passes
        the policy's name.
        """
        workspace = workspace or Workspace.of(root)
        given = dict(attributes or {})
        if taken := sorted(set(given) & RESERVED_ATTRIBUTES):
            raise ValueError(f"attributes {taken} are the runtime's own; choose other names")
        record = ThreadRecord(
            id=thread_id or ports.clock.new_id(),
            root=str(workspace.primary.path),
            created_at=ports.clock.now(),
            mode=mode,
            provider=provider,
            roots=workspace.roots,
            environment=_environment_mode_of(ports),
            principal=principal,
            attributes=given,
            budget=budget,
        )
        await store.create(record)
        thread = cls(
            record,
            agent=agent,
            ports=ports,
            store=store,
            lease=lease,
            registry=registry or InProcessOffer(name=name, withhold={TURN}),
            approvals=approvals,
            checkpointer=checkpointer,
            modes=modes,
            rules=rules,
            holder=holder,
            hold_seconds=hold_seconds,
        )
        if modes is not None and (spec := modes.get(mode)) is not None:
            thread._behaviour = spec.behaviour
        await thread._take_hold()
        await thread._start()
        return thread

    @classmethod
    async def resume(
        cls,
        thread_id: str,
        *,
        agent: AgentPort,
        ports: Ports,
        store: ThreadStore,
        lease: Lease,
        registry: Offer | None = None,
        name: str = "tools",
        approvals: Any = None,
        checkpointer: Any = None,
        modes: Any = None,
        rules: Any = None,
        holder: str = "",
        hold_seconds: float = HOLD_SECONDS,
    ) -> Thread:
        """Pick a thread up from its store: the provider reopened (with its own session id, when
        it kept one), the turns kept, the numbering continued. `ThreadHeld` when another process
        holds it (D81) — nothing is read as left by a dead host while a live one has the thread."""
        record = await store.get(thread_id)
        if record is None:
            raise KeyError(f"no thread {thread_id!r} in the store")
        thread = cls(
            record,
            agent=agent,
            ports=ports,
            store=store,
            lease=lease,
            registry=registry or InProcessOffer(name=name, withhold={TURN}),
            approvals=approvals,
            checkpointer=checkpointer,
            modes=modes,
            rules=rules,
            holder=holder,
            hold_seconds=hold_seconds,
        )
        if modes is not None and (spec := modes.get(record.mode)) is not None:
            thread._behaviour = spec.behaviour
        await thread._take_hold()
        await thread._settle_what_the_last_host_left()
        await thread._start()
        return thread

    async def _take_hold(self) -> None:
        """The hold (D81), and the task that renews it every third of its life. A thread opened
        without a holder takes none."""
        if not self.holder:
            return
        if not await self._store.hold(self.id, self.holder, ttl_seconds=self._hold_seconds):
            other = await self._store.held_by(self.id)
            raise ThreadHeld(self.id, other or "another holder")
        every = self._hold_seconds / 3

        async def renewing() -> None:
            while True:
                await asyncio.sleep(every)
                if not await self._store.renew(
                    self.id, self.holder, ttl_seconds=self._hold_seconds
                ):
                    return  # lost: the hold lapsed and another took it; nothing to renew

        self._renewing = asyncio.create_task(renewing())

    async def _settle_what_the_last_host_left(self) -> None:
        """A turn still `running` on a record nobody is running is one the last host died in
        (D80). With a question open it is `parked` — the question stays pending, the run that
        parked on it is in the checkpointer, and `settle` finishes it; with nothing open the
        turn is `cancelled`, and the text says by what, because nothing else can be known."""
        turns = list(self._record.turns)
        if not turns or turns[-1].outcome != "running":
            return
        last = turns[-1]
        open_here = tuple(q for q in self._record.pending if q.turn == last.id)
        if open_here:
            turns[-1] = _replace_turn(last, outcome="parked")
        else:
            turns[-1] = _replace_turn(
                last, outcome="cancelled", text="the host went away before the turn ended"
            )
        self._record = _replace(self._record, turns=tuple(turns), pending=open_here)
        await self._store.save(self._record)

    async def _start(self) -> None:
        # **The offer lives in a task of its own.** A socket offer is an anyio listener and a task
        # group, and those are bound to the task that entered them; `open` and `close` are called
        # from whichever task a host happens to be on — over the wire, two different handler
        # tasks — and exiting a cancel scope from another task is an error. So one task holds the
        # offer open for the thread's lifetime and is told when to let go. Measured behind
        # `serve --http`: the first thread opened over HTTP died at close with *"attempted to exit
        # a cancel scope that isn't the current task's"*.
        loop = asyncio.get_running_loop()
        ready: asyncio.Future[tuple[Any, ...]] = loop.create_future()
        self._let_go = asyncio.Event()

        async def hold() -> None:
            try:
                async with self.registry.served() as sources:
                    if not ready.done():
                        ready.set_result(tuple(sources))
                    await self._let_go.wait()
            except BaseException as failed:
                if not ready.done():
                    ready.set_exception(failed)
                raise

        self._holder = asyncio.create_task(hold())
        self._sources = await ready
        self._session = await self._open_provider()

    async def _open_provider(self) -> AgentSession:
        """The provider's session, opened on this thread's tools, workspace and behaviour — and
        resumed on its own session id when the record has one (D76), so a reopen after a mode
        change, a root added or a `thread/resume` keeps the agent's memory of the conversation.
        `resume` is passed only when there is one, so an opener without the keyword (a test
        double, an adapter that predates it) is still called the way it always was."""
        extra: dict[str, Any] = {}
        if self._record.session_id:
            extra["resume"] = self._record.session_id
        return await self._agent.open(
            tools=tuple(self._sources),
            workspace=self._record.root,
            behaviour=self._behaviour,
            **extra,
        )

    async def _remember_session(self) -> None:
        """The provider's own session id, off the session, onto the record — what a resume hands
        back (D76)."""
        found = getattr(self._session, "session_id", None) if self._session is not None else None
        if isinstance(found, str) and found and found != self._record.session_id:
            self._record = _replace(self._record, session_id=found)
            await self._store.save(self._record)

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
        holder = self._holder
        if holder is not None:
            self._let_go.set()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await holder
            self._holder = None
        if self._renewing is not None:
            self._renewing.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._renewing
            self._renewing = None
        if self.holder:
            await self._store.release(self.id, self.holder)

    # ------------------------------------------------------------------ what it is

    @property
    def id(self) -> str:
        return self._record.id

    @property
    def record(self) -> ThreadRecord:
        return self._record

    def remaining(self) -> Lease:
        """What the thread may still spend across its turns: its budget less what is on the
        record (D84)."""
        return self._meter.remaining()

    def _spent(self) -> Spent:
        """The meter's counters, in the record's words (D84)."""
        counted = self._meter.spent()
        return Spent(
            steps=int(counted["steps"]),
            seconds=float(counted["elapsed_seconds"]),
            cents=int(counted["cost_cents"]),
            unpriced=bool(counted["unpriced"]),
        )

    @property
    def turning(self) -> bool:
        """Whether a turn is running right now."""
        return self._current is not None

    # ------------------------------------------------------------------ turning

    async def turn(self, text: str, *, when: When = "enqueue") -> AsyncIterator[Event]:
        """One exchange: the person's text in, the run's events out, the record kept.

        The turn is a run of one step, `turn-N`, whose component drives the provider session;
        the provider's tool calls arrive through the registry, attached to this run for the
        turn's duration, and are child runs under the step — so a host folds them under the
        turn's item (D62).

        `when` says what this turn does while another runs (D81): `enqueue` waits its turn (the
        default); `reject` raises `TurnRunning` and records nothing; `interrupt` stops the
        running turn — it ends `cancelled`, as `interrupt()` ends it — and starts this one.
        """
        if when not in ("enqueue", "reject", "interrupt"):
            raise ValueError(f"when={when!r}: one of enqueue, reject, interrupt")
        if self._holder is None:
            raise RuntimeError("the thread is closed")
        if self._turning.locked():
            if when == "reject":
                raise TurnRunning(self.id, self._record.turns[-1].id)
            if when == "interrupt":
                await self.interrupt()
        if self._session is None:
            # An interrupted provider that could not be told was closed; a turn reopens it.
            self._session = await self._open_provider()
        async with self._turning:
            # What is left is read here, under the lock: a running turn reserves everything the
            # thread has, and a turn that waited its turn (D81) reads the meter after that
            # reservation settled — read before, it saw nothing left and was refused.
            if (left := self._meter.remaining().ceiling).max_steps <= 0:
                raise RuntimeError("the thread has no steps left")
            if self._kept:
                text = "\n\n".join((*self._kept, text))
                self._kept.clear()
            number = len(self._record.turns) + 1
            turn_id = f"{TURN}-{number}"
            run_id = self._ports.clock.new_id()
            reserved = Ceiling(
                max_steps=left.max_steps,
                max_wall_seconds=left.max_wall_seconds,
                max_cost_cents=left.max_cost_cents,
            )
            lease = self._meter.carve(reserved)
            session = self._session
            registry = self.registry
            cancellation = Cancellation()
            self._current = cancellation
            self._interrupted = False
            self._parked = []

            async def turn_component(inputs: Any) -> Observation:
                context = current_run()
                assert context is not None
                prompt = str(inputs.get("prompt", "")) if isinstance(inputs, dict) else ""
                registry.attach(context)
                try:
                    done = await session.turn(prompt)
                finally:
                    registry.detach()
                if done.reasoning and context.recorded("reasoning") == 0:
                    # The provider's transport may already have put each thought on the record
                    # as it arrived (the jsonl session does); the whole is then a repeat. Only a
                    # provider that recorded nothing has this said for it (principle 6: once).
                    await context.reasoning(done.reasoning)
                output: dict[str, JsonValue] = {"text": done.text, "stop_reason": done.stop_reason}
                if done.usage is not None:
                    # The step's cost, where the meter reads it (D20).
                    output["usage"] = json.loads(dump(done.usage, Usage))
                return Completed(output)

            at = self._ports.clock.now()
            base = self._ports
            ports = replace(
                base,
                components=(
                    *base.components,
                    _TurnComponents(_turn_registration(at), turn_component, at),
                ),
            )
            plan = Composition(
                (Invoke(turn_id, TURN, (Binding("prompt", value=text),)),),
            )
            options = RunOptions(
                lease=lease,
                run_id=run_id,
                approvals=self._approvals,
                rules=self._rules,
                checkpointer=self._checkpointer,
                cancellation=cancellation,
                principal=self._record.principal or None,
                context=self._context_for(turn_id),
            )
            self._record = _replace(
                self._record,
                turns=(
                    *self._record.turns,
                    TurnRecord(id=turn_id, run_id=run_id, prompt=text, at=self._ports.clock.now()),
                ),
            )
            await self._store.save(self._record)
            outcome: str = "completed"
            said = ""
            steps_taken = 0
            spent_cents = 0
            cost_known = True
            try:
                async for event in run(plan, ports, options=options):
                    await self._keep_pending(event, turn_id, run_id)
                    if isinstance(event, Observed) and event.step == turn_id:
                        if isinstance(event.observation, Completed) and isinstance(
                            event.observation.output, dict
                        ):
                            said = str(event.observation.output.get("text", ""))
                        elif isinstance(event.observation, Failed):
                            outcome = "failed"
                    if isinstance(event, RefusedEvent) and event.step == turn_id:
                        outcome = "refused"
                        said = event.reason
                    if isinstance(event, Ended) and event.run_id == run_id:
                        steps_taken = event.steps_taken
                        if event.reason == "cancelled":
                            outcome = "cancelled"
                        elif event.reason != "completed" and outcome == "completed":
                            outcome = "failed"
                            said = said or f"the turn ended {event.reason}"
                    if event.kind == "usage" and event.run_id == run_id:
                        usage = getattr(event, "usage", None)
                        if usage is not None and usage.cost_cents is not None:
                            spent_cents += usage.cost_cents
                        elif usage is not None:
                            cost_known = False
                    yield event
            finally:
                self._current = None
                if self._interrupted:
                    # The person stopped it. The run may still say `completed` — a provider that
                    # was told returns what it had — but the turn was cut short, and says so.
                    outcome = "cancelled"
                self._meter.settle(
                    reserved, steps=steps_taken, cost_cents=spent_cents, cost_known=cost_known
                )
                turns = list(self._record.turns)
                turns[-1] = _replace_turn(turns[-1], outcome=outcome, text=said)
                # A turn that ended has no question open: whoever was asked was withdrawn from.
                still = tuple(q for q in self._record.pending if q.turn != turn_id)
                self._record = _replace(
                    self._record, turns=tuple(turns), pending=still, spent=self._spent()
                )
                await self._store.save(self._record)
                await self._remember_session()  # the provider's own id, for the next reopen

    def _context_for(self, turn_id: str) -> dict[str, JsonValue]:
        """What every judgement of this thread's runs sees (D82): the runtime's keys, the
        thread's attributes — the product's words — and the per-thread options."""
        return {
            "thread": self.id,
            "turn": turn_id,
            **({"mode": self._record.mode} if self._record.mode else {}),
            **self._record.attributes,
            **self._options,
        }

    async def _keep_pending(self, event: Event, turn_id: str, run_id: str) -> None:
        """The questions of this turn, on the record as they open and close (D80).

        A tool call the policy asks about is a child run parked on its `Ask`; the child's own
        `ApprovalRequested` names the run that parked, and the turn's — raised live from the
        offer with the component and inputs (BUG-026) — carries the handle the person answers.
        The agent's own question (`InputRequested`) is the child's alone: nothing parks, the
        answer is text. Either is off the record once its step is observed or refused."""
        pending = list(self._record.pending)
        changed = False
        if isinstance(event, ApprovalRequested) and event.run_id == run_id:
            parked_child = next(
                (
                    q.run_id
                    for q in reversed(self._parked)
                    if q.step == event.step and q.turn == turn_id
                ),
                "",
            )
            pending.append(
                PendingQuestion(
                    handle=event.handle,
                    turn=turn_id,
                    step=event.step,
                    question=event.question,
                    kind="approval",
                    component=event.component,
                    inputs=event.inputs,
                    run_id=parked_child,
                )
            )
            changed = True
        elif isinstance(event, ApprovalRequested):
            # A child's park: remember which run sleeps under this step, for the turn's question.
            self._parked.append(
                PendingQuestion(
                    handle=event.handle,
                    turn=turn_id,
                    step=event.step,
                    question=event.question,
                    run_id=event.run_id,
                )
            )
        elif isinstance(event, InputRequested):
            pending.append(
                PendingQuestion(
                    handle=event.handle,
                    turn=turn_id,
                    step=event.step,
                    question=event.question,
                    kind="input",
                )
            )
            changed = True
        elif isinstance(event, Observed | RefusedEvent) and any(
            q.step == event.step and q.turn == turn_id for q in pending
        ):
            pending = [q for q in pending if not (q.step == event.step and q.turn == turn_id)]
            changed = True
        if changed:
            self._record = _replace(self._record, pending=tuple(pending))
            await self._store.save(self._record)

    @property
    def pending(self) -> tuple[PendingQuestion, ...]:
        """The questions open on this thread (D80) — the ones a host that died left, until they
        are settled, and the ones the running turn is waiting on now."""
        return self._record.pending

    async def settle(self, handle: str, answer: Any) -> list[Event]:
        """Answer a question the last host left open (D80).

        An approval resumes the run that parked on it from the checkpointer — the act runs, or
        is refused, exactly where it stopped — and the record says what became of it. Either
        kind is folded ahead of the next prompt, so the agent learns what happened to the call
        it made: its transcript cannot be rewound, and a call it never heard back from would be
        one it might make again. The turn stays `parked`: it ended without the agent's answer.
        """
        question = next((q for q in self._record.pending if q.handle == handle), None)
        if question is None:
            raise KeyError(f"no question {handle!r} is pending on thread {self.id!r}")
        events: list[Event] = []
        if question.kind == "input":
            said = str(answer.get("text", answer) if isinstance(answer, dict) else answer)
            told = f"You asked the person {question.question!r}; they answered: {said}"
        elif not question.run_id:
            told = f"Your call {_call_line(question)} could not be settled: no run parked on it"
        else:
            events = await self._resume_parked(question, answer)
            observation = next(
                (
                    e.observation
                    for e in reversed(events)
                    if isinstance(e, Observed) and e.step == question.step
                ),
                None,
            )
            refusal = next(
                (
                    e.reason
                    for e in reversed(events)
                    if isinstance(e, RefusedEvent) and e.step == question.step
                ),
                None,
            )
            if isinstance(observation, Completed):
                told = (
                    f"Your call {_call_line(question)} from {question.turn} was approved by the "
                    f"person after the host restarted and produced: "
                    f"{json.dumps(observation.output)}"
                )
            elif observation is not None or refusal is not None:
                reason = refusal or getattr(observation, "reason", None) or "it failed"
                told = (
                    f"Your call {_call_line(question)} from {question.turn} was denied by the "
                    f"person after the host restarted: {reason}"
                )
            else:
                told = f"Your call {_call_line(question)} from {question.turn} did not settle"
        self._kept.append(told)
        turns = list(self._record.turns)
        for index, turn in enumerate(turns):
            if turn.id == question.turn:
                turns[index] = _replace_turn(
                    turn, text="\n\n".join(t for t in (turn.text, told) if t)
                )
        self._record = _replace(
            self._record,
            turns=tuple(turns),
            pending=tuple(q for q in self._record.pending if q.handle != handle),
        )
        await self._store.save(self._record)
        return events

    async def _resume_parked(self, question: PendingQuestion, answer: Any) -> list[Event]:
        """The child run that parked on the question, woken from the checkpointer with the
        answer — the same composition the offer built for the call, so the step is the same."""
        inputs = question.inputs if isinstance(question.inputs, dict) else {}
        composition = Composition(
            (
                Invoke(
                    id=question.step,
                    component=question.component or "",
                    inputs=tuple(Binding(name=k, value=v) for k, v in inputs.items()),
                ),
            )
        )
        left = self._meter.remaining().ceiling
        reserved = Ceiling(
            max_steps=min(2, max(left.max_steps, 1)),
            max_wall_seconds=left.max_wall_seconds,
            max_cost_cents=left.max_cost_cents,
        )
        lease = self._meter.carve(reserved)
        options = RunOptions(
            lease=lease,
            run_id=question.run_id,
            approvals=self._approvals,
            rules=self._rules,
            checkpointer=self._checkpointer,
            principal=self._record.principal or None,
            context=self._context_for(question.turn),
        )
        events: list[Event] = []
        steps_taken = 0
        try:
            async for event in resume_run(composition, answer, self._ports, options=options):
                events.append(event)
                if isinstance(event, Ended):
                    steps_taken = event.steps_taken
        finally:
            self._meter.settle(reserved, steps=steps_taken, cost_cents=0, cost_known=True)
        return events

    # ------------------------------------------------------------------ mode and options

    async def tools(self) -> list[Offered]:
        """What the agent is offered *now*: every registration the ports carry, each with the
        judgement the current mode gives its effects — `allow`, `ask`, or `refuse` (absent from
        the model's catalogue, `09` §4). The same registry a turn resolves against and the same
        policy, asked the same question, so what a host shows and what the run will do cannot
        drift. The turn's own step is not among them: it is the thread's, not a tool."""
        from shadow_hdk.kernel.ports import Ask, Refuse

        offered: list[Offered] = []
        for port in self._ports.components:
            try:
                registrations = await port.registrations()
            except Exception:  # noqa: BLE001 — a catalogue that will not answer offers nothing
                continue
            for registration in registrations:
                if registration.id == TURN:
                    continue
                attributes: dict[str, JsonValue] = {
                    **self._context_for("<catalogue>"),
                    "posture": registration.component.provenance.posture,
                    "component": registration.id,
                }
                judged = await self._ports.governance.judge(
                    registration.component.effects,
                    Context(
                        run_id="<catalogue>",
                        step="<catalogue>",
                        principal=self._record.principal or None,
                        attributes=attributes,
                    ),
                )
                kind = (
                    "refuse"
                    if isinstance(judged, Refuse)
                    else "ask"
                    if isinstance(judged, Ask)
                    else "allow"
                )
                offered.append(Offered(registration, kind, _source_of(port, registration)))
        return offered

    @property
    def workspace(self) -> Workspace:
        """The roots this thread works on (D76) — from the record, or the one root it names."""
        if self._record.roots:
            return Workspace(self._record.roots)
        return Workspace.of(self._record.root)

    @property
    def environment_mode(self) -> str:
        """What the sandbox enforces — the environment port's own mode — beside the policy's."""
        return _environment_mode_of(self._ports)

    async def add_root(self, name: str, path: Path | str) -> list[Event]:
        """A directory added while the thread runs (D76; Claude Code's `/add-dir`): the
        environment is re-opened on the new set — the confinement proof runs again — the record
        carries the roots, and `WorkspaceChanged` says so. Refused, unchanged, when the name is
        taken, the directory nests another root, or the sandbox cannot confine the new set."""
        grown = self.workspace.with_root(Root(name, str(path)))
        if self._turning.locked():
            raise RuntimeError("a root is added between turns, not during one")
        environment = _environment_of(self._ports)
        if environment is not None:
            await environment.reopen(workspace=grown)
        self._record = _replace(self._record, roots=grown.roots, root=str(grown.primary.path))
        await self._store.save(self._record)
        await self.registry.changed()  # the tools describe the roots; a resident agent re-lists
        await self._reopen_provider()  # and one that does not (BUG-032) is reopened, resumed
        return await self._announce(lambda **k: WorkspaceChanged(roots=grown.roots, **k))

    async def set_mode(self, mode_id: str) -> list[Event]:
        """Change the run's mode mid-thread (D64; ACP's `session/set_mode`).

        The policy the governance selects by changes at the next step; if the mode carries a
        different **behaviour**, the provider is reopened with it, resuming the thread; if it
        names a different **environment** mode (D76), the environment is re-opened — proven
        again — before the policy flips, so the page never says `full` over a sandbox that is
        not. The change is on the record (`ModeChanged`). An unknown mode raises and changes
        nothing; a sandbox that cannot make the environment mode true raises and changes nothing.
        """
        if self._modes is not None:
            find = getattr(self._modes, "find", None)
            spec = (
                await find(
                    mode_id,
                    principal=self._record.principal or None,
                    attributes=dict(self._record.attributes),
                )
                if find is not None
                else self._modes.get(mode_id)
            )
            if spec is None:
                raise KeyError(f"no mode {mode_id!r} in the registry for this thread")
            behaviour = spec.behaviour
        else:
            spec, behaviour = None, self._behaviour
        if mode_id == self._record.mode and behaviour == self._behaviour:
            return []
        wanted = getattr(spec, "environment", None) if spec is not None else None
        environment = _environment_of(self._ports)
        if environment is not None and wanted and wanted != environment.mode:
            await environment.reopen(mode=wanted)  # raises `CannotEnforce`: nothing changed
        self._record = _replace(
            self._record, mode=mode_id, environment=_environment_mode_of(self._ports)
        )
        await self._store.save(self._record)
        if spec is not None:
            self._behaviour = behaviour
        # The provider is reopened on its own session (D76): the catalogue it holds is the old
        # mode's, and a resident CLI was measured to keep it after `list_changed` (BUG-032) — a
        # fresh process re-lists, and `--resume` keeps its memory of the conversation.
        await self._reopen_provider()
        # The catalogue the provider holds is the old mode's (BUG-032): tell it to list again.
        await self.registry.changed()
        return await self._announce(lambda **k: ModeChanged(mode=mode_id, **k))

    async def _reopen_provider(self) -> None:
        if self._session is None:
            return
        await self._remember_session()
        await self._session.close()
        self._session = await self._open_provider()

    async def set_option(self, key: str, value: JsonValue) -> None:
        """A per-thread governance option, read at the next step's `Context` (ACP's
        `set_config_option`). Kept beside `mode` and passed into every turn's run."""
        self._options[key] = value

    async def _announce(self, make: Any) -> list[Event]:
        """One event on the thread's own short run, so the change is on the record even between
        turns — a mode changed while nobody was turning still happened."""
        options = RunOptions(
            lease=Lease(Ceiling(1, 1, 0), Floor(0)),
            run_id=self._ports.clock.new_id(),
            checkpointer=None,
        )
        from shadow_hdk.runtime.emit import Emitter

        assert options.run_id is not None
        emitter = Emitter(options.run_id, self._ports.clock, self._ports.observer)
        event = await emitter.emit(make)
        emitter.close()
        await emitter.drained()
        return [event]

    # ------------------------------------------------------------------ steer and interrupt

    async def steer(self, text: str) -> bool:
        """Say something to the agent while a turn runs (Codex's `turn/steer`, D63).

        `True` if the provider took it mid-turn. `False` if no turn is running or the provider
        cannot take it, in which case the text is kept and folded ahead of the next prompt — the
        record then shows it where it was actually heard.
        """
        session = self._session
        if session is not None and self._current is not None and await session.steer(text):
            return True
        self._kept.append(text)
        return False

    async def interrupt(self) -> None:
        """Stop the running turn (Codex's `turn/interrupt`): the provider is told if it can be,
        and the turn's run is cancelled either way, so the record ends `cancelled` and the lease
        settles. A provider that cannot be told is closed and reopened on the next turn."""
        session = self._session
        current = self._current
        if current is None:
            return
        told = session is not None and await session.interrupt()
        self._interrupted = True
        current.cancel("interrupted by the person")
        if not told and session is not None:
            await session.close()
            self._session = None

    # ------------------------------------------------------------------ fork and rollback

    async def fork(self) -> ThreadRecord:
        """A new thread with this one's turns, saying where it came from."""
        forked = _replace(
            self._record,
            id=self._ports.clock.new_id(),
            created_at=self._ports.clock.now(),
            forked_from=self._record.id,
            archived=False,
        )
        await self._store.create(forked)
        return forked

    async def rollback(self, *, to_turn: int) -> ThreadRecord:
        """A fork of the first `to_turn` turns. The provider's own transcript is not rewound —
        the new thread says how many turns it was seeded with, and a host seeds its first turn."""
        kept = self._record.turns[: max(0, to_turn)]
        rolled = _replace(
            self._record,
            id=self._ports.clock.new_id(),
            created_at=self._ports.clock.now(),
            forked_from=self._record.id,
            turns=kept,
            seeded_turns=len(kept),
            archived=False,
        )
        await self._store.create(rolled)
        return rolled


def _replace_turn(turn: TurnRecord, **changes: Any) -> TurnRecord:
    return replace(turn, **changes)


def _call_line(question: PendingQuestion) -> str:
    inputs = question.inputs if isinstance(question.inputs, dict) else {}
    return f"{question.component}({json.dumps(inputs)})"


__all__ = [
    "HOLD_SECONDS",
    "TURN",
    "TURN_EFFECTS",
    "InMemoryThreads",
    "Offered",
    "Thread",
    "ThreadHeld",
    "TurnRunning",
    "When",
]
