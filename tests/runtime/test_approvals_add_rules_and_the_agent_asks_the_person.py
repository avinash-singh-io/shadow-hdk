"""Approve-and-add-rule, and the agent's own question to the person (D65).

Every product has "yes, and don't ask again" (Claude Code), `acceptWithExecpolicyAmendment`
(Codex). Ours is a **rule the person adds at answer time**: an `ActRule` naming the component and
the inputs it applies to, kept by the host's `ActRules` registry, read by governance at the next
judgement — live, no restart (principle 10) — and proposed through the sink so the record says a
rule was made and by what. And every product has the agent's own question item; `ask_person`
puts an `InputRequested` on the record and waits on the same handle for text.
"""

from __future__ import annotations

from typing import Any

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from shadow_hdk.adapters.modes import Mode, ModeGovernance
from shadow_hdk.adapters.modes.acts import ActRules
from shadow_hdk.kernel import (
    ActRule,
    Binding,
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Ended,
    Event,
    Failed,
    Floor,
    Invoke,
    Lease,
    Observed,
    Proposed,
    ScopeSet,
)
from shadow_hdk.kernel.events import ApprovalRequested, InputRequested
from shadow_hdk.runtime import (
    Approvals,
    ApproveAndAddRule,
    InMemoryEffectJournal,
    Ports,
    RunOptions,
    current_run,
    resume,
    run,
)
from shadow_hdk.runtime.person import person_components
from shadow_hdk.runtime.testing import (
    AllowAuthorizer,
    FixedAuthority,
    FixedClock,
    InMemoryComponents,
    ListSink,
    make_registration,
)
from shadow_hdk.testing.contracts import ComponentPortContract

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
WRITE = make_registration("write_file", effects=EffectProfile(writes=WORKSPACE, reversible=False))
ASKING = Mode(
    "asking",
    ceiling=EffectProfile(reads=WORKSPACE, writes=WORKSPACE, reversible=False),
    ask_above=EffectProfile(reads=WORKSPACE),
)


async def write(_inputs: Any) -> Any:
    return Completed({"wrote": True})


def ports(rules: ActRules | None, sink: ListSink | None = None) -> Ports:
    return Ports(
        model=None,
        components=(InMemoryComponents([(WRITE, write)]), person_components()),
        governance=ModeGovernance({"asking": ASKING}, default="asking", rules=rules),
        sink=sink or ListSink(),
        clock=FixedClock(),
        authority=FixedAuthority(),
        authorizer=AllowAuthorizer(),
        effect_journal=InMemoryEffectJournal(),
    )


def plan(step: str, path: str = "a.txt") -> Composition:
    return Composition(
        (Invoke(step, "write_file", (Binding("path", value=path), Binding("content", value="x"))),)
    )


def options(
    approvals: Approvals | None = None, run_id: str = "r", rules: ActRules | None = None
) -> RunOptions:
    return RunOptions(
        lease=Lease(Ceiling(10, 60, None), Floor(0)),
        run_id=run_id,
        approvals=approvals,
        rules=rules,
        checkpointer=InMemorySaver(),
    )


async def collect(events: Any) -> list[Event]:
    return [e async for e in events]


def _answering(approvals: Approvals, answer: Any) -> Any:
    import asyncio

    async def answer_it() -> None:
        pending = await approvals.next()
        approvals.answer(pending.handle, answer)

    return asyncio.create_task(answer_it())


# ------------------------------------------------------------------ rules


async def test_an_act_rule_stops_the_asking_at_the_next_judgement() -> None:
    rules = ActRules()
    first = await collect(run(plan("w1"), ports(rules), options=options(None, "one")))
    assert [e for e in first if isinstance(e, ApprovalRequested)], "the policy asks first"
    assert not [e for e in first if isinstance(e, Ended)], "and the run parks on it"

    rules.add(ActRule(component="write_file", inputs={"path": "a.txt", "content": "x"}))
    second = await collect(run(plan("w2"), ports(rules), options=options(None, "two")))

    assert not [e for e in second if isinstance(e, ApprovalRequested)], "the rule stood in"
    assert [e for e in second if isinstance(e, Observed)][-1].observation == Completed(
        {"wrote": True}
    )


