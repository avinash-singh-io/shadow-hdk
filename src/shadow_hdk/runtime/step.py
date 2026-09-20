"""One governed step — the whole enforcement story, in one function.

**Nine moves**, in this order, for every step of every composition:

    cancel check → lease check → refresh → resolve → inputs → resume? → judge
      → charge + invoke → observe

The count was wrong, and wrong twice over (TD-006): this docstring said seven and `runtime.md` said
a different seven, while the function did nine. Two of them arrived without either being updated —
the cancellation check (D15) and the resume branch (D38) — which is how a summary drifts from the
thing it summarises. Nine is what the code does; if a tenth is added, this line changes with it.

The charge is inside `_carry_out` rather than at the top, because the lease measures **work** and a
step refused before it ran did none.

Two error classes are load-bearing (D7). A **component** raising, a component that is not
registered, and a binding that refers to nothing are all *data*: a `Failed` observation the agent
sees. A **port** raising is a failure: `PortFailure`, which the drive turns into
`Ended(reason="failed")`, because a broken host is not something the runtime can reason past.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, cast

from langgraph.types import interrupt
from pydantic import JsonValue

from shadow_hdk.kernel.authority import stage_effect
from shadow_hdk.kernel.components import Posture, Registration
from shadow_hdk.kernel.composition import Await, Invoke
from shadow_hdk.kernel.contracts import adapter_for
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import ApprovalRequested, EffectRecorded, Event, Invoked, Observed
from shadow_hdk.kernel.events import Refused as RefusedEvent
from shadow_hdk.kernel.events import UsageReported as SpentEvent
from shadow_hdk.kernel.observations import (
    ApprovalRequest,
    Completed,
    Failed,
    InputRequest,
    Observation,
    Pending,
    Refused,
)
from shadow_hdk.kernel.ports import (
    Allow,
    Ask,
    ComponentPort,
    Context,
    Judgement,
    Usage,
)
from shadow_hdk.kernel.ports import (
    Refuse as PortRefuse,
)
from shadow_hdk.runtime.bindings import Ports, executing
from shadow_hdk.runtime.effects import EffectState, EffectTransaction
from shadow_hdk.runtime.emit import Emitter
from shadow_hdk.runtime.errors import DanglingRef, LeaseExhausted, PortFailure, RuntimeStop
from shadow_hdk.runtime.inputs import resolve_inputs
from shadow_hdk.runtime.registry import Registry
from shadow_hdk.runtime.session import Session
from shadow_hdk.runtime.state import RunState


class StepExecutor:
    def __init__(
        self,
        session: Session,
        emitter: Emitter,
        ports: Ports,
        registry: Registry,
        context: Any = None,
        resuming: dict[str, str] | None = None,
        kept: dict[str, Any] | None = None,
        plan: JsonValue = None,
        replays: dict[str, int] | None = None,
    ) -> None:
        self.session = session
        self.registry = registry
        self._emitter = emitter
        #: The composition being executed, as JSON, written into every node's state (D116).
        self.plan = plan
        self._ports = ports
        self._context = context
        self._resuming = dict(resuming or {})
        """Steps this leg is resuming, and what each parked on (D38). Consumed on first use: a
        step resumes once, and anything after that is an ordinary step."""
        self._kept = dict(kept or {})
        """What a step that asked for itself kept before parking (D57), by step id."""
        self._replays = {k: int(v) for k, v in (replays or {}).items()}
        """How many answers each resuming step's task already holds — LangGraph replays a task's
        earlier resume values by index on every re-run, so a step that parked a second time in
        one leg finds its first answer at the first `interrupt()` and the new one after it."""
        self._drained: dict[str, int] = {}
        """What `interrupt()` handed back this leg, by step: the count a second park carries as
        `replays`, so the next leg drains exactly that many before reading the newest answer."""

    def holding(self) -> dict[str, Any]:
        """What this run is holding, for the state to carry (D37). Empty when it holds nothing,
        which is most runs."""
        if self._context is None:
            return {}
        record: dict[str, Any] = self._context.children.record()
        return record

    def spent(self) -> dict[str, float]:
        """The meter's counters and the record's high-water mark, for the state to carry (D33)."""
        return {**self.session.meter.spent(), "seq": self._emitter.seq}

    # ------------------------------------------------------------------ the seven moves

    async def invoke(self, step: Invoke | Await, state: RunState) -> Observation:
        # First, before the lease: a cancelled run should not spend the step it was about to be
        # refused for, and the reason on the record should be the host's, not the budget's (D15).
        self.session.cancellation.check()
        # Steps and the clock first, whatever the component; money once the component is known,
        # because a component that cannot spend is not refused for having nothing to spend.
        if reason := self.session.meter.check(costs=False):
            raise LeaseExhausted(reason)

        await self._refresh()

        try:
            port, registration = self.registry.resolve(step.component)
        except KeyError:
            return await self._observe(
                step, Failed(f"no component registered as {step.component!r}")
            )
        if registration.component.effects.costs and (reason := self.session.meter.check()):
            raise LeaseExhausted(reason)

        try:
            inputs = resolve_inputs(step.inputs, state["handles"])
        except DanglingRef as exc:
            return await self._observe(step, Failed(str(exc)))

        parked_on = self._resuming.pop(step.id, None)
        if parked_on is not None:
            return await self._resume_where_it_parked(step, parked_on, port, registration, inputs)

        judgement = await self._judge(
            registration.component.effects,
            self.session.context_for(step.id, registration, inputs),
        )
        match judgement:
            case PortRefuse(reason=why):
                await self._emit(lambda **k: RefusedEvent(step=step.id, reason=why, **k))
                return Refused(why)
            case Ask(question=question):
                answer = await self._ask(step, question, about=(registration.id, inputs))
                if not isinstance(answer, Allow):
                    return await self._observe(
                        step, Refused(getattr(answer, "reason", "not allowed"))
                    )

        return await self._carry_out(step, port, registration, inputs)

    async def _carry_out(
        self,
        step: Invoke | Await,
        port: ComponentPort,
        registration: Registration,
        inputs: JsonValue,
    ) -> Observation:
        """Charge the step, announce it, run it, price it, and record what came back.

        **The lease is charged here rather than at the top of `invoke`** (TD-006). A step charged
        before it was judged meant a policy refusing everything drained the budget of a run that did
        nothing — measured, five refusals under a ceiling of three ended `lease_exhausted`, which
        reports a budget problem for a policy decision. The lease measures work, and a refusal is
        the absence of work.

        Every path that actually runs a component comes through here, including the resumed one, so
        a step is charged exactly once whether it parked or not. A component that asked for itself
        (D57) is invoked twice for one step and charged here both times — and still counted once,
        because the first leg's charge never reaches the checkpoint: the node interrupted before it
        returned, and `resume()` restores the meter from what the checkpoint holds. Measured: a
        second leg that skipped the charge reported one step for two.
        """
        posture = registration.component.provenance.posture
        transactional = (
            posture == "controlled"
            and not registration.component.effects.reversible
            # A conversation is the planner/provider boundary; its tool calls are the effects.
            # Treating the turn itself as the world act would authorize the plan and then reuse
            # that grant for whatever the model later chose, the inversion D102 forbids.
            and "conversation" not in registration.component.labels
        )
        authority = self._ports.authority
        authorizer = self._ports.authorizer
        journal = self._ports.effect_journal
        if transactional and (authority is None or authorizer is None or journal is None):
            why = "controlled irreversible effect requires authority, authorizer and journal ports"
            await self._emit(lambda **k: RefusedEvent(step=step.id, reason=why, **k))
            return await self._observe(step, Refused(why), posture)

        self.session.meter.charge()
        await self._emit(
            lambda **k: Invoked(step=step.id, component=registration.id, inputs=inputs, **k)
        )
        try:
            if transactional:
                assert authority is not None and authorizer is not None and journal is not None
                expected = await authority.current(run_id=self.session.run_id, step=step.id)
                effect = stage_effect(
                    run_id=self.session.run_id,
                    step=step.id,
                    component=registration.id,
                    inputs=inputs,
                    effects=registration.component.effects,
                    authority_digest=expected.digest,
                    idempotency_key=f"{self.session.run_id}/{step.id}",
                )

                async def invoke_effect() -> JsonValue:
                    with executing(step.id):
                        result = await port.invoke(registration.id, inputs)
                    value: JsonValue = adapter_for(Observation).dump_python(result, mode="json")
                    return value

                async def record_effect(entry: Any, replayed: bool) -> None:
                    await self._emit(
                        lambda **k: EffectRecorded(
                            step=step.id,
                            attempt_id=entry.attempt_id,
                            status=entry.kind,
                            stage_digest=entry.stage_digest,
                            authorization_id=entry.authorization_id,
                            detail=entry.detail,
                            recorded_at=entry.at,
                            replayed=replayed,
                            **k,
                        )
                    )

                state = await EffectTransaction(
                    authority=authority,
                    authorizer=authorizer,
                    journal=journal,
                    clock=self._ports.clock,
                    recorded=record_effect,
                ).execute(effect, invoke=invoke_effect, expected_authority=expected)
                observation = self._effect_observation(state)
                if isinstance(observation, Refused):
                    refusal_reason = observation.reason
                    await self._emit(
                        lambda **k: RefusedEvent(step=step.id, reason=refusal_reason, **k)
                    )
            else:
                with executing(step.id):
                    observation = await port.invoke(registration.id, inputs)
        # No `except PortFailure` here, and a mutation proved it would be dead code: `RuntimeStop`
        # is a `BaseException` (TD-006), so `except Exception` cannot catch one. The fix had to be
        # there rather than here anyway — `visible()` and `propose()` run *inside* a component, and
        # every component adapter has its own `except Exception` that would have swallowed it first.
        except Exception as exc:  # noqa: BLE001 — D7: a component is untrusted
            observation = Failed(_described(exc))
        finally:
            if self._context is not None:
                self._context.resumed_done(step.id)
        if isinstance(observation, ApprovalRequest | InputRequest):
            # **The component asked for itself** (D57): a question that is not the policy's and not
            # the component's own to answer — an agent whose tool call was asked about. The run
            # parks on it exactly as if governance had asked, carrying what the component kept so
            # the next leg can pick up where it stopped. Raises to park; never returns here.
            kept = self._context.take_kept(step.id) if self._context is not None else None
            await self._ask(
                step,
                observation.question,
                kept=kept,
                by="component",
                # An approval request names the act; the agent's own question to the person does
                # not (D65) — the record keeps whichever it was.
                about=(
                    getattr(observation, "component", None),
                    getattr(observation, "inputs", None),
                ),
            )
            raise RuntimeError("interrupt() returned on the parking path")  # pragma: no cover
        usage = _usage_of(observation)
        self.session.meter.charge_cost(usage)
        if usage is not None:
            # Where the meter is charged, and only there (D20). A step that cost nothing says
            # nothing, because a kind that appears with nothing to report is one readers skip.
            await self._emit(lambda **k: SpentEvent(step=step.id, usage=usage, **k))
        if isinstance(step, Await) and isinstance(observation, Pending):
            # The grammar's other half. `Invoke` is *do it now*; `Await` is *this may take a while*,
            # so a component that says `Pending` there is taken at its word and the run parks.
            observation = Completed(await self._wait(step, observation))
        observed = await self._observe(step, observation, posture)
        # **A plan deferred by this step runs after it** (D112): the planner's step has closed
        # on the record; the plan it admitted runs on as this run's child, its events forwarded,
        # nothing folded back into the planner's transcript.
        if self._context is not None:
            await self._context.children.run_deferred()
        return observed

    @staticmethod
    def _effect_observation(state: EffectState) -> Observation:
        if state.status in {"receipt", "reconciled"}:
            try:
                return cast(Observation, adapter_for(Observation).validate_python(state.receipt))
            except Exception:  # noqa: BLE001 — a malformed receipt is effect data, not a crash
                return Failed("effect journal receipt is not an Observation")
        if state.status == "refused":
            return Refused(state.reason or "effect authorization refused")
        if state.status == "failed":
            return Failed(state.reason or "effect failed")
        if state.status == "unknown":
            return Failed(state.reason or "effect outcome is unknown")
        return Failed(f"effect attempt stopped in non-terminal state {state.status!r}")

    async def _resume_where_it_parked(
        self,
        step: Invoke | Await,
        parked_on: str,
        port: ComponentPort,
        registration: Registration,
        inputs: JsonValue,
    ) -> Observation:
        """Pick the step up at the `interrupt()` it raised, and nowhere earlier (D38).

        LangGraph re-runs a node from the top, and `interrupt()` hands back the answer only where
        it was raised — so everything above it used to happen twice. **It is not judged again:** a
        policy that changed its mind while a human was thinking overruled the human it had asked,
        and one that stopped asking discarded a refusal and ran the work. And an `Await` is not
        invoked again: it already said `Pending`, and what it is waiting for is the answer.
        """
        if parked_on == "await":
            assert isinstance(step, Await), "only an Await parks on the mailbox"
            delivered = await self._wait(step, None)
            return await self._observe(
                step, Completed(delivered), registration.component.provenance.posture
            )
        if parked_on == "component":
            # Not judged again — the policy said yes before the component asked. The component
            # finds the answer and what it kept (D57). A step that parked more than once in one
            # leg has its earlier answers replayed first (LangGraph resumes by index): they were
            # applied when they were given, so they are drained here and only the newest is the
            # component's — a plan that asks twice is not answered twice with its first answer.
            answer = await self._ask(step, "resumed")
            for _replayed in range(self._replays.get(step.id, 0)):
                answer = await self._ask(step, "resumed")
            if self._context is not None:
                self._context.resuming(step.id, answer, self._kept.get(step.id))
            return await self._carry_out(step, port, registration, inputs)
        raw = await self._ask(step, "resumed")
        if self._context is not None:
            raw = await self._context.accept_answer(raw)
        answered = _as_judgement(raw)
        if not isinstance(answered, Allow):
            return await self._observe(
                step,
                Refused(getattr(answered, "reason", "the answer to an ask was not a judgement")),
                registration.component.provenance.posture,
            )
        return await self._carry_out(step, port, registration, inputs)

    # ------------------------------------------------------------------ the seams

    async def _ask(
        self,
        step: Invoke | Await,
        question: str,
        *,
        kept: JsonValue | None = None,
        by: str = "governance",
        about: tuple[str | None, JsonValue | None] = (None, None),
    ) -> Any:
        """Park the step. Whoever implements governance decides what asking means; the runtime
        only stops, and LangGraph's checkpoint is what lets the process end here and come back.

        **`ApprovalRequested` is emitted only when the step actually parks.** LangGraph re-runs
        the whole node on resume, so everything above `interrupt()` happens a second time —
        emitting the event before the call put two asks in the record for one question. The
        contract is therefore *raise to park, return to proceed*, and the event belongs on the
        raising path.
        """
        handle = f"{self.session.run_id}:{step.id}"
        # `resume_seq` is where the record continues (D33). The checkpoint's own mark was written
        # when the last node *returned*, and this path still emits `Asked` after that — so the
        # number to come back on is one past what this emitter is about to stamp. The property
        # that guards it is a test that no seq is reused across a park, for an ask and a wait.
        payload: dict[str, Any] = {
            "run_id": self.session.run_id,
            "step": step.id,
            "question": question,
            "resume_seq": self._emitter.seq + 1,
            "replays": self._drained.get(step.id, 0),
        }
        if by == "component":
            # Who asked, what they kept — and what this run is holding (D37): a child spawned and
            # parked *in this same step* is not in the state's `children` channel yet, because the
            # node never returned. It rides the interrupt, like everything else this leg would lose.
            payload["by"] = by
            payload["kept"] = kept
            payload["holding"] = self.holding()
        component, inputs = about
        try:
            answered = interrupt(payload)
        except BaseException:  # noqa: BLE001 — anything out of interrupt() means "parking now"
            await self._emit(
                lambda **k: ApprovalRequested(
                    step=step.id,
                    question=question,
                    handle=handle,
                    component=component,
                    inputs=inputs,
                    **k,
                )
            )
            raise
        self._drained[step.id] = self._drained.get(step.id, 0) + 1
        return answered

    async def _wait(self, step: Await, pending: Pending | None) -> JsonValue:
        """Park on a handle the component named, and come back with whatever answered it.

        Same contract as `_ask`: **raise to park, return to proceed**, and the record is written on
        the raising path. LangGraph re-runs the node on resume, so the component is asked a second
        time and says `Pending` again — and this time `interrupt()` returns the answer instead of
        raising, so the wait ends rather than repeating. A component put on an `Await` therefore has
        to tolerate being called twice, which is the same rule everything above `interrupt()` obeys.
        """
        payload = {
            "run_id": self.session.run_id,
            "step": step.id,
            # `None` on the resume path, where `interrupt()` returns rather than raising and the
            # handle is only wanted for the payload it would have parked with (D38).
            "handle": pending.handle if pending is not None else "",
            "resume_seq": self._emitter.seq + 1,  # this path emits one `Observed` before it parks
            "replays": self._drained.get(step.id, 0),
        }
        try:
            answer: JsonValue = interrupt(payload)
            self._drained[step.id] = self._drained.get(step.id, 0) + 1
            return answer
        except BaseException:  # noqa: BLE001 — anything out of interrupt() means "parking now"
            # On the parking path only: the record says the step is waiting, and says it once.
            if pending is not None:
                await self._observe(step, pending)
            raise

    async def _judge(self, effects: EffectProfile, context: Context) -> Judgement:
        try:
            return await self._ports.governance.judge(effects, context)
        except RuntimeStop:
            raise
        except Exception as exc:
            raise PortFailure("governance", exc) from exc

    async def _refresh(self) -> None:
        try:
            await self.registry.refresh()
        except RuntimeStop:
            raise
        except Exception as exc:
            raise PortFailure("components", exc) from exc

    async def _emit(self, make: Callable[..., Event]) -> Event:
        return await self._emitter.emit(make)

    async def _observe(
        self, step: Invoke | Await, observation: Observation, posture: Posture = "controlled"
    ) -> Observation:
        """Record it, with the posture of what produced it (D30). A step that never reached a
        component is `controlled`: the runtime refused it, and refusing is control."""
        await self._emit(
            lambda **k: Observed(step=step.id, observation=observation, posture=posture, **k)
        )
        return observation


def _described(exc: BaseException) -> str:
    """A failure's text, with an exception group's members named — *unhandled errors in a
    TaskGroup (1 sub-exception)* says nothing a reader can act on (measured in the studio)."""
    text = f"{type(exc).__name__}: {exc}"
    if isinstance(exc, BaseExceptionGroup):
        inner = "; ".join(_described(e) for e in exc.exceptions)
        text = f"{text} [{inner}]"
    return text


def _as_judgement(answer: Any) -> Judgement | None:
    """What a host said, as a judgement — or `None` if it did not answer the question.

    An `Ask` asks a governance question, and the answer is a `Judgement`. Over the wire it arrives
    as **JSON**, because that is what crosses a checkpoint and a socket (D19), so its written form
    is loaded here at the runtime's own edge. Anything else — a bare string, a `True` — is not an
    answer, and a step whose consent nobody actually gave does not run (D38).
    """
    if isinstance(answer, Allow | Ask | PortRefuse):
        return answer
    if isinstance(answer, dict) and isinstance(answer.get("kind"), str):
        from shadow_hdk.kernel.contracts import load

        try:
            loaded: Judgement = load(json.dumps(answer), Judgement)
        except Exception:  # noqa: BLE001 — a shape we do not recognise is not an answer
            return None
        return loaded
    return None


def _usage_of(observation: Observation) -> Usage | None:
    """What a step cost, if it says. A component that made no model call reports nothing, which is
    *no cost and that is known* — never *unknown*. A model adapter that cannot price its call
    reports `cost_cents: None`, which is unknown, and the meter stops claiming to know the total.
    """
    if isinstance(observation, Completed) and isinstance(observation.output, dict):
        usage = observation.output.get("usage")
        if isinstance(usage, dict):
            return Usage(
                input_tokens=_int_or_none(usage.get("input_tokens")),
                output_tokens=_int_or_none(usage.get("output_tokens")),
                cost_cents=_int_or_none(usage.get("cost_cents")),
                # Read back whole (BUG-063): the two cache counters were dropped here, so every
                # piece of D141 was tested and `Spent` still said 0 for every thread turn.
                cache_read_tokens=_int_or_none(usage.get("cache_read_tokens")),
                cache_write_tokens=_int_or_none(usage.get("cache_write_tokens")),
            )
    return None


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) else None
