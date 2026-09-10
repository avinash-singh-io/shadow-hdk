"""The model-driven loop, as a component (D1).

One turn is: show the model what it can see, read what it wants to do, turn that into a
**composition**, and run it. Running it is `run()` — the same entry point a host uses — so a turn's
work is a child run with its own lease, its own events and its own `Composed`, and the plan the
model made is on the record whether or not it worked.

What the model may do is the *pattern's* decision, not this class's: `single` offers `propose` and
`done` and nothing else, so it cannot change its own shape. A pattern that offers `compose` can.
"""

from __future__ import annotations

from collections.abc import Sequence

from shadow_hdk.adapters.agent.catalogue import describe_for, thin
from shadow_hdk.adapters.agent.meta import BY_NAME
from shadow_hdk.adapters.agent.pattern import (
    COMPACT,
    COMPOSE,
    DESCRIBE,
    DONE,
    MAILBOX,
    PROPOSE,
    RELEASE,
    SEND,
    SPAWN,
    Pattern,
)
from pydantic import JsonValue

from shadow_hdk.kernel.components import (
    Component,
    Interface,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.composition import Await, Binding, Composition, FanOut, Invoke, Step
from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.events import Event
from shadow_hdk.kernel.observations import (
    Acted,
    Completed,
    Failed,
    Observation,
    Proposal,
    Refused,
)
from shadow_hdk.kernel.ports import (
    ComponentPort,
    Message,
    ModelRequest,
    ToolCall,
    Usage,
)
from shadow_hdk.runtime import RunContext, current_run, run

BRIEF_SCHEMA: dict[str, JsonValue] = {
    "type": "object",
    "properties": {"brief": {"type": "string"}},
    "required": ["brief"],
}


class AgentComponent(ComponentPort):
    def __init__(
        self,
        *,
        pattern: Pattern,
        effects: EffectProfile,
        name: str = "agent",
        description: str = "Work on a brief, using the tools available.",
        registration_id: RegistrationId | None = None,
        registered_by: str = "host",
        at: str = "",
    ) -> None:
        self.pattern = pattern
        self._registration = Registration(
            id=registration_id or name,
            component=Component(
                interface=Interface(
                    name=name,
                    description=description,
                    input_schema=BRIEF_SCHEMA,
                    output_schema={"type": "object"},
                ),
                effects=effects,
                provenance=Provenance(registered_by=registered_by, adapter="agent", at=at),
                labels=frozenset({"agent"}),
            ),
        )

    @property
    def registration_id(self) -> RegistrationId:
        return self._registration.id

    async def registrations(self) -> Sequence[Registration]:
        return [self._registration]

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        if registration != self._registration.id:
            return Failed(f"no component registered as {registration!r}")
        context = current_run()
        if context is None:
            return Failed("an agent is a component: it runs inside a run, never on its own")
        brief = inputs.get("brief") if isinstance(inputs, dict) else None
        if not isinstance(brief, str):
            return Failed("an agent needs a brief: a string saying what to work on")
        return await _Turnwise(self, context).work(brief)


class _Turnwise:
    """One invocation's worth of state.

    A new one per call, so nothing survives an invocation that should not.
    """

    def __init__(self, agent: AgentComponent, context: RunContext) -> None:
        self.agent = agent
        self.pattern = agent.pattern
        self.ctx = context
        self.messages: list[Message] = []
        self.spent = Usage(0, 0, 0)
        self.nudged = False
        self.proposed = 0
        self.turns = 0
        self.helpers: dict[str, str] = {}
        """The model's own names for its helpers — `@1`, `@2` — over the runtime's run ids. A
        model asked to carry a uuid between turns will eventually carry the wrong one."""

    # ------------------------------------------------------------------ the loop

    async def work(self, brief: str) -> Observation:
        self.messages = [Message("system", self.pattern.system), Message("user", brief)]
        for turn in range(self.pattern.max_turns):
            if self.ctx.remaining().ceiling.max_steps <= 0:
                return self.finished("lease_exhausted")
            self.turns = turn + 1
            response = await self.ctx.ports.model.complete(
                ModelRequest(tuple(self.messages), await self.catalogue())
            )
            self.charge(response.usage)
            if not response.tool_calls:
                self.messages.append(Message("assistant", response.text))
                return self.finished("answered", text=response.text)
            self.messages.append(Message("assistant", response.text))

            for call in [c for c in response.tool_calls if c.name == PROPOSE]:
                await self.propose(call)
            for call in [c for c in response.tool_calls if c.name == DESCRIBE]:
                await self.describe(call)
            for call in [c for c in response.tool_calls if c.name == COMPACT]:
                await self.compact(call)
            for call in [c for c in response.tool_calls if c.name in (SPAWN, SEND, RELEASE)]:
                await self.helper(call)
            done = next((c for c in response.tool_calls if c.name == DONE), None)
            if done is not None:
                verdict = self.done(done)
                if verdict is not None:
                    return verdict
                continue

            composition = self.compose(response.tool_calls)
            if composition is None:
                continue
            await self.carry_out(composition, response.tool_calls)
        return self.finished("out_of_turns")

    # ------------------------------------------------------------------ the moves

    async def catalogue(self) -> tuple[Interface, ...]:
        """What the model sees: the policy's answer, this role's names, and the pattern's verbs.

        A registered tool named like a meta-tool is refused here, before the model is asked
        (BUG-001): every call whose name is in `BY_NAME` is routed to the meta handler, enabled by
        the pattern or not, so such a tool would be shadowed silently. A deployment's naming is not
        the model's to work around, and a rename on the fly would lie about the registration's id.
        """
        visible = [
            registration
            for registration in await self.ctx.visible()
            if registration.id != self.agent.registration_id
        ]
        colliding = [r for r in visible if r.component.interface.name in BY_NAME]
        if colliding:
            named = "; ".join(
                f"registration {r.id!r} is named like the meta-tool {r.component.interface.name!r}"
                for r in colliding
            )
            raise ValueError(f"a registered tool would be shadowed by a meta-tool: {named}")
        tools = [
            registration.component.interface
            for registration in visible
            if self.pattern.shows(registration.component.interface.name)
        ]
        # Thinned only above the pattern's threshold (D13). The meta-tools are never thinned:
        # they are the model's own verbs, and a verb it has to ask about is a verb it will not use.
        return thin(tools, self.pattern) + tuple(
            BY_NAME[name] for name in sorted(self.pattern.meta_tools)
        )

    async def propose(self, call: ToolCall) -> None:
        arguments = call.arguments if isinstance(call.arguments, dict) else {}
        await self.ctx.propose(
            Proposal(
                kind=str(arguments.get("kind", "proposal")),
                payload=arguments.get("payload"),
                provenance=Provenance(
                    registered_by=self.ctx.run_id, adapter="agent", at=self.ctx.now()
                ),
            )
        )
        self.proposed += 1
        self.messages.append(Message("tool", "proposed", tool_call_id=call.id))

    async def helper(self, call: ToolCall) -> None:
        """Start, message or let go of a helper — Phase 7's `children` verbs, offered to the model.

        The **shape of the child is decided here**, which is why this could not land with the
        runtime half (D3): a helper is *the named agent given a brief, then a wait on the mailbox*.
        That composition is exactly D16's held child — a parked run — written down.

        Every failure is an answer rather than a crash (D7): a handle the model invented, an agent
        that is not registered, a deployment with no mailbox. It gets told, and keeps its turn.
        """
        arguments = call.arguments if isinstance(call.arguments, dict) else {}
        try:
            answer = await self._helper(call.name, arguments)
        except KeyError as unknown:
            answer = f"there is no helper {unknown.args[0]!r}; spawn one first"
        except Exception as failed:  # noqa: BLE001 — the model's mistake is data, not a traceback
            answer = f"that did not work: {type(failed).__name__}: {failed}"
        self.messages.append(Message("tool", answer, tool_call_id=call.id))

    async def _helper(self, verb: str, arguments: dict[str, JsonValue]) -> str:
        if verb == SPAWN:
            agent = str(arguments.get("agent", ""))
            brief = str(arguments.get("brief", ""))
            child = Composition(
                (
                    Invoke("brief", agent, (Binding(name="brief", value=brief),)),
                    Await("inbox", MAILBOX),
                )
            )
            handle, events = await self.ctx.children.spawn(child, self.ctx.remaining().ceiling)
            self.helpers[f"@{len(self.helpers) + 1}"] = handle
            name = f"@{len(self.helpers)}"
            if handle not in self.ctx.children.held:
                return f"{name} finished rather than waiting: {_last_observation(events)}"
            return f"{name} is held and waiting. Send it something, or release it."
        handle = self.helpers[str(arguments.get("handle", ""))]
        if verb == RELEASE:
            await self.ctx.children.release(handle)
            return "released"
        events = await self.ctx.children.send(handle, str(arguments.get("message", "")))
        return f"answered: {_last_observation(events)}"

    async def compact(self, call: ToolCall) -> None:
        """The model summarises its own transcript (`09` §5).

        Two things happen and neither is a runtime power. The summary goes to the **sink** as a
        proposal, and whoever implements the sink decides whether it is kept and with what
        provenance — this adapter writes it nowhere. And the transcript this loop carries is
        shortened, because a compaction that proposed a summary and then kept talking to the whole
        history would have saved nothing.

        What it may drop is the **middle**. The role the agent was given and the request it was
        asked to answer are not the model's to summarise away.
        """
        arguments = call.arguments if isinstance(call.arguments, dict) else {}
        summary = str(arguments.get("summary", ""))
        await self.ctx.propose(
            Proposal(
                kind="compaction",
                payload=summary,
                provenance=Provenance(
                    registered_by=self.ctx.run_id, adapter="agent", at=self.ctx.now()
                ),
            )
        )
        # The role and the brief — `work()` puts them first and in that order.
        kept = self.messages[:2]
        self.messages = [
            *kept,
            Message("assistant", f"Summary of what happened before this point: {summary}"),
            Message("tool", "compacted", tool_call_id=call.id),
        ]

    async def describe(self, call: ToolCall) -> None:
        """Answer what one tool takes — from `visible()` only, so a describe cannot reach past what
        the policy left."""
        arguments = call.arguments if isinstance(call.arguments, dict) else {}
        answer = describe_for(str(arguments.get("name", "")), await self.ctx.visible())
        text = answer if isinstance(answer, str) else dump(answer, Interface)
        self.messages.append(Message("tool", text, tool_call_id=call.id))

    def done(self, call: ToolCall) -> Observation | None:
        """`None` means *not yet* — the floor is not met and this is the one nudge it gets."""
        if not self.ctx.floor_met() and not self.nudged:
            self.nudged = True
            self.messages.append(Message("tool", self.pattern.nudge, tool_call_id=call.id))
            return None
        arguments = call.arguments if isinstance(call.arguments, dict) else {}
        summary = str(arguments.get("summary", ""))
        reason = "done" if self.ctx.floor_met() else "gave_up"
        return self.finished(reason, text=summary)

    def compose(self, calls: tuple[ToolCall, ...]) -> Composition | None:
        """Turn what the model asked for into a plan. One call is a plan of one step."""
        authored = next((c for c in calls if c.name == COMPOSE), None)
        if authored is not None:
            try:
                composition = load(_as_json(authored.arguments), Composition)
            except Exception as invalid:  # noqa: BLE001 — the model's mistake, not a crash
                self.messages.append(
                    Message(
                        "tool", f"that plan does not parse: {invalid}", tool_call_id=authored.id
                    )
                )
                return None
            return composition
        work = [c for c in calls if c.name not in BY_NAME]
        if not work:
            return None
        steps = tuple(_invoke(call) for call in work)
        return Composition(steps if len(steps) == 1 else (FanOut("fan", steps),))

    async def carry_out(self, composition: Composition, calls: tuple[ToolCall, ...]) -> None:
        # **Whatever is left, not a guess.** The first version carved `len(steps) + 1`, which is
        # right for tool calls and wrong the moment a step is itself an agent: a sub-agent needs
        # steps for its own turns and got two, then died `lease_exhausted` — silently, because a
        # lease ending a run is not an error. Turns are sequential and each settles before the
        # next, so the parent's remaining is the honest ceiling; its own still bounds the lot.
        ceiling = self.ctx.remaining().ceiling
        observed: dict[str, Observation] = {}
        async for event in run(
            composition, self.ctx.ports, options=self.ctx.spawn_options(ceiling)
        ):
            if event.kind == "observed":
                observed[event.step] = event.observation
            elif event.kind == "refused":
                # **A refusal emits one event, not two** — the decision taken when the governed step
                # was written, and the same trap the RecordingServer fell into in Phase 5. Watching
                # only for `observed` left a refused call answered with "that step did not run": no
                # reason, and indistinguishable from a step that never happened. A survey of other
                # agent systems found this to be the single most commonly filed bug in approval
                # implementations, so it is worth the four lines and the paragraph.
                observed[event.step] = Refused(event.reason)
        for call in calls:
            if call.name in BY_NAME:
                continue
            observation = observed.get(call.id)
            self.messages.append(Message("tool", _readable(observation), tool_call_id=call.id))

    # ------------------------------------------------------------------ bookkeeping

    def charge(self, usage: Usage | None) -> None:
        """Accumulate what the model cost, so the parent's meter can charge it (`_usage_of`)."""
        if usage is None:
            return
        self.spent = Usage(
            input_tokens=_add(self.spent.input_tokens, usage.input_tokens),
            output_tokens=_add(self.spent.output_tokens, usage.output_tokens),
            cost_cents=_add(self.spent.cost_cents, usage.cost_cents),
        )

    def finished(self, reason: str, *, text: str = "") -> Observation:
        """What the agent hands back.

        `turns` is model calls made, whichever way it ended: a run that stopped for its lease and
        one that answered are told apart by `reason`, never by a gap in the numbers.
        """
        return Completed(
            {
                "text": text or _last_words(self.messages),
                "reason": reason,
                "turns": self.turns,
                "proposals": self.proposed,
                "usage": {
                    "input_tokens": self.spent.input_tokens,
                    "output_tokens": self.spent.output_tokens,
                    "cost_cents": self.spent.cost_cents,
                },
            }
        )


# ---------------------------------------------------------------- small helpers


def _invoke(call: ToolCall) -> Step:
    arguments = call.arguments if isinstance(call.arguments, dict) else {}
    return Invoke(
        id=call.id,
        component=call.name,
        inputs=tuple(Binding(name=key, value=value) for key, value in arguments.items()),
    )


def _as_json(arguments: JsonValue) -> str:
    import json

    return json.dumps(arguments)


def _last_observation(events: Sequence[Event]) -> str:
    """What a helper ended up saying, for the model to read."""
    seen = [e for e in events if e.kind == "observed"]
    return _readable(seen[-1].observation) if seen else "nothing"


def _readable(observation: Observation | None) -> str:
    if observation is None:
        return "that step did not run"
    if isinstance(observation, Completed):
        return _as_json(observation.output)
    if isinstance(observation, Acted):
        # The receipt, not the grounds: what the world called it and how it ended are the model's
        # to cite; the lease and argv it ran under are the auditor's (R9).
        receipt = {
            "foreign_id": observation.foreign_id,
            "idempotency_key": observation.idempotency_key,
            "exit": observation.exit,
        }
        return _as_json({"acted": receipt})
    why = getattr(observation, "reason", None) or getattr(observation, "error", "")
    return f"{observation.kind}: {why}"


def _last_words(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.role == "assistant" and message.content:
            return message.content
    return ""


def _add(left: int | None, right: int | None) -> int | None:
    if left is None or right is None:
        return None
    return left + right


__all__ = ["AgentComponent"]
