"""Spawn, send, release — the three operations `09` §6 names, over parked runs (D16).

A held child is **a parked run, not a resident object**. `spawn` starts it and lets it go until it
parks or ends; `send` is a `resume` with the message as the answer; `release` cancels it and settles
its lease. `09` §6 says the runtime owns nothing durable and is disposable by design, and a resident
child with an inbox is durable runtime state under another name — it would need a lifetime, its own
supervision, and an answer for what happens when the host restarts. A checkpoint answers all three.

What this registry holds is the little a resume needs and a checkpoint cannot supply: the
composition, because `resume` takes the plan back in (`09` §6); the checkpointer the child parked
with; and the child's own `Cancellation`, which is what makes *branch* granularity mean anything —
releasing one child says nothing about its siblings.

**Holding is not a reservation.** A parked run settles what it did not spend back to its parent on
the way out, so what a parent gives up by holding a child is the steps that child actually took.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from pydantic import JsonValue

from shadow_hdk.kernel.composition import Composition
from shadow_hdk.kernel.contracts import dump
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import Ended, Event, PlanAdmitted
from shadow_hdk.kernel.events import PlanRefused as PlanRefusedEvent
from shadow_hdk.kernel.leases import Ceiling
from shadow_hdk.kernel.planning import (
    UNBOUNDED,
    Admitted,
    PlanLimits,
    PlanMismatch,
    PlanRefused,
    admit,
    composition_digest,
    leaves_of,
)
from shadow_hdk.kernel.ports import Allow, Ask, Context, GovernancePort, Judgement, Refuse
from shadow_hdk.runtime.cancel import Cancellation

if TYPE_CHECKING:
    from shadow_hdk.runtime.bindings import RunContext

RELEASED = "released"
"""What a child is sent when it is let go. Never read — see `Children.release`."""


class PlanNotAdmitted(Exception):
    """A plan refused before it compiled (D108). Whoever proposed it is told every mismatch and
    decides what to do — re-propose, split, ask, or stop; the runtime never trims a proposal
    (D111). An ordinary exception on purpose: it is an outcome for the caller, not a stop."""

    def __init__(self, refusal: PlanRefused, *, amendment: bool = False) -> None:
        self.refusal = refusal
        self.amendment = amendment
        super().__init__(readable_refusal(refusal))


def readable_refusal(refusal: PlanRefused) -> str:
    """Every mismatch in one line a model or a person can act on."""
    parts = []
    for m in refusal.mismatches:
        where = f" at {m.step}" if m.step else ""
        if m.axis == "component":
            # The words a model has always read for this (`no component registered as …`), so
            # a one-call plan naming an unknown tool is told what it was told before.
            parts.append(f"{m.axis}{where}: no component registered as {m.found!r}")
        else:
            parts.append(f"{m.axis}{where}: required {m.required}, found {m.found}")
    return "that plan was refused — " + "; ".join(parts)


@dataclass(frozen=True)
class HeldChild:
    """What a parent keeps about a held child.

    Four of these six cross a checkpoint as JSON (D37); the checkpointer and the cancellation are
    objects and cannot, which is why `shares_the_checkpointer` is recorded — a child that shared
    its parent's is reachable again after a park, and one that did not is reported as lost rather
    than replaced by a duplicate.
    """

    handle: str
    run_id: str
    composition: Composition
    ceiling: Ceiling
    checkpointer: Any
    cancellation: Cancellation
    shares_the_checkpointer: bool = False


class Narrowed:
    """The deployment's policy, then a role's ceiling. Both have to say yes (D51).

    Order matters for the *reason*, not the outcome. The deployment is asked first so that when the
    house refuses, the house's own words are what a person reads — a team debugging its pattern
    should not be sent to the pattern file over a rule it does not control.

    Lives in the runtime, below every adapter, so a child spawned across a wire can be narrowed by
    a ceiling that crossed as data. It was the agent adapter's `_Bounded` before Phase 23.
    """

    def __init__(self, inner: GovernancePort, ceiling: EffectProfile, name: str) -> None:
        self._inner, self._ceiling, self._name = inner, ceiling, name

    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        judgement = await self._inner.judge(effects, context)
        if isinstance(judgement, Refuse):
            return judgement
        if not effects.narrows(self._ceiling):
            return Refuse(f"the pattern {self._name!r} does not permit this")
        return judgement


class Children:
    """A run's children, and the three things a parent may do with one."""

    def __init__(self, context: RunContext) -> None:
        self._context = context
        self._held: dict[str, HeldChild] = {}
        #: Plans admitted by a step to run after it closes (D112), in order.
        self._deferred: list[
            tuple[Composition, Ceiling, EffectProfile | None, str, PlanLimits]
        ] = []
        self._released: set[str] = set()
        self._lost: dict[str, str] = {}

    @property
    def held(self) -> tuple[str, ...]:
        """The handles of children parked and waiting. In the order they were spawned."""
        return tuple(self._held)

    @property
    def lost(self) -> tuple[str, ...]:
        """Children this run was holding before it parked and cannot reach again (D37).

        A parent that came back to an empty hand used to start over and quietly make a second
        child, leaving the first parked forever. A handle here says *this one is gone*, which is a
        different thing from *I never had one*, and `why_lost` says which.
        """
        return tuple(self._lost)

    def why_lost(self, handle: str) -> str:
        return self._lost[handle]

    def __contains__(self, handle: str) -> bool:
        return handle in self._held

    # ------------------------------------------------------------------ across a park (D37)

    def record(self) -> dict[str, JsonValue]:
        """What this run is holding, as JSON for the checkpoint (D19).

        A released handle is kept as `None` rather than dropped, so two branches of a `FanOut`
        merge to the same answer whichever arrives first: *held* and *let go* are both statements,
        and only *never mentioned* is silence.
        """

        written: dict[str, JsonValue] = {handle: None for handle in self._released}
        for handle, child in self._held.items():
            written[handle] = {
                "run_id": child.run_id,
                "composition": json.loads(dump(child.composition, Composition)),
                "ceiling": json.loads(dump(child.ceiling, Ceiling)),
                "shares_the_checkpointer": child.shares_the_checkpointer,
            }
        return written

    def restore(self, records: Mapping[str, JsonValue], checkpointer: Any) -> None:
        """Rebuild what the parent was holding when it parked (D37).

        A child that shared this run's checkpointer is reachable again, because that checkpointer
        is the one the host just handed back. One spawned with a checkpointer of its own is not:
        the object cannot cross a checkpoint, and inventing a fresh one would produce a handle
        that answers nothing. That child is **named in `lost`**, never silently dropped.
        """
        from shadow_hdk.kernel.contracts import load

        for handle, record in records.items():
            if record is None:
                self._released.add(handle)
                continue
            if not isinstance(record, dict):  # pragma: no cover — a checkpoint we did not write
                continue
            if not record.get("shares_the_checkpointer"):
                self._lost[handle] = (
                    "it was spawned with a checkpointer of its own, which cannot cross a "
                    "checkpoint; it is still parked wherever that checkpointer lives"
                )
                continue
            self._held[handle] = HeldChild(
                handle=handle,
                run_id=str(record["run_id"]),
                composition=load(json.dumps(record["composition"]), Composition),
                ceiling=load(json.dumps(record["ceiling"]), Ceiling),
                checkpointer=checkpointer,
                # A fresh handle to stop it with: the old one was an object, and nothing this run
                # was holding had been cancelled, or it would not still be held.
                cancellation=Cancellation(),
                shares_the_checkpointer=True,
            )

    async def spawn(
        self,
        composition: Composition,
        ceiling: Ceiling,
        *,
        checkpointer: Any = None,
        within: EffectProfile | None = None,
        within_name: str = "",
        context: Mapping[str, JsonValue] | None = None,
        limits: PlanLimits | None = None,
        proposed_by: str = "compose",
        step: str | None = None,
        admitted: PlanLimits | None = None,
    ) -> tuple[str, list[Event]]:
        """Start a child and let it run. If it parks rather than ending, this parent holds it.

        The checkpointer defaults to one of ours, which makes a held child live exactly as long as
        this process. A host that wants a child to outlive a restart passes its own — the same
        checkpointer it would hand `run()`, and the same one Phase 6 proved on a file.

        `within` is a **second gate that only narrows** (D51): a pattern's ceiling, applied to the
        child's governance after the deployment's own policy has said yes. It is data — an effect
        profile and a name for the refusal — so a parent on the other side of a wire can send it,
        and the child runs here, on the record, rather than on the host with its events lost.
        """
        from shadow_hdk.runtime.loop import run

        # **Admission first** (D108): the whole plan measured and judged before anything compiles.
        # `limits` is what the caller — a pattern — allows; the run's own are met with it, so a
        # child is never admitted a wider plan than its parent would (D109). A refusal is an event
        # on the record and an exception to the caller; nothing below this line ran.
        effective = (
            admitted
            if admitted is not None
            else await self.admit(
                composition, limits=limits, proposed_by=proposed_by, context=context, step=step
            )
        )

        # **The parent's own, by default** (D37). A fresh in-memory saver made a child that could
        # not outlive this process — and, worse, could not be reached after its own parent parked,
        # so the parent came back holding nothing and started again.
        shared = checkpointer is None
        saver = checkpointer if checkpointer is not None else self._context.checkpointer
        # Its own handle, not the parent's: releasing one child must say nothing about its siblings.
        cancellation = Cancellation()
        handle = self._context.ports.clock.new_id()
        options = self._context.spawn_options(
            ceiling,
            run_id=handle,
            checkpointer=saver,
            cancellation=cancellation,
            plan_limits=effective,
            # The parent's attributes unless the caller hands the child its own (BUG-030).
            **({"context": dict(context)} if context is not None else {}),
        )
        ports = self._context.ports
        if within is not None:
            ports = replace(ports, governance=Narrowed(ports.governance, within, within_name))
        events = [event async for event in run(composition, ports, options=options)]
        if not any(isinstance(event, Ended) for event in events):
            self._held[handle] = HeldChild(
                handle=handle,
                run_id=handle,
                composition=composition,
                ceiling=ceiling,
                checkpointer=saver,
                cancellation=cancellation,
                shares_the_checkpointer=shared,
            )
            await self._context.announce_held(handle, _steps_in(events))
        return handle, events

    async def admit(
        self,
        composition: Composition,
        *,
        limits: PlanLimits | None = None,
        proposed_by: str = "compose",
        amendment: bool = False,
        context: Mapping[str, JsonValue] | None = None,
        step: str | None = None,
    ) -> PlanLimits:
        """The judgement no step can make (D108): structure and existence in the kernel, then
        each leaf's *declared* effects through this run's own policy — **named**, not pre-empted:
        `PlanAdmitted.refusals` and `.asks` say which steps will be refused or asked about when
        they run, and each step is still judged at its own invocation through the path that
        already refuses, parks or asks live (BUG-012, D57, D58, D88). A plan of one step is
        therefore told exactly what it always was; a host that wants one card for a whole plan
        has the list to present and rules to keep (D108/D121 as amended). Returns
        the effective limits the admitted plan runs under; raises `PlanNotAdmitted` otherwise,
        after the refusal is on the record with every mismatch (D111)."""
        mine = self._context.plan_limits or UNBOUNDED
        effective = mine if limits is None else mine.meet(limits)
        # The step the plan was proposed in: this task's, or the one a crossed caller names —
        # the runtime's task answering a wire call is not inside the step (as `request_approval`).
        step = step if step is not None else (self._context.step or "")
        digest = composition_digest(composition)
        registered = await self._context.registered()
        by_id = {registration.id: registration for registration in registered}

        outcome = admit(composition, registered, effective)
        mismatches: list[PlanMismatch] = list(
            outcome.mismatches if isinstance(outcome, PlanRefused) else ()
        )
        asked: list[tuple[str, str]] = []
        will_refuse: list[str] = []
        if not mismatches:
            # Every leaf's declared profile, judged where the step would be judged — the same
            # policy, the same context, marked as admission so a policy that wants to can tell.
            # Judged in the context the child will run under (BUG-030): the parent's by default,
            # or the one the caller hands the child — never a third one of admission's own.
            for leaf in leaves_of(composition):
                registration = by_id[leaf.component]
                base = self._context.context(leaf.id, registration)
                attributes: dict[str, JsonValue] = (
                    {
                        **dict(context),
                        "posture": base.attributes.get("posture"),
                        "component": leaf.component,
                    }
                    if context is not None
                    else dict(base.attributes)
                )
                attributes["admission"] = True
                judged = await self._context.judge(
                    registration.component.effects,
                    Context(
                        run_id=base.run_id,
                        step=base.step,
                        principal=base.principal,
                        attributes=attributes,
                    ),
                )
                match judged:
                    case Refuse():
                        will_refuse.append(leaf.id)
                    case Ask(question=question):
                        asked.append((leaf.id, question))
                    case Allow():
                        pass
        if mismatches:
            refusal = PlanRefused(tuple(mismatches))
            await self._context.emit(
                lambda **k: PlanRefusedEvent(
                    plan_digest=digest,
                    step=step,
                    mismatches=refusal.mismatches,
                    amendment=amendment,
                    **k,
                )
            )
            raise PlanNotAdmitted(refusal, amendment=amendment)
        authority = ""
        if (port := self._context.ports.authority) is not None:
            from shadow_hdk.kernel.authority import authority_digest

            authority = authority_digest(await port.current(run_id=self._context.run_id, step=step))
        admitted = Admitted(plan_digest=digest, authority_digest=authority, limits=effective)
        will_ask = tuple(leaf for leaf, _ in asked)
        await self._context.emit(
            lambda **k: PlanAdmitted(
                plan_digest=admitted.plan_digest,
                step=step,
                authority_digest=admitted.authority_digest,
                limits=admitted.limits,
                asks=will_ask,
                refusals=tuple(will_refuse),
                amendment=amendment,
                **k,
            )
        )
        return effective

    async def defer(
        self,
        composition: Composition,
        ceiling: Ceiling,
        *,
        within: EffectProfile | None = None,
        within_name: str = "",
        limits: PlanLimits | None = None,
        proposed_by: str = "compose",
    ) -> PlanLimits:
        """Admit a plan now and run it **after** the step that proposed it closes (D112). The
        admission is on the record at once; the run follows the planner's `Observed`, as this
        run's child, its events forwarded — the planner is told it is admitted, not its results."""
        effective = await self.admit(composition, limits=limits, proposed_by=proposed_by)
        self._deferred.append((composition, ceiling, within, within_name, effective))
        return effective

    async def run_deferred(self) -> list[Event]:
        """Spawn what the closing step deferred, in order; each already admitted."""
        events: list[Event] = []
        while self._deferred:
            composition, ceiling, within, within_name, effective = self._deferred.pop(0)
            _handle, seen = await self.spawn(
                composition, ceiling, within=within, within_name=within_name, admitted=effective
            )
            events.extend(seen)
        return events

    async def is_held(self, handle: str) -> bool:
        """Whether this parent is still holding a child — a query, so it can cross a wire (D51)."""
        return handle in self._held

    async def send(self, handle: str, message: JsonValue) -> list[Event]:
        """Wake a held child with a message. It answers where it slept, not from the beginning."""
        from shadow_hdk.runtime.loop import resume

        child = self._held[handle]
        events = [
            event
            async for event in resume(
                child.composition, message, self._context.ports, options=self._options_for(child)
            )
        ]
        if any(isinstance(event, Ended) for event in events):
            del self._held[handle]
            self._released.add(handle)
        return events

    async def amend(self, handle: str, composition: Composition, answer: Any) -> list[Event]:
        """Wake a held child on a **different** composition (D116). The runtime admits it as an
        amendment before the child takes it — `plan_admitted` with `amendment` on the record, or
        `plan_refused` and the child still held, untouched, on the plan it parked with."""
        from shadow_hdk.runtime.loop import resume

        child = self._held[handle]
        events = [
            event
            async for event in resume(
                composition, answer, self._context.ports, options=self._options_for(child)
            )
        ]
        if any(e.kind == "plan_admitted" and getattr(e, "amendment", False) for e in events):
            self._held[handle] = replace(child, composition=composition)
        if any(isinstance(event, Ended) for event in events):
            del self._held[handle]
            self._released.add(handle)
        return events

    async def release(self, handle: str) -> list[Event]:
        """Let a child go. It is cancelled, its lease settles, and the parent forgets it.

        The cancellation is set *before* the resume so the child stops at its first step boundary
        rather than doing one more piece of work on its way out. The child is woken only so that it
        can end: LangGraph re-runs the parked node from the top, the cancellation check is the first
        thing there, and the run ends `cancelled` without ever consuming what it was sent.

        Which is why the value below is a word rather than `None`. It is never read — but
        `Command(resume=None)` raises inside LangGraph 1.2 (`cannot access local variable
        'resume_is_map'`), so a run released that way would end `failed` and say something about a
        variable instead of saying it was let go.
        """
        from shadow_hdk.runtime.loop import resume

        child = self._held.pop(handle)
        self._released.add(handle)
        child.cancellation.cancel(f"released by {self._context.run_id}")
        return [
            event
            async for event in resume(
                child.composition, RELEASED, self._context.ports, options=self._options_for(child)
            )
        ]

    def _options_for(self, child: HeldChild) -> Any:
        return self._context.spawn_options(
            _within(child.ceiling, self._context.remaining().ceiling),
            run_id=child.run_id,
            checkpointer=child.checkpointer,
            cancellation=child.cancellation,
        )


