"""A model that is refused is told **why**, and told it was refused rather than broken.

Found by research into what other agent systems actually do (recorded in phase-2's history). Two
findings from that survey land directly here:

* **You cannot simply not answer a tool call.** Every major provider rejects a dangling one —
  Anthropic, OpenAI and Google all 400 a request whose tool calls are not each paired with a
  result. So a refusal has to *synthesise* an answer, and the industry's most commonly filed bug in
  approval systems is exactly this pairing being missed.
* **A refusal delivered through the error channel invites a retry.** MCP defines its error flag as
  the bucket for *"actionable feedback that language models can use to self-correct and retry"*, and
  Anthropic documents the model retrying two or three times on an invalid call. So *you may not* and
  *it broke* must not read the same.

This harness was already well placed for the second — `Refused` and `Failed` are separate
observations, and a refusal emits its own event kind. It was wrong on the first. `carry_out`
collected only `observed` events, and a refusal emits `refused` and no `observed`, so a refused
tool call came back to the model as **"that step did not run"**: no reason, and indistinguishable
from a step that never happened.
"""

from __future__ import annotations

from shadow_hdk.adapters.agent import Pattern

from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import Context, Judgement, ModelResponse, Refuse, ToolCall
from shadow_hdk.runtime import Ports
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

ROLE = "You are working on one task, using the tools you are given, and you may be refused."


class NoWrites:
    """A policy on the deployment, not in the model's head.

    It refuses **writes**, which the tool has and the agent component does not — so the agent runs
    and is refused *inside* its own turn, which is the situation under test. An earlier version
    refused reads and stopped the agent itself before it ever reached a second turn.
    """

    async def judge(self, effects: EffectProfile, _context: Context) -> Judgement:
        from shadow_hdk.kernel.ports import Allow

        if effects.writes.names or effects.writes.everything:
            return Refuse("writing is not permitted in this deployment")
        return Allow()


def wipe(what: str) -> str:
    """Delete something."""
    return f"wiped {what}"


async def _drive_refused() -> ScriptedModel:
    from shadow_hdk.adapters.agent import AgentComponent
    from shadow_hdk.adapters.basic import CallableComponents

    from shadow_hdk.kernel import (
        Binding,
        Ceiling,
        Composition,
        Floor,
        Invoke,
        Lease,
        ScopeSet,
    )
    from shadow_hdk.runtime import RunOptions, run

    tools = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    tools.add(wipe, effects=EffectProfile(writes=ScopeSet.of("workspace"), reversible=False))
    agent = AgentComponent(
        pattern=Pattern(name="p", system=ROLE),
        effects=EffectProfile(costs=True),
        at="2026-01-01T00:00:00+00:00",
    )
    model = ScriptedModel(
        [
            ModelResponse("wiping", (ToolCall("t1", "wipe", {"what": "the lathe"}),)),
            ModelResponse("fine", (ToolCall("d1", "done", {"summary": "was refused"}),)),
        ]
    )
    ports = Ports(
        model=model,
        components=(tools, agent),
        governance=NoWrites(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    composition = Composition(
        (Invoke("a1", agent.registration_id, (Binding(name="brief", value="tidy the workshop"),)),)
    )
    async for _ in run(
        composition, ports, options=RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0)))
    ):
        pass
    return model


async def test_a_refused_tool_call_is_answered_at_all() -> None:
    """The pairing rule. Every provider rejects a tool call with no result beside it, so a refusal
    has to answer — and this is the bug most commonly filed against approval systems."""
    model = await _drive_refused()
    second = model.requests[1]
    answers = [m for m in second.messages if m.role == "tool"]
    assert [m.tool_call_id for m in answers] == ["t1"], "the refused call was left unanswered"


async def test_the_model_is_told_why_it_was_refused() -> None:
    model = await _drive_refused()
    answer = [m for m in model.requests[1].messages if m.role == "tool"][0].content
    assert "writing is not permitted" in answer, answer


async def test_a_refusal_does_not_read_like_a_breakage() -> None:
    """*You may not* and *it broke* invite different next moves, and a channel that collapses them
    invites the wrong one — the error channel's documented contract is `try again differently`."""
    model = await _drive_refused()
    answer = [m for m in model.requests[1].messages if m.role == "tool"][0].content
    assert answer.startswith("refused:"), answer
    assert "failed" not in answer, answer
    assert "did not run" not in answer, answer
