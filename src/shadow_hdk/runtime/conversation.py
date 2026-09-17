"""The governed turn as a primitive (D87): one provider session, its turns as runs, no record.

A product that owns its conversation — its own messages, its own tables — takes this and keeps
the rest: `Conversation.open` serves the registry to the provider and opens its session;
`turn(text)` runs one turn as a run of one step whose component drives that session, the
provider's tool calls arriving through the registry as child runs (D62), every event yielded as
it happens; `last` is what the turn came to — for the product to fold into whatever it keeps.
`Thread` (`runtime/threads.py`) is a `Conversation` plus a record, a store and a hold.

**A park on purpose** (D88). A question the policy raises during a turn is put to the host's
`Questions` handle live (D58), because a provider blocked on its tool call cannot wait for a
process that has ended. A host that cannot answer now — a request that must return, a person
who is not there — answers `Parked`: the call is kept, the provider is told so and asked to
stop, the child run stays asleep in the checkpointer, and the turn ends `parked` with the
question on `last.pending` for whoever keeps the record to settle later (`Thread.settle`, D80).
`turn(on_question="park")` answers every question of the turn so, without a host in the loop.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
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
from shadow_hdk.kernel.planning import PlanLimits
from shadow_hdk.kernel.ports import (
    AgentPort,
    AgentSession,
    ComponentPort,
    Context,
)
from shadow_hdk.kernel.usage import Usage
from shadow_hdk.kernel.workspace import Root, Workspace
from shadow_hdk.runtime.approvals import Parked
from shadow_hdk.runtime.bindings import Ports, RunOptions, current_run
from shadow_hdk.runtime.cancel import Cancellation
from shadow_hdk.runtime.environment import Environment
from shadow_hdk.runtime.loop import resume as resume_run
from shadow_hdk.runtime.loop import run
from shadow_hdk.runtime.offer import InProcessOffer, Offer
from shadow_hdk.runtime.session import RESERVED_ATTRIBUTES, LeaseMeter

TURN = "turn"

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

When = Literal["enqueue", "reject", "interrupt"]
"""What a second turn does while one runs (D81): wait its turn, be refused, or stop the first."""

OnQuestion = Literal["wait", "park"]
"""What a turn does with a question the policy raises (D88): `wait` puts it to the host's
handle live and waits; `park` keeps it for later and ends the turn `parked`."""


class TurnRunning(RuntimeError):
    """A turn is running and the caller asked not to wait (`when="reject"`, D81)."""

    def __init__(self, thread_id: str, turn_id: str) -> None:
        super().__init__(f"thread {thread_id!r} is running {turn_id}")
        self.thread_id = thread_id
        self.turn_id = turn_id


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


@dataclass(frozen=True)
class Turned:
    """What a turn came to (D87): the turn as a record would remember it, what it spent, and the
    questions it left open — parked on purpose (D88) for whoever keeps the record to settle."""

    id: str
    run_id: str
    prompt: str
    at: str
    outcome: str
    text: str
    spent: Spent
    pending: tuple[PendingQuestion, ...] = ()

    def as_record(self) -> TurnRecord:
        return TurnRecord(
            id=self.id,
            run_id=self.run_id,
            prompt=self.prompt,
            at=self.at,
            outcome=self.outcome,  # type: ignore[arg-type]
            text=self.text,
        )


@dataclass(frozen=True)
class Changed:
    """What `set_mode` changed: the mode id and the environment mode now enforced."""

    mode: str
    environment: str


def _unwrapped(port: Any) -> Any:
    inner = port
    while (wrapped := getattr(inner, "_inner", None)) is not None:  # `Switched`, or the next
        inner = wrapped
    return inner


def environment_of(ports: Ports) -> Environment | None:
    """The environment among the ports, if one is there — the runtime's own base class, so no
    adapter is named here; a host that composes something else gets `None` and no re-opening."""
    for port in ports.components:
        inner = _unwrapped(port)
        if isinstance(inner, Environment):
            return inner
    return None


def environment_mode_of(ports: Ports) -> str:
    environment = environment_of(ports)
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


def spent_of(meter: LeaseMeter) -> Spent:
    """The meter's counters, in the record's words (D84)."""
    counted = meter.spent()
    return Spent(
        steps=int(counted["steps"]),
        seconds=float(counted["elapsed_seconds"]),
        cents=int(counted["cost_cents"]),
        unpriced=bool(counted["unpriced"]),
        input_tokens=int(counted["input_tokens"]),
        output_tokens=int(counted["output_tokens"]),
        unmetered=bool(counted["unmetered"]),
    )


def call_line(question: PendingQuestion) -> str:
    inputs = question.inputs if isinstance(question.inputs, dict) else {}
    return f"{question.component}({json.dumps(inputs)})"


class Conversation:
    """One provider session, its turns governed and streamed, nothing kept but the last turn."""

    def __init__(
        self,
        *,
        conversation_id: str,
        agent: AgentPort,
        ports: Ports,
        lease: Lease,
        registry: Offer,
        workspace: Workspace,
        approvals: Any = None,
        checkpointer: Any = None,
        modes: Any = None,
        rules: Any = None,
        mode: str = "",
        principal: str = "",
        attributes: Mapping[str, JsonValue] | None = None,
        session_id: str = "",
        turns_taken: int = 0,
        spent: Spent | None = None,
        idle_seconds: float | None = None,
        plan_limits: PlanLimits | None = None,
    ) -> None:
        self.id = conversation_id
        self._idle_seconds = idle_seconds
        #: The host's plan limits (D109), met with the mode's at every turn.
        self._plan_limits = plan_limits
        self._mode_plan: PlanLimits | None = None
        """After this long without a turn the provider's session is closed (D94) — the
        conversation stays open; the next turn reopens the provider on its session id. `None`
        keeps the provider for the conversation's whole life."""
        self._idling: asyncio.Task[None] | None = None
        self.mode = mode
        """The policy's mode id — what the governance selects by (the context key `mode`)."""
        self.principal = principal
        self.attributes: dict[str, JsonValue] = dict(attributes or {})
        self.workspace = workspace
        self.session_id = session_id
        """The provider's own session id, when it has one — what a reopen hands back (D76)."""
        self.turns_taken = turns_taken
        self.last: Turned | None = None
        """What the last turn came to; `None` before the first."""
        self._agent = agent
        self._ports = ports
        self._rules = rules
        self._meter = LeaseMeter(lease, ports.clock)
        if spent is not None:
            self._meter.restore(
                {
                    "steps": spent.steps,
                    "cost_cents": spent.cents,
                    "unpriced": 1 if spent.unpriced else 0,
                    "elapsed_seconds": spent.seconds,
                    "input_tokens": spent.input_tokens,
                    "output_tokens": spent.output_tokens,
                    "unmetered": 1 if spent.unmetered else 0,
                }
            )
        # **The clock runs only in a turn** (D90): a conversation sitting open spends nothing.
        self._meter.pause()
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
        modes adapter, so a host hands in its own. `None` means the conversation has no
        behaviours to apply and `set_mode` only flips the policy the governance selects by."""
        self._behaviour: Any = None
        self._options: dict[str, JsonValue] = {}
        self._current: Cancellation | None = None
        """The running turn's handle to stop it (D15), while one runs."""
        self._interrupted = False
        self._kept: list[str] = []
        """Steering the provider could not take mid-turn, and what became of a call settled
        after its turn ended (D80, D88): folded into the next prompt."""
        self._running_turn: str = ""
        self._parked_children: list[PendingQuestion] = []
        """Children parked during the running turn, by step — so a question can name the run
        that sleeps on it."""
        self._open_questions: list[PendingQuestion] = []
        """The running turn's questions, as they open and close."""

    # ------------------------------------------------------------------ opening and closing

    @classmethod
    async def open(
        cls,
        *,
        agent: AgentPort,
        ports: Ports,
        root: Path | str | None = None,
        lease: Lease,
        registry: Offer | None = None,
        name: str = "tools",
        approvals: Any = None,
        checkpointer: Any = None,
        modes: Any = None,
        rules: Any = None,
        mode: str = "",
        workspace: Workspace | None = None,
        principal: str = "",
        attributes: Mapping[str, JsonValue] | None = None,
        conversation_id: str | None = None,
        session_id: str = "",
        turns_taken: int = 0,
        spent: Spent | None = None,
        idle_seconds: float | None = None,
        plan_limits: PlanLimits | None = None,
    ) -> Conversation:
        """Serve the registry, open the provider on it. `workspace` names the roots (D76) — one
        or many; `root` alone is the one-root workspace. `mode` is the policy's mode id; when
        `modes` is given and knows it, its behaviour is the provider's. `principal` and
        `attributes` (D82) are on every judgement's context; a reserved attribute name is
        refused. `session_id`, `turns_taken` and `spent` are what a record hands back when the
        conversation is picked up rather than started. `idle_seconds` (D94) closes the provider
        after that long without a turn; the next turn reopens it on its session id."""
        if workspace is None:
            if root is None:
                raise ValueError("a conversation needs a root or a workspace")
            workspace = Workspace.of(root)
        given = dict(attributes or {})
        if taken := sorted(set(given) & RESERVED_ATTRIBUTES):
            raise ValueError(f"attributes {taken} are the runtime's own; choose other names")
        conversation = cls(
            conversation_id=conversation_id or ports.clock.new_id(),
            agent=agent,
            ports=ports,
            lease=lease,
            registry=registry or InProcessOffer(name=name, withhold={TURN}),
            workspace=workspace,
            approvals=approvals,
            checkpointer=checkpointer,
            modes=modes,
            rules=rules,
            mode=mode,
            principal=principal,
            attributes=given,
            session_id=session_id,
            turns_taken=turns_taken,
            spent=spent,
            idle_seconds=idle_seconds,
            plan_limits=plan_limits,
        )
        if modes is not None and (spec := modes.get(mode)) is not None:
            conversation._behaviour = spec.behaviour
            conversation._mode_plan = getattr(spec, "plan", None)
        await conversation._start()
        conversation._idle_from_now()
        return conversation

    def _idle_from_now(self) -> None:
        """Start the idle clock (D94): when it runs out with no turn begun, the provider's
        session is closed and reopened on its id at the next turn. Restarted after every turn;
        stopped while one runs."""
        self._stop_idling()
        if self._idle_seconds is None:
            return

        async def idling() -> None:
            await asyncio.sleep(self._idle_seconds or 0)
            if self._session is not None and self._current is None:
                self._remember_session()
                await self._session.close()
                self._session = None

        self._idling = asyncio.create_task(idling())

    def _stop_idling(self) -> None:
        if self._idling is not None:
            self._idling.cancel()
            self._idling = None

    async def _start(self) -> None:
        # **The offer lives in a task of its own.** A socket offer is an anyio listener and a task
        # group, and those are bound to the task that entered them; `open` and `close` are called
        # from whichever task a host happens to be on — over the wire, two different handler
        # tasks — and exiting a cancel scope from another task is an error. So one task holds the
        # offer open for the conversation's lifetime and is told when to let go. Measured behind
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
        """The provider's session, opened on the tools, workspace and behaviour — and resumed on
        its own session id when there is one (D76), so a reopen after a mode change, a root
        added or a pick-up keeps the agent's memory of the conversation. `resume` is passed only
        when there is one, so an opener without the keyword (a test double, an adapter that
        predates it) is still called the way it always was."""
        extra: dict[str, Any] = {}
        if self.session_id:
            extra["resume"] = self.session_id
        return await self._agent.open(
            tools=tuple(self._sources),
            workspace=str(self.workspace.primary.path),
            behaviour=self._behaviour,
            **extra,
        )

    def _remember_session(self) -> bool:
        """The provider's own session id, off the session (D76). `True` when it changed."""
        found = getattr(self._session, "session_id", None) if self._session is not None else None
        if isinstance(found, str) and found and found != self.session_id:
            self.session_id = found
            return True
        return False

    async def _reopen_provider(self) -> None:
        if self._session is None:
            return
        self._remember_session()
        await self._session.close()
        self._session = await self._open_provider()

    async def close(self) -> None:
        self._stop_idling()
        if self._session is not None:
            self._remember_session()
            await self._session.close()
            self._session = None
        holder = self._holder
        if holder is not None:
            self._let_go.set()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await holder
            self._holder = None

    @property
    def closed(self) -> bool:
        return self._holder is None

    @property
    def ports(self) -> Ports:
        """The ports every turn runs on — what the host composed, observer included."""
        return self._ports

    # ------------------------------------------------------------------ what it is

    @property
    def plan_limits(self) -> PlanLimits | None:
        """How much plan a turn admits now (D109): the host's limits met with the current mode's —
        read at every turn, so `set_mode` changes what the next plan may be, live."""
        host, mode = self._plan_limits, self._mode_plan
        if host is None:
            return mode
        if mode is None:
            return host
        return host.meet(mode)

    def remaining(self) -> Lease:
        """What may still be spent across the turns: the lease less what was spent (D84)."""
        return self._meter.remaining()

    def spent(self) -> Spent:
        return spent_of(self._meter)

    @property
    def turning(self) -> bool:
        """Whether a turn is running right now."""
        return self._current is not None

    @property
    def environment_mode(self) -> str:
        """What the sandbox enforces — the environment port's own mode — beside the policy's."""
        return environment_mode_of(self._ports)

    def context_for(self, turn_id: str) -> dict[str, JsonValue]:
        """What every judgement of this conversation's runs sees (D82): the runtime's keys, the
        attributes — the product's words — and the per-conversation options."""
        return {
            "thread": self.id,
            "turn": turn_id,
            **({"mode": self.mode} if self.mode else {}),
            **self.attributes,
            **self._options,
        }

    def tell(self, text: str) -> None:
        """Something the provider is told ahead of its next prompt: what became of a call it
        made and never heard back from (D80, D88), or steering it could not take mid-turn."""
        self._kept.append(text)

    # ------------------------------------------------------------------ turning

    async def turn(
        self,
        text: str,
        *,
        when: When = "enqueue",
        on_question: OnQuestion = "wait",
        began: Any = None,
    ) -> AsyncIterator[Event]:
        """One exchange: the person's text in, the run's events out, `last` set at the end.

        The turn is a run of one step, `turn-N`, whose component drives the provider session;
        the provider's tool calls arrive through the registry, attached to this run for the
        turn's duration, and are child runs under the step — so a host folds them under the
        turn's item (D62).

        `when` says what this turn does while another runs (D81): `enqueue` waits its turn (the
        default); `reject` raises `TurnRunning`; `interrupt` stops the running turn — it ends
        `cancelled` — and starts this one. `on_question` (D88): `wait` puts a question to the
        host's handle and waits; `park` keeps it and ends the turn `parked`. `began`, when
        given, is awaited with the turn's `TurnRecord` once the turn has the lock and a run id —
        a keeper of records writes the turn down there, before anything runs.
        """
        if when not in ("enqueue", "reject", "interrupt"):
            raise ValueError(f"when={when!r}: one of enqueue, reject, interrupt")
        if on_question not in ("wait", "park"):
            raise ValueError(f"on_question={on_question!r}: one of wait, park")
        if self._holder is None:
            raise RuntimeError("the conversation is closed")
        if self._turning.locked():
            if when == "reject":
                raise TurnRunning(self.id, self._running_turn)
            if when == "interrupt":
                await self.interrupt()
        self._stop_idling()
        if self._session is None:
            # A provider closed for idling (D94), or interrupted and not told: a turn reopens it.
            self._session = await self._open_provider()
        async with self._turning:
            # What is left is read here, under the lock: a running turn reserves everything the
            # conversation has, and a turn that waited its turn (D81) reads the meter after that
            # reservation settled — read before, it saw nothing left and was refused.
            if (left := self._meter.remaining().ceiling).max_steps <= 0:
                raise RuntimeError("the thread has no steps left")
            if self._kept:
                text = "\n\n".join((*self._kept, text))
                self._kept.clear()
            number = self.turns_taken + 1
            turn_id = f"{TURN}-{number}"
            run_id = self._ports.clock.new_id()
            at = self._ports.clock.now()
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
            self._running_turn = turn_id
            self._parked_children = []
            self._open_questions = []
            self.turns_taken = number
            unreported: list[bool] = []

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
                else:
                    # A turn the provider said nothing about (D90): the count is a floor.
                    unreported.append(True)
                return Completed(output)

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
                principal=self.principal or None,
                context=self.context_for(turn_id),
                plan_limits=self.plan_limits,
            )
            if began is not None:
                await began(TurnRecord(id=turn_id, run_id=run_id, prompt=text, at=at))
            outcome: str = "completed"
            said = ""
            steps_taken = 0
            spent_cents = 0
            cost_known = True
            tokens_in = 0
            tokens_out = 0
            tokens_known = True
            self._meter.unpause()
            try:
                async for event in run(plan, ports, options=options):
                    await self._watch_questions(event, turn_id, run_id, on_question)
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
                    if event.kind == "usage":
                        # The turn's own calls and its children's alike (D90): every call the
                        # turn caused is the turn's to count.
                        usage = getattr(event, "usage", None)
                        if usage is not None and event.run_id == run_id:
                            if usage.cost_cents is not None:
                                spent_cents += usage.cost_cents
                            else:
                                cost_known = False
                        if usage is not None:
                            if usage.input_tokens is None and usage.output_tokens is None:
                                tokens_known = False
                            else:
                                tokens_in += usage.input_tokens or 0
                                tokens_out += usage.output_tokens or 0
                    yield event
            finally:
                self._current = None
                self._running_turn = ""
                if self._interrupted:
                    # The person stopped it. The run may still say `completed` — a provider that
                    # was told returns what it had — but the turn was cut short, and says so.
                    outcome = "cancelled"
                self._meter.settle(
                    reserved,
                    steps=steps_taken,
                    cost_cents=spent_cents,
                    cost_known=cost_known,
                    tokens=(tokens_in, tokens_out),
                    tokens_known=tokens_known and not unreported,
                )
                self._meter.pause()
                self._idle_from_now()
                # **Kept, or withdrawn** (D88). A question answered `Parked` stays open on the
                # turn — the run that sleeps on it is in the checkpointer; every other question
                # still open when the turn ended was withdrawn from whoever was asked (D59).
                parked: set[str] = getattr(self._approvals, "parked", set())
                kept = tuple(q for q in self._open_questions if q.handle in parked)
                if kept and outcome == "completed":
                    outcome = "parked"
                self._remember_session()  # the provider's own id, for the next reopen
                self.last = Turned(
                    id=turn_id,
                    run_id=run_id,
                    prompt=text,
                    at=at,
                    outcome=outcome,
                    text=said,
                    spent=self.spent(),
                    pending=kept,
                )

    @property
    def open_questions(self) -> tuple[PendingQuestion, ...]:
        """The running turn's questions nobody has answered yet — for a keeper of records to
        write down as they open (D80), so a crash finds them."""
        return tuple(self._open_questions)

    async def _watch_questions(
        self, event: Event, turn_id: str, run_id: str, on_question: OnQuestion
    ) -> None:
        """The turn's questions as they open and close (D80, D88).

        A tool call the policy asks about is a child run parked on its `Ask`; the child's own
        `ApprovalRequested` names the run that parked, and the turn's — raised live from the
        offer with the component and inputs (BUG-026) — carries the handle the person answers.
        The agent's own question (`InputRequested`) is the child's alone: nothing parks, the
        answer is text. Either closes once its step is observed or refused. With
        `on_question="park"` the turn answers each itself, `Parked`."""
        if isinstance(event, ApprovalRequested) and event.run_id == run_id:
            parked_child = next(
                (
                    q.run_id
                    for q in reversed(self._parked_children)
                    if q.step == event.step and q.turn == turn_id
                ),
                "",
            )
            question = PendingQuestion(
                handle=event.handle,
                turn=turn_id,
                step=event.step,
                question=event.question,
                kind="approval",
                component=event.component,
                inputs=event.inputs,
                run_id=parked_child,
            )
            self._open_questions.append(question)
            if on_question == "park":
                self._park(question)
        elif isinstance(event, ApprovalRequested):
            # A child's park: remember which run sleeps under this step, for the turn's question.
            self._parked_children.append(
                PendingQuestion(
                    handle=event.handle,
                    turn=turn_id,
                    step=event.step,
                    question=event.question,
                    run_id=event.run_id,
                )
            )
        elif isinstance(event, InputRequested):
            question = PendingQuestion(
                handle=event.handle,
                turn=turn_id,
                step=event.step,
                question=event.question,
                kind="input",
            )
            self._open_questions.append(question)
            if on_question == "park":
                self._park(question)
        elif isinstance(event, Observed | RefusedEvent):
            # The step answered, so its questions are closed — except one answered `Parked`
            # (D88): the step's refusal is the agent being told "not now", and the question
            # stays open for whoever keeps the record (BUG-044: the agent's own question).
            parked: set[str] = getattr(self._approvals, "parked", set())
            self._open_questions = [
                q
                for q in self._open_questions
                if not (q.step == event.step and q.turn == turn_id) or q.handle in parked
            ]

    def _park(self, question: PendingQuestion) -> None:
        """Answer the host's handle `Parked` for this question (D88): kept, not put to anyone.
        Without a handle there is nobody to keep it for; the refusal stands as it always did."""
        if self._approvals is not None:
            self._approvals.answer(question.handle, Parked())

    async def resume_parked(
        self,
        question: PendingQuestion,
        answer: Any,
        *,
        composition: Composition | None = None,
    ) -> list[Event]:
        """The child run that parked on the question, woken from the checkpointer with the
        answer — on the composition it parked with (D116), read from the checkpoint; or, for an
        **amendment**, on the one handed in, which the runtime admits before continuing."""
        from shadow_hdk.runtime.loop import parked_composition

        if composition is None:
            composition = await parked_composition(self._checkpointer, question.run_id)
        if composition is None:
            # Nothing carried — the shape the offer built for the call, as before.
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
        # **What the thread has left, not a guess at the call** (BUG-024's rule, the other way
        # round): the run being woken may hold a plan of many steps below the one step this
        # composition names, and a carve sized for one call starved that plan at its first step.
        # Admission bounds the plan; the meter settles what is not spent back to the thread.
        reserved = Ceiling(
            max_steps=max(left.max_steps, 1),
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
            principal=self.principal or None,
            context=self.context_for(question.turn),
            plan_limits=self.plan_limits,
        )
        events: list[Event] = []
        steps_taken = 0
        self._meter.unpause()
        try:
            async for event in resume_run(composition, answer, self._ports, options=options):
                events.append(event)
                if isinstance(event, Ended):
                    steps_taken = event.steps_taken
        finally:
            self._meter.settle(reserved, steps=steps_taken, cost_cents=0, cost_known=True)
            self._meter.pause()
        return events

    # ------------------------------------------------------------------ mode and options

    async def tools(self) -> list[Offered]:
        """What the agent is offered *now*: every registration the ports carry, each with the
        judgement the current mode gives its effects — `allow`, `ask`, or `refuse` (absent from
        the model's catalogue, `09` §4). The same registry a turn resolves against and the same
        policy, asked the same question, so what a host shows and what the run will do cannot
        drift. The turn's own step is not among them: it is the conversation's, not a tool."""
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
                    **self.context_for("<catalogue>"),
                    "posture": registration.component.provenance.posture,
                    "component": registration.id,
                }
                judged = await self._ports.governance.judge(
                    registration.component.effects,
                    Context(
                        run_id="<catalogue>",
                        step="<catalogue>",
                        principal=self.principal or None,
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

    async def add_root(self, name: str, path: Path | str) -> list[Event]:
        """A directory added while the conversation runs (D76; Claude Code's `/add-dir`): the
        environment is re-opened on the new set — the confinement proof runs again — and
        `WorkspaceChanged` says so. Refused, unchanged, when the name is taken, the directory
        nests another root, or the sandbox cannot confine the new set."""
        grown = self.workspace.with_root(Root(name, str(path)))
        if self._turning.locked():
            raise RuntimeError("a root is added between turns, not during one")
        environment = environment_of(self._ports)
        if environment is not None:
            await environment.reopen(workspace=grown)
        self.workspace = grown
        await self.registry.changed()  # the tools describe the roots; a resident agent re-lists
        await self._reopen_provider()  # and one that does not (BUG-032) is reopened, resumed
        return await self.announce(lambda **k: WorkspaceChanged(roots=grown.roots, **k))

    async def set_mode(self, mode_id: str) -> Changed | None:
        """Change the run's mode mid-conversation (D64; ACP's `session/set_mode`).

        The policy the governance selects by changes at the next step; if the mode carries a
        different **behaviour**, the provider is reopened with it, resuming the conversation;
        if it names a different **environment** mode (D76), the environment is re-opened —
        proven again — before the policy flips, so a page never says `full` over a sandbox that
        is not. `None` when nothing changed. An unknown mode, or one out of the principal's
        scope (D82), raises and changes nothing; a sandbox that cannot make the environment
        mode true raises and changes nothing.
        """
        if self._modes is not None:
            find = getattr(self._modes, "find", None)
            spec = (
                await find(
                    mode_id, principal=self.principal or None, attributes=dict(self.attributes)
                )
                if find is not None
                else self._modes.get(mode_id)
            )
            if spec is None:
                raise KeyError(f"no mode {mode_id!r} in the registry for this thread")
            behaviour = spec.behaviour
        else:
            spec, behaviour = None, self._behaviour
        if mode_id == self.mode and behaviour == self._behaviour:
            return None
        wanted = getattr(spec, "environment", None) if spec is not None else None
        environment = environment_of(self._ports)
        if environment is not None and wanted and wanted != environment.mode:
            await environment.reopen(mode=wanted)  # raises `CannotEnforce`: nothing changed
        self.mode = mode_id
        if spec is not None:
            self._behaviour = behaviour
            self._mode_plan = getattr(spec, "plan", None)
        # The provider is reopened on its own session (D76): the catalogue it holds is the old
        # mode's, and a resident CLI was measured to keep it after `list_changed` (BUG-032) — a
        # fresh process re-lists, and `--resume` keeps its memory of the conversation.
        await self._reopen_provider()
        # The catalogue the provider holds is the old mode's (BUG-032): tell it to list again.
        await self.registry.changed()
        return Changed(mode=mode_id, environment=self.environment_mode)

    async def set_option(self, key: str, value: JsonValue) -> None:
        """A per-conversation governance option, read at the next step's `Context` (ACP's
        `set_config_option`). Kept beside `mode` and passed into every turn's run."""
        self._options[key] = value

    async def announce(self, make: Any) -> list[Event]:
        """One event on the conversation's own short run, so a change is on the record even
        between turns — a mode changed while nobody was turning still happened."""
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

    async def announce_mode(self, mode_id: str) -> list[Event]:
        return await self.announce(lambda **k: ModeChanged(mode=mode_id, **k))

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
        and the turn's run is cancelled either way, so the turn ends `cancelled` and the lease
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


__all__ = [
    "TURN",
    "TURN_EFFECTS",
    "Changed",
    "Conversation",
    "Offered",
    "OnQuestion",
    "TurnRunning",
    "Turned",
    "When",
    "call_line",
    "environment_mode_of",
    "environment_of",
    "spent_of",
]