def _within(asked: Ceiling, left: Ceiling) -> Ceiling:
    """A child's ceiling, clamped to what the parent still has.

    The ceiling a child was spawned with is a *request*, and the parent has spent since. Waking a
    child on its original ceiling asks for budget that is no longer there, and the carve refuses —
    which is right, but the answer is to ask for what is left rather than to fail.

    Found in Phase 8: a coordinating agent spawned a helper, took two more turns, and then could
    neither message nor release it, because both re-asked for the ceiling it started with. Phase 7's
    own tests missed it because the parent there spent nothing in between.
    """
    return Ceiling(
        max_steps=min(asked.max_steps, left.max_steps),
        max_wall_seconds=min(asked.max_wall_seconds, left.max_wall_seconds),
        max_cost_cents=_least(asked.max_cost_cents, left.max_cost_cents),
    )


def _least(asked: int | None, left: int | None) -> int | None:
    """`None` is *unknown*, not *unlimited*: a known ceiling beside an unknown one is the answer."""
    if asked is None:
        return left
    if left is None:
        return asked
    return min(asked, left)


def _steps_in(events: list[Event]) -> int:
    return sum(1 for event in events if event.kind == "invoked")


__all__ = ["Children", "HeldChild", "PlanNotAdmitted", "readable_refusal"]