async def test_a_rule_matches_exactly_what_it_names_and_nothing_wider() -> None:
    rules = ActRules([ActRule(component="write_file", inputs={"path": "a.txt", "content": "x"})])

    other = await collect(run(plan("w1", path="b.txt"), ports(rules), options=options()))

    assert [e for e in other if isinstance(e, ApprovalRequested)], "a different path is asked about"


async def test_a_prefix_rule_covers_what_starts_the_same_way() -> None:
    rules = ActRules([ActRule(component="write_file", inputs={"path": "notes/*"})])

    inside = await collect(run(plan("w1", path="notes/today.md"), ports(rules), options=options()))

    assert not [e for e in inside if isinstance(e, ApprovalRequested)]


async def test_a_rule_for_another_component_does_not_cover_this_one() -> None:
    """The bound a rule must not cross: the component it names. A rule about reading is not a
    rule about writing, whatever the inputs look like."""
    rules = ActRules([ActRule(component="read_file", inputs={"path": "a.txt"})])

    events = await collect(run(plan("w1", path="a.txt"), ports(rules), options=options()))

    assert [e for e in events if isinstance(e, ApprovalRequested)], "write_file is still asked"


async def test_a_prefix_rule_does_not_cover_what_starts_differently() -> None:
    rules = ActRules([ActRule(component="write_file", inputs={"path": "notes/*"})])

    outside = await collect(run(plan("w1", path="other/today.md"), ports(rules), options=options()))

    assert [e for e in outside if isinstance(e, ApprovalRequested)], "outside the prefix is asked"


async def test_a_rule_can_deny_too_and_says_so() -> None:
    rules = ActRules([ActRule(component="write_file", inputs={"path": ".env"}, decision="deny")])

    refused = await collect(run(plan("w1", path=".env"), ports(rules), options=options()))

    assert [e for e in refused if e.kind == "refused"], "a deny rule refuses without asking"


async def test_approve_and_add_rule_on_resume_adds_it_live_and_proposes_it() -> None:
    """The parked path: the top-level step asked, the run parked, the host resumes it with
    *approve and add a rule*. The registry has the rule the moment the answer lands; the record
    says a rule was made; the next run does not ask."""
    rules = ActRules()
    sink = ListSink()
    rule = ActRule(component="write_file", inputs={"path": "a.txt", "content": "x"})
    first_options = options(None, "one", rules)
    parked = await collect(run(plan("w1"), ports(rules, sink), options=first_options))
    assert [e for e in parked if isinstance(e, ApprovalRequested)]

    resumed = await collect(
        resume(plan("w1"), ApproveAndAddRule(rule), ports(rules, sink), options=first_options)
    )

    assert [e for e in resumed if isinstance(e, Observed)][-1].observation == Completed(
        {"wrote": True}
    )
    assert rules.all() == (rule,), "the run's registry has it the moment the person said so"
    proposed = [e for e in resumed if isinstance(e, Proposed)]
    assert proposed and proposed[0].proposal.kind == "rule", "the record says a rule was made"
    assert [p.kind for p in sink.proposals] == ["rule"]

    second = await collect(run(plan("w2"), ports(rules, sink), options=options(None, "two", rules)))
    assert not [e for e in second if isinstance(e, ApprovalRequested)]


