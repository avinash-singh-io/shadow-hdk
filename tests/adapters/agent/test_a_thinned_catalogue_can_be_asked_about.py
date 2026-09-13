"""A thinned entry says *call describe* — so `describe` is offered, whatever the pattern said (D13).

Thinning replaces two hundred schemas with two hundred one-liners, each ending *call `describe`
with this name to see what it takes*. That sentence is a promise. A pattern that did not enable
`describe` — and `single`, the deterministic one, does not — was making it above the threshold
anyway, and the model was told to call a verb it did not have. The existing wiring test encoded
exactly that: `meta_tools={"done"}` over a threshold of two, asserting the sentence and never
checking the verb.

So the rule: **when thinning is in effect, `describe` is offered**, because it is the other half of
the mechanism and a mechanism offered by halves is a lie. Below the threshold nothing changes — a
catalogue small enough to read whole is cheaper read whole.

The second claim here is the one the phase exists for, measured rather than asserted: two hundred
tools cost two hundred lines, not two hundred schemas.
"""

from __future__ import annotations

import json

from shadow_hdk.adapters.agent import DESCRIBE, Pattern, thin
from shadow_hdk.kernel.components import Interface
from shadow_hdk.kernel.ports import ModelResponse, ToolCall
from tests.adapters.agent.test_agent import drive_agent

ROLE = "You are working on one task."


def a_wide_schema(i: int) -> Interface:
    return Interface(
        name=f"tool_{i}",
        description=f"Tool number {i}, which does the {i}th thing.",
        input_schema={
            "type": "object",
            "properties": {
                f"arg_{j}": {"type": "string", "description": f"argument {j} of tool {i}"}
                for j in range(6)
            },
            "required": [f"arg_{j}" for j in range(3)],
        },
    )


async def test_describe_is_offered_whenever_the_catalogue_is_thinned() -> None:
    """The lie, corrected: a pattern with no `describe` of its own still gets it above the line."""
    crowded = Pattern(
        name="crowded", system=ROLE, meta_tools=frozenset({"done"}), catalogue_threshold=2
    )

    _events, model, _sink = await drive_agent(
        [ModelResponse("nothing to do", (ToolCall("c1", "done", {"summary": "looked"}),))],
        pattern=crowded,
    )

    offered = {i.name for i in model.requests[0].tools}
    assert DESCRIBE in offered, "the model was told to call a verb it was not given"


async def test_describe_is_not_forced_on_a_catalogue_read_whole() -> None:
    """Below the threshold the pattern's own verbs are its verbs — `single` stays deterministic."""
    small = Pattern(
        name="small", system=ROLE, meta_tools=frozenset({"done"}), catalogue_threshold=30
    )

    _events, model, _sink = await drive_agent(
        [ModelResponse("nothing to do", (ToolCall("c1", "done", {"summary": "looked"}),))],
        pattern=small,
    )

    offered = {i.name for i in model.requests[0].tools}
    assert DESCRIBE not in offered


def test_two_hundred_tools_cost_two_hundred_lines() -> None:
    """The phase's claim, measured. What reaches the model is what it pays for."""
    full = [a_wide_schema(i) for i in range(200)]
    pattern = Pattern(name="p", system=ROLE, catalogue_threshold=30)

    thinned = thin(full, pattern)

    whole = len(json.dumps([i.__dict__ for i in full], default=str))
    lean = len(json.dumps([i.__dict__ for i in thinned], default=str))
    assert len(thinned) == 200, "thinning dropped a component"
    assert lean < whole / 4, f"thinned catalogue is {lean} bytes against {whole} whole — not lean"
    assert all(not i.input_schema for i in thinned)
