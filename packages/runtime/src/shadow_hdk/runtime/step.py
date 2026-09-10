"""One governed step — the whole enforcement story, in one function.

Seven moves, in this order, for every step of every composition:

    lease check → refresh → resolve → inputs → judge → invoke → observe

Two error classes are load-bearing (D7). A **component** raising, a component that is not
registered, and a binding that refers to nothing are all *data*: a `Failed` observation the agent
sees. A **port** raising is a failure: `PortFailure`, which the drive turns into
`Ended(reason="failed")`, because a broken host is not something the runtime can reason past.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from langgraph.types import interrupt
from pydantic import JsonValue

from shadow_hdk.kernel.components import Posture, Registration
from shadow_hdk.kernel.composition import Await, Invoke
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import Asked as AskedEvent
from shadow_hdk.kernel.events import Event, Invoked, Observed
from shadow_hdk.kernel.events import Refused as RefusedEvent
from shadow_hdk.kernel.events import Spent as SpentEvent
from shadow_hdk.kernel.observations import (
    Completed,
    Failed,
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
    Refuse,
    Usage,
)
from shadow_hdk.runtime.bindings import Ports, executing
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
    ) -> None:
        self.session = session
        self.registry = registry
        self._emitter = emitter
        self._ports = ports
        self._context = context
        self._resuming = dict(resuming or {})
        """Steps this leg is resuming, and what each parked on (D38). Consumed on first use: a
        step resumes once, and anything after that is an ordinary step."""

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
        if reason := self.session.meter.check():
            raise LeaseExhausted(reason)
        self.session.meter.charge()

        await self._refresh()

        try:
            port, registration = self.registry.resolve(step.component)
        except KeyError:
            return await self._observe(
                step, Failed(f"no component registered as {step.component!r}")
            )

        try:
            inputs = resolve_inputs(step.inputs, state["handles"])
        except DanglingRef as exc:
            return await self._observe(step, Failed(str(exc)))

        parked_on = self._resuming.pop(step.id, None)
        if parked_on is not None:
            return await self._resume_where_it_parked(step, parked_on, port, registration, inputs)

        judgement = await self._judge(
            registration.component.effects, self.session.context_for(step.id, registration)
        )
        match judgement:
            case Refuse(reason=reason):
                await self._emit(lambda **k: RefusedEvent(step=step.id, reason=reason, **k))
                return Refused(reason)
            case Ask(question=question):
                answer = await self._ask(step, question)
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
        """Announce the step, run it, price it, and record what came back."""
        await self._emit(
            lambda **k: Invoked(step=step.id, component=registration.id, inputs=inputs, **k)
        )
        try:
            with executing(step.id):
                observation = await port.invoke(registration.id, inputs)
        except Exception as exc:  # noqa: BLE001 — D7: a component is untrusted
            observation = Failed(f"{type(exc).__name__}: {exc}")
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
        return await self._observe(step, observation, registration.component.provenance.posture)

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
            delivered = await self._wait(step, None)
            return await self._observe(
                step, Completed(delivered), registration.component.provenance.posture
            )
        answered = _as_judgement(await self._ask(step, "resumed"))
        if not isinstance(answered, Allow):
            return await self._observe(
                step,
                Refused(getattr(answered, "reason", "the answer to an ask was not a judgement")),
                registration.component.provenance.posture,
            )
        return await self._carry_out(step, port, registration, inputs)

    # ------------------------------------------------------------------ the seams

    async def _ask(self, step: Invoke | Await, question: str) -> Any:
        """Park the step. Whoever implements governance decides what asking means; the runtime
        only stops, and LangGraph's checkpoint is what lets the process end here and come back.

        **`Asked` is emitted only when the step actually parks.** LangGraph re-runs the whole node
        on resume, so everything above `interrupt()` happens a second time — emitting the event
        before the call put two asks in the record for one question. The contract is therefore
        *raise to park, return to proceed*, and the event belongs on the raising path.
        """
        handle = f"{self.session.run_id}:{step.id}"
        # `resume_seq` is where the record continues (D33). The checkpoint's own mark was written
        # when the last node *returned*, and this path still emits `Asked` after that — so the
        # number to come back on is one past what this emitter is about to stamp. The property
        # that guards it is a test that no seq is reused across a park, for an ask and a wait.
        payload = {
            "run_id": self.session.run_id,
            "step": step.id,
            "question": question,
            "resume_seq": self._emitter.seq + 1,
        }
        try:
            return interrupt(payload)
        except BaseException:  # noqa: BLE001 — anything out of interrupt() means "parking now"
            await self._emit(
                lambda **k: AskedEvent(step=step.id, question=question, handle=handle, **k)
            )
            raise

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
        }
        try:
            answer: JsonValue = interrupt(payload)
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


def _as_judgement(answer: Any) -> Judgement | None:
    """What a host said, as a judgement — or `None` if it did not answer the question.

    An `Ask` asks a governance question, and the answer is a `Judgement`. Over the wire it arrives
    as **JSON**, because that is what crosses a checkpoint and a socket (D19), so its written form
    is loaded here at the runtime's own edge. Anything else — a bare string, a `True` — is not an
    answer, and a step whose consent nobody actually gave does not run (D38).
    """
    if isinstance(answer, Allow | Ask | Refuse):
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
            )
    return None


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) else None
