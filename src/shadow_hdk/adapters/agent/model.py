"""A ModelPort adapted below AgentPort, so every product still opens one Thread (D98)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import Any, cast

from shadow_hdk.adapters.agent.component import AgentComponent, _Turnwise
from shadow_hdk.adapters.agent.pattern import Pattern
from shadow_hdk.adapters.agent.skills import Skill
from shadow_hdk.kernel import Behaviour, EffectProfile
from shadow_hdk.kernel.observations import ApprovalRequest, Completed, Failed
from shadow_hdk.kernel.ports import (
    AgentSession,
    ModelPort,
    ToolSource,
    Turn,
    TurnChunk,
    Usage,
)
from shadow_hdk.runtime import Parked, current_run
from shadow_hdk.runtime.offer import PARKED_REASON


class ModelAgent:
    """Give a caller-owned model the provider-owned loop shape a Thread consumes.

    The loop itself is the same ``_Turnwise`` implementation used by ``AgentComponent``. During
    a turn it sees only the current run's visible registry, which is the registry the Thread
    attached before invoking the session. External agents receive that same registry as handed
    ``ToolSource`` values; an in-process model needs no second transport or product runner.
    """

    def __init__(
        self,
        *,
        model: ModelPort,
        pattern: Pattern,
        skill: Skill | None = None,
    ) -> None:
        self.model = model
        self.pattern = pattern
        self.skill = skill
        # A model agent is not registered as a component here. This object only supplies the
        # existing loop's pattern, skill and collision identity.
        self._loop = AgentComponent(
            pattern=pattern,
            skill=skill,
            effects=EffectProfile(),
            name="__model_agent__",
            registered_by="shadow-hdk",
        )

    async def open(
        self,
        *,
        tools: Sequence[ToolSource] = (),
        workspace: str | None = None,
        behaviour: Behaviour | None = None,
        resume: str | None = None,
    ) -> AgentSession:
        # Keep the exact sources on the session: they are the externally transportable form of
        # the attached registry and remain available to future model transports. The in-process
        # loop routes through the attached RunContext, so it cannot escape that registry.
        return cast(
            AgentSession,
            _ModelSession(
                self,
                tuple(tools),
                workspace=workspace,
                behaviour=behaviour,
                resume=resume,
            ),
        )


class _ModelSession:
    def __init__(
        self,
        agent: ModelAgent,
        tools: tuple[ToolSource, ...],
        *,
        workspace: str | None,
        behaviour: Behaviour | None,
        resume: str | None,
    ) -> None:
        self.agent = agent
        self.tools = tools
        self.workspace = workspace
        self.behaviour = behaviour
        self.session_id = resume or ""
        self.closed = False
        self._active: asyncio.Task[Any] | None = None
        self._interrupted = False

    async def turn(self, prompt: str) -> Turn:
        if self.closed:
            return Turn(text="the model session is closed", stop_reason="closed", failed=True)
        self._interrupted = False
        active = asyncio.create_task(self._turn(prompt))
        self._active = active
        try:
            return await active
        except asyncio.CancelledError:
            if not self._interrupted:
                raise
            return Turn(
                text="the model call was interrupted",
                stop_reason="interrupted",
            )
        finally:
            if self._active is active:
                self._active = None

    async def _turn(self, prompt: str) -> Turn:
        context = current_run()
        if context is None:
            return Turn(
                text="a model agent takes turns inside a Thread run",
                stop_reason="no_run",
                failed=True,
            )
        loop = _Turnwise(
            self.agent._loop,  # noqa: SLF001 — two halves of this adapter
            context,
            model=self.agent.model,
        )
        observation = await loop.work(prompt)
        while isinstance(observation, ApprovalRequest):
            answer = await context.request_approval(
                observation.question,
                step=observation.handle,
                about=(observation.component, observation.inputs),
            )
            if isinstance(answer, Parked):
                observation = loop.finished(
                    "parked",
                    text=PARKED_REASON.format(name=observation.component or "tool"),
                )
            else:
                observation = await loop.resume(answer)
        if isinstance(observation, Failed):
            return Turn(text=observation.error, stop_reason="failed", failed=True)
        if not isinstance(observation, Completed) or not isinstance(observation.output, dict):
            return Turn(
                text=f"the model loop ended with {observation.kind}",
                stop_reason=observation.kind,
                failed=True,
            )
        output = observation.output
        usage = _usage(output.get("usage"))
        reason = str(output.get("reason", ""))
        return Turn(
            text=str(output.get("text", "")),
            usage=usage,
            stop_reason=reason,
            failed=reason in {"failed", "provider_failed", "skill_unmet"},
        )

    async def close(self) -> None:
        self.closed = True
        active = self._active
        if active is not None and active is not asyncio.current_task():
            active.cancel()

    async def stream(self, prompt: str) -> AsyncIterator[TurnChunk]:
        done = await self.turn(prompt)
        yield TurnChunk(text=done.text, usage=done.usage, done=True)

    async def steer(self, text: str) -> bool:
        return False

    async def interrupt(self) -> bool:
        active = self._active
        if active is None or active.done():
            return False
        self._interrupted = True
        active.cancel()
        return True


def _usage(value: Any) -> Usage | None:
    if not isinstance(value, dict):
        return None
    return Usage(
        input_tokens=_optional_int(value.get("input_tokens")),
        output_tokens=_optional_int(value.get("output_tokens")),
        cost_cents=_optional_int(value.get("cost_cents")),
    )


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


__all__ = ["ModelAgent"]
