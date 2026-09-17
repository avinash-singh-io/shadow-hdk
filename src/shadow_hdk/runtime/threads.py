"""A thread of turns, each turn a run (D62): a `Conversation` with a record (D87).

The container every product has — thread (Codex, OpenAI, LangGraph), session (ACP, Claude Code)
— as the harness's own primitive: a `Conversation` (`runtime/conversation.py`: the provider
session, the served registry, the governed turns) plus what a record adds — a `ThreadRecord`
kept through a `ThreadStore` the host may implement over its own tables, one holder at a time
(D81), the questions a turn left open (D80, D88), what was spent (D84), and fork and rollback.

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
from collections.abc import AsyncIterator, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from pydantic import JsonValue

from shadow_hdk.kernel import (
    RECORD_VERSION,
    Ceiling,
    Completed,
    Lease,
    Observed,
    PendingQuestion,
    ThreadRecord,
    TurnRecord,
)
from shadow_hdk.kernel.capabilities import ExecutionRequirements, ExecutionSelection
from shadow_hdk.kernel.composition import Composition
from shadow_hdk.kernel.events import Event
from shadow_hdk.kernel.events import Refused as RefusedEvent
from shadow_hdk.kernel.planning import PlanLimits
from shadow_hdk.kernel.ports import AgentPort, ThreadStore
from shadow_hdk.kernel.workspace import Workspace
from shadow_hdk.runtime.approvals import Amend
from shadow_hdk.runtime.bindings import Ports
from shadow_hdk.runtime.conversation import (
    TURN,
    TURN_EFFECTS,
    Conversation,
    Offered,
    OnQuestion,
    TurnRunning,
    When,
    call_line,
    environment_mode_of,
)
from shadow_hdk.runtime.offer import InProcessOffer, Offer

HOLD_SECONDS = 30.0
"""How long a hold on a thread lives without renewal (D81): a host that died is out of the way
within half a minute; a live one renews every third of it."""


class ThreadHeld(RuntimeError):
    """The thread is open in another process (D81): the store says who holds it."""

    def __init__(self, thread_id: str, holder: str) -> None:
        super().__init__(f"thread {thread_id!r} is held by {holder!r}")
        self.thread_id = thread_id
        self.holder = holder


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
    """The conversation, kept: open once, turn many times, close — a `Conversation` and its
    record. Every method of the conversation is here too, with the record kept in step."""

    def __init__(
        self,
        record: ThreadRecord,
        conversation: Conversation,
        *,
        store: ThreadStore,
        holder: str = "",
        hold_seconds: float = HOLD_SECONDS,
    ) -> None:
        self._record = record
        self.conversation = conversation
        """The governed turns themselves (D87): a product that keeps its own record takes this
        alone."""
        self._store = store
        self.holder = holder
        """Who holds this thread (D81) — the process's name on the store's lease; empty when the
        thread was opened without one, which takes no hold."""
        self._hold_seconds = hold_seconds
        self._renewing: asyncio.Task[None] | None = None
        self.execution: ExecutionSelection | None = None
        """The capability pair accepted by a composing host, when it supplied one."""

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
        idle_seconds: float | None = None,
        requirements: ExecutionRequirements | None = None,
        plan_limits: PlanLimits | None = None,
    ) -> Thread:
        """Start a thread: the record created and held, the conversation opened on it.

        `budget` (D84) is this thread's own ceiling over `lease`, the host's default; what the
        thread spends is on its record after every turn, and a resume starts from it.

        `holder` names this process on the thread's hold (D81): taken here, renewed while the
        thread is open, released at close; `ThreadHeld` when another process has it.

        `principal` and `attributes` (D82) are who the thread is for and the product's words
        about it — on the record, and on every judgement's context from now on.

        `workspace` names the roots (D76) — one or many; `root` alone is the one-root workspace.
        The record carries both: `root` the primary for a one-root reader, `roots` the whole.

        `mode` is the **policy's** mode id — what `ModeGovernance` selects by at every step of
        every turn (the context key `mode`) — not the environment's.
        """
        workspace = workspace or Workspace.of(root)
        given = dict(attributes or {})
        record = ThreadRecord(
            id=thread_id or ports.clock.new_id(),
            root=str(workspace.primary.path),
            created_at=ports.clock.now(),
            mode=mode,
            provider=provider,
            roots=workspace.roots,
            environment=environment_mode_of(ports),
            principal=principal,
            attributes=given,
            budget=budget,
            requirements=requirements or ExecutionRequirements(),
            version=RECORD_VERSION,
        )
        thread = cls(record, _unopened(), store=store, holder=holder, hold_seconds=hold_seconds)
        await thread._take_hold(create=True)
        try:
            thread.conversation = await Conversation.open(
                agent=agent,
                ports=ports,
                lease=thread._own_lease(lease),
                registry=registry or InProcessOffer(name=name, withhold={TURN}),
                approvals=approvals,
                checkpointer=checkpointer,
                modes=modes,
                rules=rules,
                mode=mode,
                workspace=workspace,
                principal=principal,
                attributes=given,
                conversation_id=record.id,
                idle_seconds=idle_seconds,
                plan_limits=plan_limits,
            )
        except BaseException:
            await thread._let_go_of_hold()
            raise
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
        idle_seconds: float | None = None,
        plan_limits: PlanLimits | None = None,
    ) -> Thread:
        """Pick a thread up from its store: the provider reopened (with its own session id, when
        it kept one), the turns kept, the numbering continued, the meter from what the record
        says was spent (D84). `ThreadHeld` when another process holds it (D81) — nothing is read
        as left by a dead host while a live one has the thread."""
        record = await store.get(thread_id)
        if record is None:
            raise KeyError(f"no thread {thread_id!r} in the store")
        thread = cls(record, _unopened(), store=store, holder=holder, hold_seconds=hold_seconds)
        await thread._take_hold(create=False)
        try:
            if record.version < RECORD_VERSION:
                # A record from an older kit, written back in this one's shape (D93): every
                # field it lacked has its default, and the version now says so.
                thread._record = _replace(record, version=RECORD_VERSION)
                await store.save(thread._record)
            await thread._settle_what_the_last_host_left()
            thread.conversation = await Conversation.open(
                agent=agent,
                ports=ports,
                lease=thread._own_lease(lease),
                registry=registry or InProcessOffer(name=name, withhold={TURN}),
                approvals=approvals,
                checkpointer=checkpointer,
                modes=modes,
                rules=rules,
                mode=record.mode,
                workspace=thread.workspace,
                principal=record.principal,
                attributes=record.attributes,
                conversation_id=record.id,
                session_id=record.session_id,
                turns_taken=len(record.turns),
                spent=record.spent,
                idle_seconds=idle_seconds,
                plan_limits=plan_limits,
            )
        except BaseException:
            await thread._let_go_of_hold()
            raise
        return thread

    def _own_lease(self, default: Lease) -> Lease:
        """The thread's own budget over the host's default (D84)."""
        if self._record.budget is None:
            return default
        return Lease(self._record.budget, default.floor)

    async def _take_hold(self, *, create: bool) -> None:
        """The hold (D81) — before the record is created, so two processes cannot both make it —
        and the task that renews it every third of its life. A thread opened without a holder
        takes none."""
        if self.holder:
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
        if create:
            await self._store.create(self._record)

    async def _let_go_of_hold(self) -> None:
        if self._renewing is not None:
            self._renewing.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._renewing
            self._renewing = None
        if self.holder:
            await self._store.release(self.id, self.holder)

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

    async def close(self) -> None:
        await self.conversation.close()
        await self._remember_session()
        await self._let_go_of_hold()

    async def _remember_session(self) -> None:
        """The provider's own session id, off the conversation, onto the record — what a resume
        hands back (D76)."""
        found = self.conversation.session_id
        if found and found != self._record.session_id:
            self._record = _replace(self._record, session_id=found)
            await self._store.save(self._record)

    # ------------------------------------------------------------------ what it is

    @property
    def id(self) -> str:
        return self._record.id

    @property
    def record(self) -> ThreadRecord:
        return self._record

    @property
    def registry(self) -> Offer:
        return self.conversation.registry

    @property
    def ports(self) -> Ports:
        return self.conversation.ports

    def remaining(self) -> Lease:
        """What the thread may still spend across its turns: its budget less what is on the
        record (D84)."""
        return self.conversation.remaining()

    @property
    def turning(self) -> bool:
        """Whether a turn is running right now."""
        return self.conversation.turning

    @property
    def workspace(self) -> Workspace:
        """The roots this thread works on (D76) — from the record, or the one root it names."""
        if self._record.roots:
            return Workspace(self._record.roots)
        return Workspace.of(self._record.root)

    @property
    def environment_mode(self) -> str:
        """What the sandbox enforces — the environment port's own mode — beside the policy's."""
        return self.conversation.environment_mode

    @property
    def unmapped_behaviour(self) -> tuple[str, ...]:
        """The behaviour fields the current mode set that this provider could not take (ENH-020)
        — `system` or `model` on a CLI whose record maps no flag for them. Named at open, at
        resume and after every `set_mode`, so a host hides the control instead of showing one
        that does nothing."""
        return self.conversation.unmapped_behaviour

    @property
    def pending(self) -> tuple[PendingQuestion, ...]:
        """The questions open on this thread (D80, D88) — the ones a host that died or a turn
        that parked left, until they are settled, and the ones the running turn is waiting on."""
        return self._record.pending

    # ------------------------------------------------------------------ turning

    async def turn(
        self, text: str, *, when: When = "enqueue", on_question: OnQuestion = "wait"
    ) -> AsyncIterator[Event]:
        """One exchange, on the record: the turn written down before it runs, its questions as
        they open (D80), its outcome and what it spent when it ends (D84); a question the turn
        parked on purpose (D88) stays on the record for `settle`."""
        conversation = self.conversation

        async def began(turn: TurnRecord) -> None:
            self._record = _replace(self._record, turns=(*self._record.turns, turn))
            await self._store.save(self._record)

        try:
            async for event in conversation.turn(
                text, when=when, on_question=on_question, began=began
            ):
                await self._keep_pending(conversation)
                yield event
        finally:
            last = conversation.last
            # By its id, not the last row: a turn that waited its turn (D81) may have been
            # written down before this one's ending reached the record.
            index = next(
                (
                    i
                    for i, t in enumerate(self._record.turns)
                    if last is not None and t.id == last.id
                ),
                None,
            )
            if last is not None and index is not None:
                turns = list(self._record.turns)
                turns[index] = last.as_record()
                # A turn that ended has no question open but the ones it parked (D88): every
                # other was withdrawn from whoever was asked (D59).
                still = (
                    *(q for q in self._record.pending if q.turn != last.id),
                    *last.pending,
                )
                self._record = _replace(
                    self._record, turns=tuple(turns), pending=still, spent=last.spent
                )
                await self._store.save(self._record)
                await self._remember_session()

    async def _keep_pending(self, conversation: Conversation) -> None:
        """The running turn's open questions, on the record as they open and close (D80) — so a
        host that dies with a card up leaves them where the next host finds them."""
        running = self._record.turns[-1].id if self._record.turns else ""
        theirs = tuple(q for q in self._record.pending if q.turn != running)
        now = (*theirs, *conversation.open_questions)
        if now != self._record.pending:
            self._record = _replace(self._record, pending=now)
            await self._store.save(self._record)

    async def amend(self, handle: str, composition: Composition, answer: Any = None) -> list[Event]:
        """Continue a parked plan on a different composition (D116) — the person's answer to the
        question is `Amend`, carried to whoever holds the plan, which admits the amendment under
        the same limits, registry and policy as the original. Refused, the plan is as it was and
        the question stays open."""
        return await self.settle(handle, Amend(composition=composition, answer=answer))

    async def settle(self, handle: str, answer: Any) -> list[Event]:
        """Answer a question a turn left open (D80, D88).

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
            told = f"Your call {call_line(question)} could not be settled: no run parked on it"
        else:
            events = await self.conversation.resume_parked(question, answer)
            if isinstance(answer, Amend) and any(
                e.kind == "plan_refused" and getattr(e, "amendment", False) for e in events
            ):
                # The amendment was refused (D116): the plan is as it was, still waiting, and
                # the question stays on the record for the next answer.
                self.conversation.tell(
                    f"The person tried to amend your plan from {question.turn}; the amendment "
                    "was refused and your plan is as it was, still waiting."
                )
                self._record = _replace(self._record, spent=self.conversation.spent())
                await self._store.save(self._record)
                return events
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
                    f"Your call {call_line(question)} from {question.turn} was approved by the "
                    f"person and produced: {json.dumps(observation.output)}"
                )
            elif observation is not None or refusal is not None:
                reason = refusal or getattr(observation, "reason", None) or "it failed"
                told = (
                    f"Your call {call_line(question)} from {question.turn} was denied by the "
                    f"person: {reason}"
                )
            else:
                told = f"Your call {call_line(question)} from {question.turn} did not settle"
        self.conversation.tell(told)
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
            spent=self.conversation.spent(),
        )
        await self._store.save(self._record)
        return events

    # ------------------------------------------------------------------ mode and options

    async def tools(self) -> list[Offered]:
        """What the agent is offered *now*, each with the mode's judgement (D73)."""
        return await self.conversation.tools()

    async def add_root(self, name: str, path: Path | str) -> list[Event]:
        """A directory added while the thread runs (D76): the environment re-opened on the new
        set, the record carrying the roots, `WorkspaceChanged` on the record."""
        events = await self.conversation.add_root(name, path)
        grown = self.conversation.workspace
        self._record = _replace(self._record, roots=grown.roots, root=str(grown.primary.path))
        await self._store.save(self._record)
        return events

    async def set_mode(self, mode_id: str) -> list[Event]:
        """Change the run's mode mid-thread (D64): the policy, the environment it needs (D76),
        the provider's behaviour — and the record (`ModeChanged`)."""
        changed = await self.conversation.set_mode(mode_id)
        if changed is None:
            return []
        self._record = _replace(self._record, mode=changed.mode, environment=changed.environment)
        await self._store.save(self._record)
        return await self.conversation.announce_mode(changed.mode)

    async def set_option(self, key: str, value: JsonValue) -> None:
        """A per-thread governance option, read at the next step's `Context`."""
        await self.conversation.set_option(key, value)

    # ------------------------------------------------------------------ steer and interrupt

    async def steer(self, text: str) -> bool:
        """Say something to the agent while a turn runs (D63)."""
        return await self.conversation.steer(text)

    async def interrupt(self) -> None:
        """Stop the running turn (Codex's `turn/interrupt`)."""
        await self.conversation.interrupt()

    # ------------------------------------------------------------------ fork and rollback

    async def fork(self) -> ThreadRecord:
        """A new thread with this one's turns, saying where it came from."""
        clock = self.conversation.ports.clock
        forked = _replace(
            self._record,
            id=clock.new_id(),
            created_at=clock.now(),
            forked_from=self._record.id,
            archived=False,
        )
        await self._store.create(forked)
        return forked

    async def rollback(self, *, to_turn: int) -> ThreadRecord:
        """A fork of the first `to_turn` turns. The provider's own transcript is not rewound —
        the new thread says how many turns it was seeded with, and a host seeds its first turn."""
        clock = self.conversation.ports.clock
        kept = self._record.turns[: max(0, to_turn)]
        rolled = _replace(
            self._record,
            id=clock.new_id(),
            created_at=clock.now(),
            forked_from=self._record.id,
            turns=kept,
            seeded_turns=len(kept),
            archived=False,
        )
        await self._store.create(rolled)
        return rolled


def _unopened() -> Conversation:
    """A placeholder until the conversation is opened: reading it before is a mistake."""
    return _NotYet()  # type: ignore[return-value]


class _NotYet:
    def __getattr__(self, name: str) -> Any:
        raise RuntimeError("the thread's conversation is not open yet")


def _replace_turn(turn: TurnRecord, **changes: Any) -> TurnRecord:
    return replace(turn, **changes)


__all__ = [
    "HOLD_SECONDS",
    "TURN",
    "TURN_EFFECTS",
    "InMemoryThreads",
    "Offered",
    "OnQuestion",
    "Thread",
    "ThreadHeld",
    "TurnRunning",
    "When",
]
