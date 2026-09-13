"""A large result is held back from the model's context, and never from the record (D47).

A tool that returns a hundred kilobytes — a file listing, a log, a page — costs a hundred kilobytes
of context on every turn after it, because the transcript is re-sent whole. The benchmarked
competitor credits *large-result offloading* for a good part of its cost advantage, and the
mechanism is not complicated: past a threshold the model sees a handle, a size and a preview, and
pulls the rest in slices when it wants them.

**Where the rest lives is the design question, and the answer is: with the agent, not on disk.**
The first plan said *the environment, as a file*. That would give the runtime a write path, which
the second principle forbids — the runtime acts through components and records through the sink,
and a file it wrote itself is neither. Offloading is about the *model's* context. The agent adapter
holds the full result for the run and offers `recall` to page it; the record and the sink get the
whole observation exactly as they always did, because offloading never touches them.

The threshold is a pattern field like `catalogue_threshold`: what the model sees is the pattern's
to say. `None` is off.
"""

from __future__ import annotations

from typing import Any

from shadow_hdk.adapters.agent import RECALL, Pattern
from shadow_hdk.adapters.basic import AllowAll, CallableComponents
from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Composition,
    Floor,
    Invoke,
    Lease,
    Observed,
)
from shadow_hdk.kernel.ports import ModelResponse, ToolCall
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel
from tests.adapters.agent.test_agent import AGENT_EFFECTS, READS

ROLE = "You are working on one task."
BIG = "x" * 20_000


def listing(_what: str = "") -> dict[str, Any]:
    return {"lines": BIG}


async def drive(pattern: Pattern, *script: ModelResponse) -> tuple[list[Any], ScriptedModel]:
    from shadow_hdk.adapters.agent import AgentComponent

    tools = CallableComponents(registered_by="tests", at="t")
    tools.add(listing, effects=READS)
    agent = AgentComponent(pattern=pattern, effects=AGENT_EFFECTS, at="t")
    model = ScriptedModel(list(script))
    ports = Ports(
        model=model,
        components=(tools, agent),
        governance=AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    plan = Composition((Invoke("a1", "agent", (Binding("brief", value="list it"),)),))
    events = [
        e
        async for e in run(
            plan, ports, options=RunOptions(lease=Lease(Ceiling(20, 600, 100), Floor(0)))
        )
    ]
    return events, model


def offloading(over: int | None) -> Pattern:
    return Pattern(
        name="p", system=ROLE, tool_names=frozenset({"listing"}), max_turns=4, offload_over=over
    )


def tool_reply(model: ScriptedModel, turn: int) -> str:
    """The tool message the model saw on its `turn`-th request."""
    request = model.requests[turn]
    return next(m.content for m in reversed(request.messages) if m.role == "tool")


async def test_a_result_over_the_threshold_reaches_the_model_as_a_handle() -> None:
    _events, model = await drive(
        offloading(1_000),
        ModelResponse(tool_calls=(ToolCall("c1", "listing", {"_what": ""}),)),
        ModelResponse("done"),
    )

    seen = tool_reply(model, 1)
    assert len(seen) < 2_000, f"the model saw {len(seen)} chars of a 20,000-char result"
    assert "offloaded" in seen and "preview" in seen and "size" in seen
    assert RECALL in seen, "the handle does not say how to get the rest"


async def test_the_record_still_gets_the_whole_thing() -> None:
    """Offloading is about the model's context and nothing else. The sink and the stream see the
    observation exactly as they always did."""
    events, _model = await drive(
        offloading(1_000),
        ModelResponse(tool_calls=(ToolCall("c1", "listing", {"_what": ""}),)),
        ModelResponse("done"),
    )

    observed = [e for e in events if isinstance(e, Observed) and e.step != "a1"]
    assert observed, "the tool's observation never reached the stream"
    assert BIG in str(observed[0].observation.output), "the record was truncated"  # type: ignore[union-attr]


async def test_the_model_can_recall_a_slice() -> None:
    _events, model = await drive(
        offloading(1_000),
        ModelResponse(tool_calls=(ToolCall("c1", "listing", {"_what": ""}),)),
        ModelResponse(
            tool_calls=(ToolCall("c2", RECALL, {"handle": "result-1", "start": 0, "length": 50}),)
        ),
        ModelResponse("done"),
    )

    recalled = tool_reply(model, 2)
    # A slice of the *rendered* result — the JSON the model would have seen whole — so the first
    # fifty characters are the prefix and the start of the payload, exactly as they lie in it.
    assert len(recalled) == 50, recalled
    assert recalled.startswith('{"lines": "xxx')


async def test_recall_is_offered_whenever_offloading_is_on() -> None:
    """The mechanism's other half, the same rule as `describe` above the threshold: a handle the
    model cannot follow is worse than the flood it replaced."""
    _events, model = await drive(offloading(1_000), ModelResponse("done"))

    assert RECALL in {i.name for i in model.requests[0].tools}


async def test_off_by_default_and_a_small_result_is_untouched() -> None:
    _events, model = await drive(
        offloading(None),
        ModelResponse(tool_calls=(ToolCall("c1", "listing", {"_what": ""}),)),
        ModelResponse("done"),
    )

    assert BIG in tool_reply(model, 1)
    assert RECALL not in {i.name for i in model.requests[0].tools}


async def test_a_handle_nobody_issued_is_a_sentence_not_a_crash() -> None:
    _events, model = await drive(
        offloading(1_000),
        ModelResponse(tool_calls=(ToolCall("c1", RECALL, {"handle": "result-9", "start": 0}),)),
        ModelResponse("done"),
    )

    assert "no offloaded result" in tool_reply(model, 1)