async def test_approve_and_add_rule_live_adds_it_and_proposes_it() -> None:
    """The live path (D58): a component asks through the handle while its step runs — the way a
    provider's tool call does — and the answer carries a rule."""
    rules = ActRules()
    sink = ListSink()
    approvals = Approvals()
    rule = ActRule(component="write_file", inputs={"path": "a.txt", "content": "x"})
    _answering(approvals, ApproveAndAddRule(rule))

    async def asks(_inputs: Any) -> Any:
        context = current_run()
        assert context is not None
        judged = await context.request_approval(
            "may it?", about=("write_file", {"path": "a.txt", "content": "x"})
        )
        return Completed({"judged": judged.kind})

    asking_ports = Ports(
        model=None,
        components=(InMemoryComponents([(make_registration("asks"), asks)]),),
        governance=ModeGovernance({"asking": ASKING}, default="asking", rules=rules),
        sink=sink,
        clock=FixedClock(),
    )
    events = await collect(
        run(
            Composition((Invoke("s1", "asks", (Binding("brief", value=""),)),)),
            asking_ports,
            options=options(approvals, "one", rules),
        )
    )

    assert [e for e in events if isinstance(e, Observed)][-1].observation == Completed(
        {"judged": "allow"}
    )
    assert rules.all() == (rule,)
    assert [p.kind for p in sink.proposals] == ["rule"]


async def test_a_rule_scoped_to_a_mode_applies_only_there() -> None:
    rules = ActRules(
        [ActRule(component="write_file", inputs={"path": "a.txt", "content": "x"}, mode="other")]
    )

    events = await collect(run(plan("w1"), ports(rules), options=options()))

    assert [e for e in events if isinstance(e, ApprovalRequested)], "the rule is for another mode"


# ------------------------------------------------------------------ the agent asks the person


def ask_plan() -> Composition:
    return Composition((Invoke("q1", "ask_person", (Binding("question", value="which colour?"),)),))


async def test_ask_person_puts_an_input_request_on_the_record_and_returns_the_answer() -> None:
    approvals = Approvals()
    _answering(approvals, "blue")

    events = await collect(run(ask_plan(), ports(None), options=options(approvals)))

    asked = [e for e in events if isinstance(e, InputRequested)]
    assert [a.question for a in asked] == ["which colour?"]
    assert asked[0].step == "q1"
    done = [e for e in events if isinstance(e, Observed) and e.step == "q1"][-1]
    assert done.observation == Completed({"answer": "blue"})
    assert [e for e in events if isinstance(e, Ended)][-1].reason == "completed"


async def test_ask_person_with_nobody_there_fails_and_says_so() -> None:
    events = await collect(run(ask_plan(), ports(None), options=options(None)))

    done = [e for e in events if isinstance(e, Observed) and e.step == "q1"][-1]
    assert isinstance(done.observation, Failed)
    assert "nobody" in done.observation.error


async def test_the_pending_request_says_it_is_for_input_not_approval() -> None:
    approvals = Approvals()
    seen: list[Any] = []

    async def look() -> None:
        pending = await approvals.next()
        seen.append(pending)
        approvals.answer(pending.handle, "red")

    import asyncio

    asyncio.create_task(look())
    await collect(run(ask_plan(), ports(None), options=options(approvals)))

    assert seen and seen[0].kind == "input" and seen[0].question == "which colour?"


async def test_ask_person_declares_no_effects_so_every_mode_offers_it() -> None:
    port = person_components()
    [registration] = await port.registrations()
    assert registration.id == "ask_person"
    assert registration.component.effects == EffectProfile()


async def test_ask_person_from_inside_a_component_uses_the_running_context() -> None:
    """The component reaches the run through `current_run()` like any other, so it works over the
    wire the way every crossed component does."""
    approvals = Approvals()
    _answering(approvals, "green")
    port = person_components()

    context_seen: list[Any] = []

    async def probe(_inputs: Any) -> Any:
        context_seen.append(current_run())
        return Completed({})

    ports_ = Ports(
        model=None,
        components=(InMemoryComponents([(make_registration("probe"), probe)]), port),
        governance=ModeGovernance({"asking": ASKING}, default="asking"),
        sink=ListSink(),
        clock=FixedClock(),
    )
    events = await collect(run(ask_plan(), ports_, options=options(approvals)))
    assert [e for e in events if isinstance(e, Observed) and e.step == "q1"][
        -1
    ].observation == Completed({"answer": "green"})


class TestPersonComponentsIsAComponentPort(ComponentPortContract):
    def port(self) -> Any:
        return person_components()

    def valid_call(self) -> tuple[str, Any]:
        return "ask_person", {"question": "hi?"}
