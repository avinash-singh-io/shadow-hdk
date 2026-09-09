"""One governed step — the seven moves, and the whole enforcement story.

Every node of every compiled graph calls `invoke`. Nothing else touches a component, and nothing
else asks the governance port. That is why "was this judged?" is a structural fact rather than a
review question.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import JsonValue

from shadow_hdk.kernel.composition import Await, Invoke
from shadow_hdk.kernel.events import Asked as AskedEvent
from shadow_hdk.kernel.events import Invoked, Observed
from shadow_hdk.kernel.events import Refused as RefusedEvent
from shadow_hdk.kernel.observations import (
    Asked,
    Completed,
    Failed,
    Observation,
    Pending,
    Refused,
)
from shadow_hdk.kernel.ports import Allow, Ask, Context, Refuse, Usage
from shadow_hdk.runtime.bindings import Ports
from shadow_hdk.runtime.emit import Emitter
from shadow_hdk.runtime.errors import DanglingRef, LeaseExhausted, PortFailure
from shadow_hdk.runtime.inputs import resolve_inputs
from shadow_hdk.runtime.registry import Registry
from shadow_hdk.runtime.session import Session
from shadow_hdk.runtime.state import RunState

T = TypeVar("T")

Interrupter = Callable[[dict[str, JsonValue]], object]
"""How the executor parks a step. LangGraph's `interrupt` in a graph; injectable for tests."""


def _langgraph_interrupt(payload: dict[str, JsonValue]) -> object:
    from langgraph.types import interrupt

    return interrupt(payload)


class StepExecutor:
    def __init__(
        self,
        session: Session,
        emitter: Emitter,
        ports: Ports,
        registry: Registry,
        *,
        interrupter: Interrupter = _langgraph_interrupt,
    ) -> None:
        self.session = session
        self.emitter = emitter
        self.ports = ports
        self.registry = registry
        self._interrupt = interrupter

    async def visible(self) -> list:
        """The catalogue as the policy leaves it, for whoever is about to show it to a model."""
        return await self.registry.visible(
            self.ports.governance, self.session.context_for("<catalogue>")
        )

    async def invoke(self, step: Invoke | Await, state: RunState) -> Observation:
        # 1 — the ceiling always beats everything, including the floor.
        if reason := self.session.meter.check():
            raise LeaseExhausted(reason)

        # 2 — resolve, against a registry read fresh. The registry is live (`09` §4): connect an
        # MCP server mid-session and its tools are here on the next step. Making that cheap is the
        # adapter's business — an adapter over a remote server caches and decides when to re-read;
        # the runtime only asks. Group 5's benchmark is where that claim is checked.
        await self._port("component", self.registry.refresh())
        try:
            port, registration = self.registry.resolve(step.component)
        except KeyError:
            return await self._observe(
                step, Failed(f"no component registered as {step.component!r}")
            )

        # 3 — inputs, likewise.
        try:
            inputs = resolve_inputs(step.inputs, state["handles"])
        except DanglingRef as exc:
            return await self._observe(step, Failed(str(exc)))

        # 4 — judge, over effects, never over the name.
        context = self.session.context_for(step.id)
        judgement = await self._port(
            "governance", self.ports.governance.judge(registration.component.effects, context)
        )
        match judgement:
            case Refuse(reason=reason):
                # One event, not two: the refusal *is* the record of what happened to this step.
                await self.emitter.emit(lambda **k: RefusedEvent(step=step.id, reason=reason, **k))
                return Refused(reason)
            case Ask(question=question):
                answer = await self._ask(step, context, question)
                if answer is not None:
                    return answer
            case Allow():
                pass

        # 5 — invoke. A component is untrusted (D7).
        await self.emitter.emit(
            lambda **k: Invoked(step=step.id, component=registration.id, inputs=inputs, **k)
        )
        try:
            observation = await port.invoke(registration.id, inputs)
        except Exception as exc:  # noqa: BLE001 — the whole point: a component never crashes a run
            observation = Failed(f"{type(exc).__name__}: {exc}")

        # 6 — charge, 7 — observe.
        self.session.meter.charge(_usage_of(observation))
        return await self._observe(step, observation)

    async def _ask(
        self, step: Invoke | Await, context: Context, question: str
    ) -> Observation | None:
        """Park the step. `None` means the host allowed it and the step may proceed."""
        handle = f"{self.session.run_id}:{step.id}"
        await self.emitter.emit(
            lambda **k: AskedEvent(step=step.id, question=question, handle=handle, **k)
        )
        answer = self._interrupt(
            {"run_id": self.session.run_id, "step": step.id, "question": question}
        )
        if isinstance(answer, Allow):
            return None
        if isinstance(answer, Refuse):
            return Refused(answer.reason)
        if answer is None:
            return Pending(handle)
        return Refused(f"not allowed: {answer!r}")

    async def _observe(self, step: Invoke | Await, observation: Observation) -> Observation:
        """`Observed` only. `Invoked` is emitted where a component is actually called — a step that
        failed to resolve or whose inputs were dangling never reached one, and saying otherwise
        would put a call in the record that never happened."""
        await self.emitter.emit(lambda **k: Observed(step=step.id, observation=observation, **k))
        return observation

    async def _port(self, name: str, call: Awaitable[T]) -> T:
        """A port is the host. If it raises, the run ends — it is not reasoned past (D7)."""
        try:
            return await call
        except Exception as exc:
            raise PortFailure(name, exc) from exc


def _usage_of(observation: Observation) -> Usage | None:
    """A step that made no model call charges no cost, and that is known — not unknown (Group 0)."""
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


__all__ = ["Asked", "StepExecutor"]
