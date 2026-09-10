"""A model that can summarise itself — and never keep the summary (D18).

`09` §5: *compaction is a component, not a runtime power: the model proposes a summary of its own
transcript, the proposal goes to the sink, and whoever implements the sink decides whether it is
kept and with what provenance.*

The load-bearing half is **not a runtime power**. Two things follow, and both are tests here: the
summary reaches the sink as a `Proposal` and the runtime writes it nowhere, and the transcript the
model carries afterwards is shorter — because a compaction that proposes a summary and then keeps
talking to the whole history has saved nothing.
"""

from __future__ import annotations

from shadow_hdk.adapters.agent import COMPACT, Pattern

from shadow_hdk.kernel.ports import ModelResponse, ToolCall
from tests.adapters.agent.test_agent import drive_agent

ROLE = "You are working on one task, and you may summarise your own transcript when it gets long."


def _pattern() -> Pattern:
    return Pattern(name="tidy", system=ROLE, meta_tools=frozenset({COMPACT, "propose", "done"}))


SUMMARY = "Looked up the lathe, found its mass, nothing else outstanding."


async def test_a_compaction_reaches_the_sink_as_a_proposal() -> None:
    _events, _model, sink = await drive_agent(
        [
            ModelResponse("tidying up", (ToolCall("c1", COMPACT, {"summary": SUMMARY}),)),
            ModelResponse("carrying on", (ToolCall("c2", "done", {"summary": "finished"}),)),
        ],
        pattern=_pattern(),
    )
    compactions = [p for p in sink.proposals if p.kind == "compaction"]
    assert len(compactions) == 1, "the summary never reached the sink"
    assert compactions[0].payload == SUMMARY
    assert compactions[0].provenance.adapter == "agent"


async def test_the_transcript_the_model_carries_afterwards_is_shorter() -> None:
    """A compaction that proposed a summary and then kept talking to the whole history would have
    saved nothing at all."""
    _events, model, _sink = await drive_agent(
        [
            ModelResponse("first", (ToolCall("t1", "search", {"query": "lathe"}),)),
            ModelResponse("second", (ToolCall("t2", "weigh", {"what": "lathe"}),)),
            ModelResponse("tidying", (ToolCall("c1", COMPACT, {"summary": SUMMARY}),)),
            ModelResponse("done now", (ToolCall("c2", "done", {"summary": "finished"}),)),
        ],
        pattern=_pattern(),
    )
    before = model.requests[2].messages
    after = model.requests[3].messages
    assert len(after) < len(before), "the transcript was not shortened"
    assert SUMMARY in "".join(m.content for m in after), "the summary is not in what it carries"


async def test_the_brief_and_the_role_survive_a_compaction() -> None:
    """What a compaction may drop is the middle. The role it was given and the job it was asked to
    do are not the model's to summarise away."""
    _events, model, _sink = await drive_agent(
        [
            ModelResponse("first", (ToolCall("t1", "search", {"query": "lathe"}),)),
            ModelResponse("tidying", (ToolCall("c1", COMPACT, {"summary": SUMMARY}),)),
            ModelResponse("done now", (ToolCall("c2", "done", {"summary": "finished"}),)),
        ],
        pattern=_pattern(),
    )
    after = model.requests[2].messages
    assert after[0].role == "system" and after[0].content == ROLE
    assert any(m.role == "user" and "lathe" in m.content for m in after), "the brief was dropped"


async def test_a_pattern_that_does_not_offer_it_cannot_compact() -> None:
    """D3. A team that does not want its agent rewriting its own history simply does not list the
    verb, and there is nothing in the runtime that knows the name."""
    from shadow_hdk.adapters.agent import single

    assert COMPACT not in single.meta_tools
