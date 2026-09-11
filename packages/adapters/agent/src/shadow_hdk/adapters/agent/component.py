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

from shadow_hdk.adapters.agent.catalogue import describe_for, thin, thinned
from shadow_hdk.adapters.agent.meta import BY_NAME, use_skill_for
from shadow_hdk.adapters.agent.pattern import (
    COMPACT,
    COMPOSE,
    DESCRIBE,
    DONE,
    MAILBOX,
    MINT_SKILL,
    PROPOSE,
    RECALL,
    RELEASE,
    SEND,
    SPAWN,
    USE_SKILL,
    Pattern,
)
from shadow_hdk.adapters.agent.registry import SkillRegistry
from shadow_hdk.adapters.agent.skills import Skill, missing_for, skill_from
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
from shadow_hdk.runtime import RunContext, current_run

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
        skill: Skill | None = None,
        skills: SkillRegistry | None = None,
    ) -> None:
        self.pattern = pattern
        self.skill = skill
        self.skills = skills
        """The registry this role may choose from (D54). Names and lines ride the `use_skill` verb;
        a body arrives when chosen, after D17's check. `None` offers no verb."""
        """A team's procedure, and what it cannot do without (D17). Checked against what the policy
        leaves visible **before the first turn**, so a skill needing a component this deployment
        hides is refused for a penny rather than discovered halfway through for a pound."""
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
        self.held: dict[str, str] = {}
        """Results too large for the model's context; kept for the run, paged by `recall` (D47)."""
        self.spent = Usage(0, 0, 0)
        self.nudged = False
        self.proposed = 0
        self.using: list[str] = []
        """Skills chosen this run, in order — for the record this loop reports when it finishes."""
        self.turns = 0
        self.helpers: dict[str, str] = {}
        """The model's own names for its helpers — `@1`, `@2` — over the runtime's run ids. A
        model asked to carry a uuid between turns will eventually carry the wrong one."""

    # ------------------------------------------------------------------ the loop

    async def work(self, brief: str) -> Observation:
        skill = self.agent.skill
        if skill is not None:
            # Before the first turn, which is the whole value of the check (D17, BUG-012): against
            # `visible()`, the same computation the catalogue comes from, so a skill can never be
            # told it may use something the model would not be offered.
            missing = missing_for(skill, await self.ctx.visible())
            if missing:
                return self.finished(
                    "skill_unmet",
                    text=(
                        f"the skill {skill.name!r} needs "
                        f"{', '.join(sorted(missing))}, which this deployment does not offer"
                    ),
                )
        self.messages = [Message("system", self._role(skill)), Message("user", brief)]
        for turn in range(self.pattern.max_turns):
            if (await self.ctx.remaining_now()).ceiling.max_steps <= 0:
                return self.finished("lease_exhausted")
            self.turns = turn + 1
            # Built outside the catch on purpose: `catalogue()` refuses a tool named like a
            # meta-tool (BUG-001), and that is our refusal, not a provider's failure.
            request = ModelRequest(tuple(self.messages), await self.catalogue())
            try:
                response = await self.ctx.ports.model.complete(request)
            except Exception as broken:  # noqa: BLE001 — the money is the point, not the crash
                # **Spend that happened is spend that is recorded** (D33, BUG-012). This used to
                # throw straight out of the component, and `step.py` turns that into `Failed` (D7)
                # — an observation with nowhere to carry usage — so every paid turn before the
                # break was charged to nobody. It ends the way this loop ends every other way it
                # stops early: `Completed`, with a `reason` and what it spent.
                #
                # `Exception`, not `BaseException`: a host cancelling a run (D15) travels as
                # `CancelledError`, and catching that would turn *stop* into *carry on*.
                self.turns -= 1
                return self.finished("provider_failed", text=f"{type(broken).__name__}: {broken}")
            self.charge(response.usage)
            # **Why before what** (D45): the thought goes on the record ahead of the calls it led
            # to, so a reader — or a projection — sees the reasoning above the invocation.
            await self.ctx.reasoned(response.reasoning)
            if not response.tool_calls:
                self.messages.append(Message("assistant", response.text))
                return self.finished("answered", text=response.text)
            # With the calls it made: a tool result whose call is in no message is rejected by
            # every provider, and a model that cannot see what it called cannot reason about it.
            self.messages.append(
                Message("assistant", response.text, tool_calls=response.tool_calls)
            )

            for call in [c for c in response.tool_calls if c.name == PROPOSE]:
                await self.propose(call)
            for call in [c for c in response.tool_calls if c.name == DESCRIBE]:
                await self.describe(call)
            for call in [c for c in response.tool_calls if c.name == USE_SKILL]:
                await self.use_skill(call)
            for call in [c for c in response.tool_calls if c.name == MINT_SKILL]:
                await self.mint_skill(call)
            for call in [c for c in response.tool_calls if c.name == RECALL]:
                self.recall(call)
            for call in [c for c in response.tool_calls if c.name == COMPACT]:
                await self.compact(call)
            for call in [c for c in response.tool_calls if c.name in (SPAWN, SEND, RELEASE)]:
                await self.helper(call)
            done = next((c for c in response.tool_calls if c.name == DONE), None)
            if done is not None:
                verdict = await self.done(done)
                if verdict is not None:
                    return verdict
                continue

            composition = self.compose(response.tool_calls)
            if composition is None:
                continue
            await self.carry_out(composition, response.tool_calls)
        return self.finished("out_of_turns")

    # ------------------------------------------------------------------ the moves

    def _role(self, skill: Skill | None) -> str:
        """The pattern says how this role works; the skill says what this piece of work is.

        One system message rather than two: several providers accept only one, and a procedure
        split from the role it runs under reads to the model as two voices disagreeing.
        """
        if skill is None:
            return self.pattern.system
        return f"{self.pattern.system}\n\n{skill.prompt}"

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
            and self._within_the_ceiling(registration)
        ]
        # Thinned only above the pattern's threshold (D13). The meta-tools are never thinned:
        # they are the model's own verbs, and a verb it has to ask about is a verb it will not use.
        # **And `describe` is offered whenever thinning is in effect**, whether the pattern enabled
        # it or not: a thinned entry has no schema, and a mechanism offered by halves is a lie.
        verbs = set(self.pattern.meta_tools)
        if thinned(tools, self.pattern):
            verbs.add(DESCRIBE)
        if self.pattern.offload_over is not None:
            verbs.add(RECALL)  # a handle the model cannot follow is worse than the flood
        # **Skills ride the verb** (D55): the registry's names and lines are on `use_skill` itself,
        # rebuilt each turn so a skill minted a turn ago is there. Offered whenever there is one to
        # choose, whether the pattern named the verb or not — a registry nobody can reach is a
        # directory. `mint_skill` is the pattern's to grant: writing procedures is a power.
        listing = await self.agent.skills.listing() if self.agent.skills is not None else ()
        verbs.discard(USE_SKILL)
        if self.agent.skills is None:
            verbs.discard(MINT_SKILL)
        offered = [BY_NAME[name] for name in sorted(verbs)]
        if listing:
            offered.append(use_skill_for(listing))
        return thin(tools, self.pattern) + tuple(offered)

    def _within_the_ceiling(self, registration: Registration) -> bool:
        """Whether this role could ever be permitted to use it (BUG-012).

        Discovery, not permission — but the two must agree, or the model is offered a tool whose
        every use is refused and spends its turns learning that. Permission is enforced separately,
        because a plan may name a component nobody offered.
        """
        if self.pattern.ceiling is None:
            return True
        return registration.component.effects.narrows(self.pattern.ceiling)

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
            handle, events = await self.ctx.children.spawn(
                child, (await self.ctx.remaining_now()).ceiling
            )
            self.helpers[f"@{len(self.helpers) + 1}"] = handle
            name = f"@{len(self.helpers)}"
            if not await self.ctx.children.is_held(handle):
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
        the policy left. A skill's name is answered too: its line, its needs and its body, without
        loading it — a look, not a choice."""
        arguments = call.arguments if isinstance(call.arguments, dict) else {}
        name = str(arguments.get("name", ""))
        answer = describe_for(name, await self.ctx.visible())
        skill = await self.agent.skills.find(name) if self.agent.skills is not None else None
        if isinstance(answer, str) and skill is not None:
            text = _skill_text(skill, loaded=False)
        else:
            text = answer if isinstance(answer, str) else dump(answer, Interface)
        self.messages.append(Message("tool", text, tool_call_id=call.id))

    async def use_skill(self, call: ToolCall) -> None:
        """The act of choosing (D55), and where D17's check runs: against `visible()`, so a skill
        needing what this run does not offer is refused by name and its body never arrives."""
        arguments = call.arguments if isinstance(call.arguments, dict) else {}
        name = str(arguments.get("name", ""))
        registry = self.agent.skills
        skill = await registry.find(name) if registry is not None else None
        if skill is None:
            names = ", ".join(n for n, _ in (await registry.listing() if registry else ()))
            text = f"there is no skill named {name!r}; the skills are: {names or 'none'}"
        else:
            missing = missing_for(skill, await self.ctx.visible())
            if missing:
                text = (
                    f"the skill {name!r} needs {sorted(missing)}, which this run does not offer; "
                    "it was not loaded"
                )
            else:
                self.using.append(name)
                text = _skill_text(skill, loaded=True)
        self.messages.append(Message("tool", text, tool_call_id=call.id))

    async def mint_skill(self, call: ToolCall) -> None:
        """Write a procedure down (D56). Two things happen and neither is a runtime power — the
        same shape as `compact`: the skill goes into the registry this role was handed, usable at
        once, and it goes to the **sink** as a proposal, where whoever keeps the record decides.
        This adapter writes nowhere."""
        arguments = call.arguments if isinstance(call.arguments, dict) else {}
        registry = self.agent.skills
        if registry is None:
            text = "this role has no skill registry to mint into"
        else:
            try:
                needs = arguments.get("needs", [])
                data = {
                    "name": arguments.get("name", ""),
                    "description": arguments.get("description", ""),
                    "prompt": arguments.get("prompt", ""),
                    "needs": [str(n) for n in needs] if isinstance(needs, list) else [],
                }
                minted = registry.minted.add(skill_from(data, where=MINT_SKILL, source="minted"))
            except ValueError as malformed:
                text = f"not minted: {malformed}"
            else:
                await self.ctx.propose(
                    Proposal(
                        kind="skill",
                        payload={
                            "name": minted.name,
                            "description": minted.description,
                            "prompt": minted.prompt,
                            "needs": sorted(minted.needs),
                        },
                        provenance=Provenance(
                            registered_by=self.ctx.run_id, adapter="agent", at=self.ctx.now()
                        ),
                    )
                )
                text = (
                    f"minted {minted.name!r}: usable now with `{USE_SKILL}`, and proposed for "
                    "keeping — whether it is kept is not yours to decide"
                )
        self.messages.append(Message("tool", text, tool_call_id=call.id))

    def offered(self, observation: Observation | None) -> str:
        """What the model sees of a result — the whole of it, or a handle if it is large (D47).

        The record and the sink saw the whole observation already; this is about the *model's*
        context, which is re-sent on every turn after this one. Past the pattern's threshold the
        model gets a handle, the size, a preview and the verb to page the rest. Held here, in
        memory, for the run: the runtime has no write path and offloading is not a reason to grow
        one.
        """
        text = _readable(observation)
        over = self.pattern.offload_over
        if over is None or len(text) <= over:
            return text
        handle = f"result-{len(self.held) + 1}"
        self.held[handle] = text
        preview = text[: min(over // 4, 800)]
        return _as_json(
            {
                "offloaded": handle,
                "size": len(text),
                "preview": preview,
                "how": f"call `{RECALL}` with this handle, a start and a length to read more",
            }
        )

    def recall(self, call: ToolCall) -> None:
        """A slice of a held result. A handle nobody issued is a sentence, not a crash — the model
        made it up, and telling it so is cheaper than ending the run."""
        arguments = call.arguments if isinstance(call.arguments, dict) else {}
        handle = str(arguments.get("handle", ""))
        if (whole := self.held.get(handle)) is None:
            self.messages.append(
                Message("tool", f"no offloaded result is called {handle!r}", tool_call_id=call.id)
            )
            return
        start = max(0, int(arguments.get("start", 0) or 0))
        length = max(1, int(arguments.get("length", 4_000) or 4_000))
        self.messages.append(Message("tool", whole[start : start + length], tool_call_id=call.id))

    async def done(self, call: ToolCall) -> Observation | None:
        """`None` means *not yet* — the floor is not met and this is the one nudge it gets."""
        if not await self.ctx.floor_met_now() and not self.nudged:
            self.nudged = True
            self.messages.append(Message("tool", self.pattern.nudge, tool_call_id=call.id))
            return None
        arguments = call.arguments if isinstance(call.arguments, dict) else {}
        summary = str(arguments.get("summary", ""))
        reason = "done" if await self.ctx.floor_met_now() else "gave_up"
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
        ceiling = (await self.ctx.remaining_now()).ceiling
        observed: dict[str, Observation] = {}
        # **Through the runtime, never a local `run()`** (D51). A composition the agent authors is
        # a child run: spawned where the record is, with the pattern's ceiling crossing as data and
        # applied there as a second gate. A host-side nested run — what this did until Phase 23 —
        # put the child's events on a stream nobody reads when the agent is on the far side of a
        # wire, and was the one thing that kept the agent from running there at all.
        _handle, events = await self.ctx.children.spawn(
            composition, ceiling, within=self.pattern.ceiling, within_name=self.pattern.name
        )
        for event in events:
            if event.kind == "observed":
                observed[event.step] = event.observation
            elif event.kind == "refused":
                # **A refusal emits one event, not two** — the decision taken when the governed step
                # was written, and the same trap the RecordingServer fell into in Phase 5. Watching
                # only for `observed` left a refused call answered with "that step did not run".
                observed[event.step] = Refused(event.reason)
        for call in calls:
            if call.name == COMPOSE:
                # **The plan's own call is answered with the whole plan** (BUG-012). Its steps are
                # named by the model — `s1`, `s2` — and belong to no tool call, so matching by
                # `call.id` found nothing and the loop skipped `compose` as a meta-tool. That left
                # the call unanswered, which is the dangling tool call every provider rejects, and
                # broke this interface's own promise that *you see every result*.
                self.messages.append(
                    Message("tool", _readable_plan(composition, observed), tool_call_id=call.id)
                )
                continue
            if call.name in BY_NAME:
                continue
            observation = observed.get(call.id)
            self.messages.append(Message("tool", self.offered(observation), tool_call_id=call.id))

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


def _readable_plan(composition: Composition, observed: dict[str, Observation]) -> str:
    """Every step of an authored plan, by the model's own name for it.

    Named rather than positional because a plan is not always a straight line — a `FanOut` settles
    in whatever order its branches finish, and a `Until` runs a step more than once. The name is the
    only thing that survives all three, and it is what the model wrote and can refer to next turn.

    A step with no observation is reported as such instead of being left out: *this did not run* is
    what a model needs to know after a plan whose earlier step failed.
    """
    return _as_json({step: _readable(observed.get(step)) for step in _step_ids(composition)})


def _step_ids(node: object) -> list[str]:
    """Every step id in a composition, in the order it is written."""
    found: list[str] = []
    steps = getattr(node, "steps", None)
    if steps is not None:
        for step in steps:
            found.extend(_step_ids(step))
        return found
    body = getattr(node, "body", None)
    if body is not None:
        found.extend(_step_ids(body))
        return found
    identifier = getattr(node, "id", None)
    if isinstance(identifier, str):
        found.append(identifier)
    return found


def _skill_text(skill: Skill, *, loaded: bool) -> str:
    verb = "Follow this procedure from here on" if loaded else "Not loaded; this is what it says"
    needs = ", ".join(sorted(skill.needs)) or "nothing in particular"
    return (
        f"Skill {skill.name!r} ({skill.source}) — {skill.description}\nNeeds: {needs}\n"
        f"{verb}:\n\n{skill.prompt}"
    )


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
