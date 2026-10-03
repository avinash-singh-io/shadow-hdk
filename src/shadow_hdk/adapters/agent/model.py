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
    Message,
    ModelPort,
    ToolSource,
    Turn,
    TurnChunk,
    Usage,
)
from shadow_hdk.kernel.providers import unmapped_for_a_model
from shadow_hdk.runtime import Parked, current_run
from shadow_hdk.runtime.offer import PARKED_TURN


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
        self._loop: Any = None
        self.before: tuple[Message, ...] = ()
        """This thread's earlier turns, carried from one turn to the next (D181, BUG-232).

        It lives here rather than on the loop because **the loop is built fresh for every turn** and
        the session is what outlives them. Everything after the system message, so the role is
        rebuilt per turn and a `set_mode` is not shadowed by a stale one.

        Unbounded on purpose, for now: this is what every chat API does and what a product expects
        of a thread. Fitting a transcript to a model's window is a budget and a compaction, which
        are separate asks — ENH-052 records the interaction."""
        self.unmapped: tuple[str, ...] = unmapped_for_a_model(
            behaviour, selects_model=_selects_model(agent.model)
        )
        """What this mode asked for that this port cannot honour (BUG-229, D170, BUG-231).

        Read off the session by name in `Conversation` (ENH-020), exactly as a CLI's is. Before
        this a `_ModelSession` had no such attribute, so `getattr(session, "unmapped", ())`
        answered `()` — and a host read that as *your mode was honoured in full* while the
        instructions were being dropped. Empty was the one answer this must never give by
        accident.

        `model` is now the port's answer rather than a constant (D180): one that can build a chat
        model for another spec honours it, one wrapping a chat model somebody else configured cannot
        and says so. Phase 62 reported it honoured unconditionally while the only real adapter
        discarded it (BUG-231)."""

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
            # BUG-229: stored here since Phase 30 and read by nothing, so a mode's instructions
            # were dropped and the thread reported them honoured.
            behaviour=self.behaviour,
            before=self.before,
        )
        # Held while the turn runs so `steer` has something to deliver into (ENH-046).
        self._loop = loop
        try:
            observation = await loop.work(prompt)
        finally:
            loop._turning = False  # noqa: SLF001 — two halves of this adapter
            self._loop = None
            # Everything but the role, so the next turn reads what this one said (D181, BUG-232).
            # Kept even on a failed or interrupted turn: a model that was asked something and
            # answered badly was still asked it, and a transcript with the awkward parts removed is
            # not the conversation that happened.
            self.before = tuple(loop.messages[1:])
        while isinstance(observation, ApprovalRequest):
            answer = await context.request_approval(
                observation.question,
                step=observation.handle,
                about=(observation.component, observation.inputs),
            )
            if isinstance(answer, Parked):
                # **The turn ends here, and the host speaks** (BUG-228). `stop_reason` is
                # `parked`: that is what a host keys on. The text is the kit's plainest
                # description of why the turn stopped — never the note written for the agent
                # (which addressed it in the second person, and which one model read back to
                # the person as its answer), and never the model's last words, which would
                # present something said on the way to a call as an answer to the person.
                observation = loop.finished(
                    "parked",
                    text=PARKED_TURN.format(name=observation.component or "tool"),
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
        """Words folded into the turn that is running (ENH-046, D173).

        `False` where there is nothing to steer — no turn running, or one that has already ended —
        which is the same honest answer a one-shot CLI gives. The contract is unchanged; what
        changed is that it can now be `True`.
        """
        loop = self._loop
        if loop is None:
            return False
        taken: bool = loop.steer(text)
        return taken

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
        cache_read_tokens=_optional_int(value.get("cache_read_tokens")),
        cache_write_tokens=_optional_int(value.get("cache_write_tokens")),
    )


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


__all__ = ["ModelAgent"]


def _selects_model(port: Any) -> bool:
    """Whether this `ModelPort` can answer a request naming a model other than its own (D180).

    Asked of the port rather than assumed, and **defaulting to true**: `model` is a `ModelRequest`
    field, so a port is expected to read it, and a port that says nothing is taken at its word. The
    kit's own adapter is the one that has to be accurate, and it is — `LangChainModel.selects_model`
    is false exactly where it wraps a chat model it cannot re-specify.
    """
    return bool(getattr(port, "selects_model", True))
