"""The run's registry, offered to an agent that owns its own loop (D42, D62).

A provider — a CLI on a subscription, an in-process double — calls a tool by name. The call is
**routed through the run**: composed as one step, spawned as a child run under a ceiling carved
from what the parent has left, judged by the policy, recorded, and — when the policy asks — put to
the host live while the caller waits (D58). What comes back is an observation in the loop's own
vocabulary. Nothing here knows what transport the call arrived on; the recording adapter puts an
MCP server and a socket in front of it, a test calls it directly.

The routing lived inside the recording adapter's server until the thread (D62) needed it without
a socket. Loop logic belongs to the loop.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any, Protocol

from pydantic import JsonValue

from shadow_hdk.kernel import Binding, Ceiling, Composition, Invoke, Observation, Refused
from shadow_hdk.kernel.events import ApprovalRequested, Observed
from shadow_hdk.kernel.events import Refused as RefusedEvent
from shadow_hdk.kernel.ports import ToolSource
from shadow_hdk.runtime.approvals import Parked
from shadow_hdk.runtime.bindings import RunContext

REFUSED_NOT_RUNNING = "no turn is running, so there is nothing to call into"
PARKED_REASON = (
    "not now: the person will be asked about {name} later, and the call is kept — it runs once "
    "they approve, and you will be told what came of it at your next turn. Say what you "
    "proposed and why, then stop."
)


class Offer(Protocol):
    """What a `Thread` needs from whatever offers its registry to the agent (D62).

    `attach`/`detach` bind the run the calls route through — a thread attaches each turn's run
    and detaches after it. `served` yields the tool sources the agent is opened with: a socket
    offer yields the relay; an in-process offer yields nothing, because the agent reaches
    `call` directly.
    """

    @property
    def name(self) -> str: ...

    def attach(self, context: RunContext) -> None: ...

    def detach(self) -> None: ...

    def served(self) -> Any: ...

    async def call(
        self, name: str, arguments: Mapping[str, JsonValue] | None = None
    ) -> Observation: ...

    async def changed(self) -> None:
        """The catalogue changed under a resident agent — the mode flipped, a root was added —
        and whoever holds a list of it should list again (BUG-032; MCP's
        `notifications/tools/list_changed`). An in-process offer has nothing to tell."""
        ...


class Routing:
    """The routing itself: one counter, one name, one attached run at a time."""

    def __init__(self, *, name: str = "tools", withhold: frozenset[str] | set[str] = frozenset()):
        self.name = name
        self.calls = 0
        self._withheld = frozenset(withhold)
        self._context: RunContext | None = None

    @property
    def context(self) -> RunContext | None:
        return self._context

    @property
    def withheld(self) -> frozenset[str]:
        return self._withheld

    def attach(self, context: RunContext) -> None:
        self._context = context

    def detach(self) -> None:
        self._context = None

    async def call(
        self, name: str, arguments: Mapping[str, JsonValue] | None = None
    ) -> Observation:
        """Route the agent's call through the attached run, and hand back what came out."""
        context = self._context
        if context is None:
            return Refused(REFUSED_NOT_RUNNING)
        if name in self._withheld:
            return Refused(f"no component named {name!r}")
        self.calls += 1
        # `__` and not `:` — LangGraph reserves the colon for checkpoint namespaces, so a step id
        # carrying one fails at graph construction.
        step = f"{self.name}__{name}__{self.calls}"
        composition = Composition(
            (
                Invoke(
                    id=step,
                    component=name,
                    inputs=tuple(
                        Binding(name=key, value=value) for key, value in (arguments or {}).items()
                    ),
                ),
            )
        )
        remaining = (await context.remaining_now()).ceiling
        if remaining.max_steps <= 0:
            return Refused("the run has no steps left")
        # **Reserve what this call can cost, not everything that is left** (BUG-024). A component
        # whose effects say it does not cost money reserves none; one that does reserves what
        # remains, which is the honest worst case.
        costs = await _costs(context, name)
        # **Through the runtime's own children, never a local `run()`** (D51). A child spawned this
        # way is held when it parks, and `send` resumes it with a ceiling clamped to what the
        # parent still has.
        ceiling = Ceiling(
            max_steps=min(2, remaining.max_steps),
            max_wall_seconds=remaining.max_wall_seconds,
            max_cost_cents=remaining.max_cost_cents if costs else 0,
        )
        handle, events = await context.children.spawn(composition, ceiling)
        observation, question = outcome_of(events, step)
        while observation is None and question is not None:
            # **The policy asked, and the child is waiting on this very call** (BUG-021, D58). The
            # nested run parked; this step cannot — it is what keeps the provider alive — so the
            # request is put to the host live, naming the call itself (BUG-026) *and its step*
            # (BUG-040: raised from the socket's task, the context has no current step, and the
            # record said `""`), and the held child is sent the answer.
            answer = await context.request_approval(
                question, step=step, about=(name, dict(arguments or {}))
            )
            if isinstance(answer, Parked):
                # **Kept, not answered** (D88). The child stays asleep in the checkpointer with
                # the question on it; whoever keeps the record settles it later and tells the
                # provider then. Now the provider hears that, and is asked to stop.
                return Refused(PARKED_REASON.format(name=name))
            if not await context.children.is_held(handle):
                break
            observation, question = outcome_of(await context.children.send(handle, answer), step)
        return (
            observation if observation is not None else Refused("the call produced no observation")
        )


async def _costs(context: RunContext, name: str) -> bool:
    for registration in await context.visible():
        if registration.id == name:
            return bool(registration.component.effects.costs)
    return True  # unknown is the worst case


def outcome_of(events: list[Any], step: str) -> tuple[Observation | None, str | None]:
    """What the child's step observed, or what it asked."""
    observation: Observation | None = None
    question: str | None = None
    for event in events:
        if isinstance(event, Observed) and event.step == step:
            observation = event.observation
        elif isinstance(event, RefusedEvent) and event.step == step:
            # A refusal emits one event, not two: the refusal *is* the record of what happened.
            observation = Refused(event.reason)
        elif isinstance(event, ApprovalRequested) and event.step == step:
            question = event.question
    return observation, question


class InProcessOffer(Routing):
    """The registry offered to an agent in this process: it calls `call` directly, so there is
    nothing to serve and no tool source to hand it."""

    async def changed(self) -> None:
        return None

    @asynccontextmanager
    async def served(self) -> AsyncIterator[tuple[ToolSource, ...]]:
        yield ()


__all__ = [
    "PARKED_REASON",
    "REFUSED_NOT_RUNNING",
    "InProcessOffer",
    "Offer",
    "Routing",
    "outcome_of",
]
