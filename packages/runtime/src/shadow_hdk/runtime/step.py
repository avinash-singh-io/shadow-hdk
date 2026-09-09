"""One governed step — the whole enforcement story, in one function.

Seven moves, in this order, for every step of every composition:

    lease check → refresh → resolve → inputs → judge → invoke → observe

Two error classes are load-bearing (D7). A **component** raising, a component that is not
registered, and a binding that refers to nothing are all *data*: a `Failed` observation the agent
sees. A **port** raising is a failure: `PortFailure`, which the drive turns into
`Ended(reason="failed")`, because a broken host is not something the runtime can reason past.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.types import interrupt

from shadow_hdk.kernel.components import Registration
from shadow_hdk.kernel.composition import Await, Invoke
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import Asked as AskedEvent
from shadow_hdk.kernel.events import Event, Invoked, Observed
from shadow_hdk.kernel.events import Refused as RefusedEvent
from shadow_hdk.kernel.observations import Failed, Observation, Refused
from shadow_hdk.kernel.ports import Allow, Ask, Context, Judgement, Refuse
from shadow_hdk.runtime.bindings import Ports
from shadow_hdk.runtime.emit import Emitter
from shadow_hdk.runtime.errors import DanglingRef, LeaseExhausted, PortFailure, RuntimeStop
from shadow_hdk.runtime.inputs import resolve_inputs
from shadow_hdk.runtime.registry import Registry
from shadow_hdk.runtime.session import Session
from shadow_hdk.runtime.state import RunState

CATALOGUE = ""
"""The step id used when governance is asked about the catalogue rather than about a step."""


class StepExecutor:
    def __init__(
        self, session: Session, emitter: Emitter, ports: Ports, registry: Registry
    ) -> None:
        self.session = session
        self.registry = registry
        self._emitter = emitter
        self._ports = ports

    # ------------------------------------------------------------------ what the agent may see

    async def visible(self) -> list[Registration]:
        """The catalogue, filtered by governance. A component the policy would refuse for every
        input is **absent**, not greyed out, so a narrowed agent never sees what it may not touch.
        """
        context = self.session.context_for(CATALOGUE)
        shown: list[Registration] = []
        for registration in self.registry.all():
            if not isinstance(await self._judge(registration.component.effects, context), Refuse):
                shown.append(registration)
        return shown

    # ------------------------------------------------------------------ the seven moves

    async def invoke(self, step: Invoke | Await, state: RunState) -> Observation:
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

        judgement = await self._judge(
            registration.component.effects, self.session.context_for(step.id)
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

        await self._emit(
            lambda **k: Invoked(step=step.id, component=registration.id, inputs=inputs, **k)
        )
        try:
            observation = await port.invoke(registration.id, inputs)
        except Exception as exc:  # noqa: BLE001 — D7: a component is untrusted
            observation = Failed(f"{type(exc).__name__}: {exc}")
        return await self._observe(step, observation)

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
        payload = {"run_id": self.session.run_id, "step": step.id, "question": question}
        try:
            return interrupt(payload)
        except BaseException:  # noqa: BLE001 — anything out of interrupt() means "parking now"
            await self._emit(
                lambda **k: AskedEvent(step=step.id, question=question, handle=handle, **k)
            )
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

    async def _observe(self, step: Invoke | Await, observation: Observation) -> Observation:
        await self._emit(lambda **k: Observed(step=step.id, observation=observation, **k))
        return observation
