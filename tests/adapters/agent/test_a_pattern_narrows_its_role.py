"""A pattern's ceiling is enforced, not merely parsed (BUG-012).

`Pattern.ceiling` has existed since Phase 8 and its own docstring says what it is for — *a ceiling
narrowing this role beyond whatever the deployment's mode already allows*. It was loaded from the
file, held on the dataclass, and read by nothing. A team writing `[ceiling]` into a pattern file got
a value object and no enforcement, which is worse than the field not existing: it reads as a
guarantee.

Two halves, and they are the same rule from either end. **Absent, not greyed out** (`09` §4): a
component this role may never use is not in the catalogue the model is shown. And **permission is
still effects** (`09` §2): the ceiling is enforced at judgement, so a plan naming a component
directly is refused even though nobody offered it.

A pattern can only ever narrow. The deployment's policy is asked first and its refusal stands — a
role cannot grant itself what the house withheld.
"""

from __future__ import annotations

from typing import Any

from shadow_hdk.adapters.agent import AgentComponent, Pattern
from shadow_hdk.adapters.agent.pattern import COMPOSE, DONE, PROPOSE
from shadow_hdk.adapters.basic import AllowAll, CallableComponents

from shadow_hdk.kernel import (
    Binding,
    Ceiling,
    Composition,
    Floor,
    Invoke,
    Lease,
    ScopeSet,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import (
    Allow,
    Context,
    Judgement,
    ModelResponse,
    Refuse,
    ToolCall,
)
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, ListSink, ScriptedModel

WORKSPACE = ScopeSet.of("workspace")
READS_ONLY = EffectProfile(reads=WORKSPACE)


def look(topic: str) -> str:
    """Look a topic up."""
    return f"found {topic}"


def wipe(what: str) -> str:
    """Delete something."""
    return f"wiped {what}"


class RefusesReads:
    """Refuses the *tools*, not the agent. The agent component declares `costs` and no reads, so a
    policy refusing everything would stop the role at the door and prove nothing about its steps."""

    async def judge(self, effects: EffectProfile, _context: Context) -> Judgement:
        if effects.reads.names or effects.reads.everything:
            return Refuse("the deployment refuses this")
        return Allow()


async def drive(
    calls: tuple[ToolCall, ...],
    *,
    ceiling: EffectProfile | None,
    governance: Any = None,
) -> ScriptedModel:
    tools = CallableComponents(registered_by="tests", at="2026-01-01T00:00:00+00:00")
    tools.add(look, effects=READS_ONLY)
    tools.add(wipe, effects=EffectProfile(writes=WORKSPACE, reversible=False))
    agent = AgentComponent(
        pattern=Pattern(
            name="reader",
            system="read things",
            meta_tools=frozenset({COMPOSE, PROPOSE, DONE}),
            ceiling=ceiling,
        ),
        effects=EffectProfile(costs=True),
        at="2026-01-01T00:00:00+00:00",
    )
    model = ScriptedModel(
        [
            ModelResponse("working", calls),
            ModelResponse("ok", (ToolCall("d1", "done", {"summary": "finished"}),)),
        ]
    )
    ports = Ports(
        model=model,
        components=(tools, agent),
        governance=governance or AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    async for _ in run(
        Composition((Invoke("a1", agent.registration_id, (Binding(name="brief", value="go"),)),)),
        ports,
        options=RunOptions(lease=Lease(Ceiling(40, 3600, 10_000), Floor(0))),
    ):
        pass
    return model


def offered(model: ScriptedModel, turn: int = 0) -> set[str]:
    return {tool.name for tool in model.requests[turn].tools}


def answers(model: ScriptedModel, turn: int = 1) -> dict[str | None, str]:
    return {m.tool_call_id: m.content for m in model.requests[turn].messages if m.role == "tool"}


async def test_a_component_above_the_ceiling_is_never_offered() -> None:
    """Absent, not refused-on-use. A model shown a tool it may never use spends tokens deciding to
    use it and gets a refusal for its trouble."""
    model = await drive((ToolCall("t1", "look", {"topic": "one"}),), ceiling=READS_ONLY)

    assert "look" in offered(model)
    assert "wipe" not in offered(model), "a component the role may never use was offered anyway"


async def test_a_component_within_the_ceiling_still_runs() -> None:
    model = await drive((ToolCall("t1", "look", {"topic": "one"}),), ceiling=READS_ONLY)

    assert answers(model) == {"t1": '"found one"'}


async def test_naming_it_anyway_is_refused_and_says_which_rule() -> None:
    """The catalogue is discovery; the ceiling is permission (`09` §2). A model that names a
    component it was not offered — from an authored plan, from memory of an earlier turn, or by
    guessing — is refused, and told it was the role and not the deployment."""
    model = await drive((ToolCall("t1", "wipe", {"what": "the lathe"}),), ceiling=READS_ONLY)
    answer = answers(model)["t1"]

    assert "refused" in answer
    assert "reader" in answer, f"the refusal does not name the pattern that caused it: {answer}"


async def test_a_pattern_without_a_ceiling_changes_nothing() -> None:
    """The default, and it must stay the permissive one: `None` means *whatever the deployment
    allows*, so every pattern written before this field was read behaves as it always did."""
    model = await drive((ToolCall("t1", "wipe", {"what": "the lathe"}),), ceiling=None)

    assert offered(model) == {"look", "wipe", "compose", "propose", "done"}
    assert answers(model) == {"t1": '"wiped the lathe"'}


async def test_a_pattern_cannot_grant_what_the_deployment_withheld() -> None:
    """Only ever narrower. A role's ceiling is a second gate, not a replacement for the first, and
    a pattern file that could widen the house would make every pattern a security decision."""
    model = await drive(
        (ToolCall("t1", "look", {"topic": "one"}),),
        ceiling=EffectProfile(reads=ScopeSet(everything=True), writes=ScopeSet(everything=True)),
        governance=RefusesReads(),
    )

    assert "the deployment refuses this" in answers(model)["t1"]


async def test_the_agent_itself_is_still_reachable_under_a_narrow_ceiling() -> None:
    """The agent component declares `costs=True`, which a reads-only ceiling does not permit — and
    the ceiling governs the role's *steps*, not the step that started the role. Getting this wrong
    makes a narrow pattern refuse to run at all, which is the failure that looks like a hang."""
    model = await drive((ToolCall("t1", "look", {"topic": "one"}),), ceiling=READS_ONLY)

    assert len(model.requests) == 2, "the agent never reached its second turn"


async def test_when_both_refuse_the_deployment_gets_the_last_word() -> None:
    """Found by a mutation that survived: asking the deployment first and returning its refusal
    early changed no outcome any test could see, because no test had *both* gates closed.

    The outcome is the same either way — refused is refused. The **reason** is not, and it is the
    only part a person acts on: a team debugging its own pattern file should not be sent there over
    a rule it does not control and cannot change.
    """
    model = await drive(
        (ToolCall("t1", "look", {"topic": "one"}),),
        ceiling=EffectProfile(),
        governance=RefusesReads(),
    )
    answer = answers(model)["t1"]

    assert "the deployment refuses this" in answer
    assert "pattern" not in answer, f"the role was blamed for the house's refusal: {answer}"
