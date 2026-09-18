"""`compose`: a plan proposed as a component (D110).

The kit's own loop authors a plan through a meta-tool; a resident CLI cannot reach a meta-tool —
it reaches the run's registry, over the socket, like any tool. So planning is a **component**:
offered like any other, no effects (proposing is not an effect; running is), the composition as
its input, the plan's results as its output. The precedent is D55, where the skill registry became
a component "so choosing is on the record and reaches every host".

One path, whoever proposes: the loop's `compose` meta-tool and this component both hand the plan
to `children.spawn`, where admission lives (D108). Through the offer, a CLI's call becomes a
one-step child whose step spawns the plan as a grandchild — the nesting a sub-agent already has;
nothing new in the runtime. A refused plan is a `Refused` observation naming every mismatch
(D111); a plan that does not parse is a `Failed`, never a crash.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from pydantic import JsonValue

from shadow_hdk.kernel import (
    ApprovalRequest,
    Completed,
    Component,
    Composition,
    EffectProfile,
    Failed,
    Interface,
    Observation,
    Provenance,
    Refused,
    Registration,
)
from shadow_hdk.kernel.contracts import dump, json_schema, load
from shadow_hdk.kernel.ports import Allow, ComponentPort
from shadow_hdk.runtime.approvals import Amend
from shadow_hdk.runtime.bindings import current_run
from shadow_hdk.runtime.children import PlanNotAdmitted

COMPOSE = "compose"


class PlanComponents(ComponentPort):
    """One component: `compose(steps) -> {steps: {id: observation}}`."""

    def __init__(self, *, at: str = "2026-09-18T00:00:00+00:00") -> None:
        schema = dict(json_schema("Composition"))
        schema["description"] = (
            "A plan: steps over the tools you have — invoke, sequence, fan_out (in parallel), "
            "until (loop with a stop), await. It is admitted against this run's limits before "
            "anything runs, and every step is judged as it runs."
        )
        self._registrations: tuple[Registration, ...] = (
            Registration(
                id=COMPOSE,
                component=Component(
                    interface=Interface(
                        name=COMPOSE,
                        description=(
                            "Propose a plan of several steps and run it: the steps you name, "
                            "over the tools you have, in sequence or in parallel. The plan is "
                            "admitted as a whole first — its depth, fan-out, size and every tool "
                            "it names — and you see every result, or every reason it was refused."
                        ),
                        input_schema=schema,
                        output_schema={
                            "type": "object",
                            "properties": {"steps": {"type": "object"}},
                        },
                    ),
                    effects=EffectProfile(),
                    provenance=Provenance(registered_by="runtime", adapter="planning", at=at),
                    labels=frozenset({"tool", "plan"}),
                ),
            ),
        )

    async def registrations(self) -> Sequence[Registration]:
        return list(self._registrations)

    async def invoke(self, registration: str, inputs: JsonValue) -> Observation:
        if registration != COMPOSE:
            return Failed(f"no component registered as {registration!r}")
        raw: Any = inputs
        if isinstance(raw, dict) and "composition" in raw and "steps" not in raw:
            raw = raw["composition"]
        try:
            composition = load(json.dumps(raw), Composition)
        except Exception as invalid:  # noqa: BLE001 — the proposer's mistake, not a crash
            return Failed(f"that plan does not parse: {invalid}")
        context = current_run()
        if context is None:
            return Failed("compose runs inside a run, and there is none")
        # **Picking up where it parked** (D57): a step inside the plan asked, this step parked
        # with the plan's handle kept, and the host has answered — the answer goes into the held
        # plan, which continues where it stopped.
        back = await context.resumed()
        if back is not None and isinstance(back.kept, dict) and "handle" in back.kept:
            handle = str(back.kept["handle"])
            if isinstance(back.answer, Amend):
                # The person changed the plan (D116): the held plan is woken on the amended
                # composition, admitted first; refused, it stays held and this step parks again
                # on the same question.
                amended = back.answer.composition
                if not isinstance(amended, Composition):
                    amended = load(json.dumps(amended), Composition)
                answer = Allow() if back.answer.answer is None else back.answer.answer
                events = await context.children.amend(handle, amended, answer)
                if any(e.kind == "plan_refused" for e in events):
                    await context.keep(dict(back.kept))  # the same question, whole, for next time
                    component = back.kept.get("component")
                    return ApprovalRequest(
                        question=str(back.kept.get("question", "the plan is waiting")),
                        handle=str(back.kept.get("step", "")),
                        component=component if isinstance(component, str) else None,
                        inputs=back.kept.get("inputs"),
                    )
                return await self._settle(context, handle, events)
            events = await context.children.send(handle, back.answer)
            return await self._settle(context, handle, events)
        ceiling = (await context.remaining_now()).ceiling
        try:
            handle, events = await context.children.spawn(composition, ceiling, proposed_by=COMPOSE)
        except PlanNotAdmitted as refused:
            return Refused(str(refused))
        return await self._settle(context, handle, events)

    async def _settle(self, context: Any, handle: str, events: list[Any]) -> Observation:
        """What the plan's events mean for the caller — or, if a step inside asked, the question,
        which becomes this step's own (D57): the run parks here with the plan's handle kept, and
        the answer is sent into the held plan when this step is invoked again."""
        question = next(
            (e for e in events if e.kind == "approval_requested" and e.run_id == handle), None
        )
        if question is not None and await context.children.is_held(handle):
            await context.keep(
                {
                    "handle": handle,
                    "question": question.question,
                    "step": question.step,
                    "component": question.component,
                    "inputs": question.inputs,
                }
            )
            return ApprovalRequest(
                question=question.question,
                handle=question.step,
                component=question.component,
                inputs=question.inputs,
            )
        observed: dict[str, JsonValue] = {}
        for event in events:
            if event.kind == "observed":
                observed[event.step] = json.loads(dump(event.observation, Observation))
            elif event.kind == "refused":
                observed[event.step] = {"kind": "refused", "reason": event.reason}
        return Completed({"steps": observed})


def plan_components() -> PlanComponents:
    return PlanComponents()


__all__ = ["COMPOSE", "PlanComponents", "plan_components"]
