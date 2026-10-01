"""The agent's own plan, kept on the record as it changes (ENH-045, lane P's ask 8).

Half of this already existed and it was not the half a host needed. `Composed` is emitted every time
the composition changes, `PlanAdmitted`/`PlanRefused` carry a whole plan's admission (D108/D116),
and
`items()` renders steps for a client — so **what the runtime is about to do** is on the record and
rendered. What was absent is the agent's own narration: the field's to-do list, revised as it
learns,
which is the agent saying what it intends in its own words. A governed CLI had no way to say it,
because its only tools are the registry's.

**A registered component, not a runtime concept** (D171). Two reasons, and the second is the one
  that
decides it:

* The boundary rule. The *mechanism* is the kit's; a plan's *content* — what the steps are, what a
  status means, how it renders — is the product's.
* **No effects at all**, so every mode admits it, `read-only` included. An agent that had to ask
  permission to say what it intends would stop saying it, and a narration nobody can afford is worse
  than no narration.

The record carries the revisions in order for nothing extra: `Invoked.inputs` already does that. A
host reads the `update_plan` invocations and renders the latest.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from shadow_hdk.kernel.components import (
    Component,
    Interface,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.observations import Observation, Refused
from shadow_hdk.kernel.ports import ComponentPort
from shadow_hdk.runtime.environment import _completed  # noqa: PLC2701 — one builder, not two

UPDATE_PLAN = "update_plan"

ITEMS = 200
"""More items than this is not a plan, it is a data structure — refused rather than carried."""


class PlanComponents(ComponentPort):
    """`update_plan` as a tool, and the last plan it was told, for a host that wants it directly.

    The plan is kept here as well as on the record so a host attaching mid-run has something to
    render without replaying every event — the same reason a thread keeps `spent` beside the
    `Spent` events.
    """

    def __init__(self, *, registered_by: str = "host", at: str = "") -> None:
        self._provenance = Provenance(registered_by=registered_by, adapter="agent", at=at)
        self.plan: tuple[dict[str, Any], ...] = ()
        """The latest plan this run said, or empty."""
        self.revisions = 0

    async def registrations(self) -> Sequence[Registration]:
        return (
            Registration(
                id=UPDATE_PLAN,
                component=Component(
                    interface=Interface(
                        name=UPDATE_PLAN,
                        description=(
                            "Say what you intend to do, as a short list of steps, and say it again "
                            "whenever it changes. Each step has a `step` and a `status`. This "
                            "changes nothing in the world — it is how a person following along "
                            "knows where you are."
                        ),
                        input_schema={
                            "type": "object",
                            "properties": {
                                "items": {
                                    "type": "array",
                                    "description": "The steps, in the order you mean to do them.",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "step": {
                                                "type": "string",
                                                "description": "What this step is.",
                                            },
                                            "status": {
                                                "type": "string",
                                                "description": (
                                                    "Where it stands — for example `pending`, "
                                                    "`doing`, `done`, `dropped`."
                                                ),
                                            },
                                        },
                                        "required": ["step"],
                                    },
                                }
                            },
                            "required": ["items"],
                        },
                        output_schema={"type": "object"},
                    ),
                    # **Nothing at all** (D171). Every mode admits it, `read-only` included: an
                    # agent that had to ask permission to say what it intends would stop saying it.
                    effects=EffectProfile(),
                    provenance=self._provenance,
                    labels=frozenset({"plan"}),
                ),
            ),
        )

    async def invoke(self, registration: RegistrationId, inputs: Any) -> Observation:
        if registration != UPDATE_PLAN:
            return Refused(f"no component registered as {registration!r}")
        arguments = inputs if isinstance(inputs, dict) else {}
        items = arguments.get("items")
        if not isinstance(items, list):
            return Refused("a plan needs `items`, a list of {step, status}")
        if len(items) > ITEMS:
            return Refused(
                f"{len(items)} steps is not a plan anybody can follow; keep it under {ITEMS}"
            )
        kept: list[dict[str, Any]] = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                return Refused(f"step {index} is not an object with `step` and `status`")
            step = item.get("step")
            if not isinstance(step, str) or not step.strip():
                return Refused(f"step {index} needs `step`, a string saying what it is")
            # `status` is an **open string** (D172), the cut `Provider.transport` makes: a Literal
            # would change the kit's contract every time a product wants a status it did not think
            # of, and a plan's vocabulary is exactly what a product owns.
            status = item.get("status")
            kept.append(
                {"step": step.strip(), "status": str(status).strip() if status else "pending"}
            )
        self.plan = tuple(kept)
        self.revisions += 1
        return _completed({"items": len(kept), "revision": self.revisions})


def plan_components(*, registered_by: str = "host", at: str = "") -> PlanComponents:
    return PlanComponents(registered_by=registered_by, at=at)


__all__ = ["ITEMS", "UPDATE_PLAN", "PlanComponents", "plan_components"]
