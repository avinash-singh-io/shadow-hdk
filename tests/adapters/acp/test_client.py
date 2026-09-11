"""The client half is a governance surface: fourteen doors, and each governable one is judged.

A mode written for the harness governs a child agent **without knowing that child exists**. Nobody
enumerated Codex's tools; the bridge turns each request into six fields and asks the same port the
runtime asks before its own steps.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from acp import schema
from acp.exceptions import RequestError
from shadow_hdk.adapters.acp import BridgeClient, Spend
from shadow_hdk.adapters.modes import Mode, ModeGovernance

from shadow_hdk.kernel import ASSUME_WORST, EffectProfile, ScopeSet
from tests.adapters.acp.conftest import EVERYTHING, inside_a_run

WORKSPACE = ScopeSet.of("workspace")

READING = Mode("reading", EffectProfile(reads=EVERYTHING, contained=False, costs=True))
WRITING = Mode(
    "writing",
    EffectProfile(reads=EVERYTHING, writes=WORKSPACE, reversible=True, contained=False, costs=True),
)
ASKING = Mode(
    "asking",
    ceiling=EffectProfile(reads=EVERYTHING, writes=WORKSPACE, contained=False, costs=True),
    ask_above=EffectProfile(reads=EVERYTHING, contained=False, costs=True),
)


def mode(one: Mode) -> ModeGovernance:
    return ModeGovernance({one.name: one}, default=one.name)


def options(*kinds: str) -> list[schema.PermissionOption]:
    return [
        schema.PermissionOption(option_id=f"opt-{kind}", name=kind, kind=kind)  # type: ignore[arg-type]
        for kind in kinds
    ]


def a_call(kind: str | None) -> schema.ToolCallUpdate:
    return schema.ToolCallUpdate(tool_call_id="c1", title="do the thing", kind=kind)  # type: ignore[arg-type]


# ---------------------------------------------------------------- permission


async def test_a_permitted_tool_call_is_allowed_in_the_agents_own_words() -> None:
    client = BridgeClient()
    answer = await inside_a_run(
        lambda: client.request_permission(
            "s", a_call("read"), options("allow_once", "reject_once")
        ),
        governance=mode(READING),
    )
    assert answer.outcome.outcome == "selected"
    assert answer.outcome.option_id == "opt-allow_once"


async def test_a_refused_tool_call_is_refused_in_the_agents_own_words() -> None:
    """Choosing a rejection option the agent itself offered is *answering* in its vocabulary — it
    can tell "not this time" from "never" and adapt. `DeniedOutcome` is the blunter "I will not
    answer"."""
    client = BridgeClient()
    answer = await inside_a_run(
        lambda: client.request_permission(
            "s", a_call("delete"), options("allow_once", "reject_once")
        ),
        governance=mode(READING),
    )
    assert answer.outcome.outcome == "selected"
    assert answer.outcome.option_id == "opt-reject_once"


async def test_reject_once_and_not_reject_always() -> None:
    """Our governance was asked about *this* call. Claiming permanence would assert a policy
    nobody wrote."""
    client = BridgeClient()
    answer = await inside_a_run(
        lambda: client.request_permission(
            "s", a_call("delete"), options("reject_always", "reject_once")
        ),
        governance=mode(READING),
    )
    assert answer.outcome.option_id == "opt-reject_once"


async def test_an_agent_offering_no_way_to_say_no_gets_denied_outright() -> None:
    client = BridgeClient()
    answer = await inside_a_run(
        lambda: client.request_permission("s", a_call("delete"), options("allow_once")),
        governance=mode(READING),
    )
    assert answer.outcome.outcome == "cancelled"


async def test_an_unlabelled_tool_call_is_the_worst_case_and_is_refused() -> None:
    """Nobody said what it does, so it is assumed to do everything — and a reading mode says no."""
    client = BridgeClient()
    answer = await inside_a_run(
        lambda: client.request_permission("s", a_call(None), options("allow_once", "reject_once")),
        governance=mode(READING),
    )
    assert answer.outcome.option_id == "opt-reject_once"


async def test_a_question_nobody_can_answer_is_a_refusal_that_says_so() -> None:
    """A child holding an open request cannot wait for a person: our `Ask` is an `interrupt()` that
    ends the parent's step, and the child's call would be abandoned mid-flight. So the honest answer
    is no, the question is recorded, and a host wanting a person in the loop pre-authorises.

    `contained=True` here is the arrangement, not the claim (BUG-018): the ASKING mode's ceiling
    permits workspace writes and asks above reads. An **uncontained** child's `edit` writes
    anywhere and so exceeds the ceiling — refused outright, never reaching the question. This test
    used to pass because the profile lied about that; now the edit has to be genuinely inside the
    workspace for the question to arise at all."""
    client = BridgeClient(contained=True)
    answer = await inside_a_run(
        lambda: client.request_permission(
            "s", a_call("edit"), options("allow_once", "reject_once")
        ),
        governance=mode(ASKING),
    )
    assert answer.outcome.option_id == "opt-reject_once"
    assert client.asked, "the question was thrown away"
    assert any("would have asked" in r for r in client.refusals)


# ---------------------------------------------------------------- the filesystem


async def test_a_child_may_write_under_a_writing_mode(tmp_path: Path) -> None:
    client = BridgeClient(workspace=tmp_path)
    await inside_a_run(
        lambda: client.write_text_file("s", "notes.md", "# from the child\n"),
        governance=mode(WRITING),
    )
    assert (tmp_path / "notes.md").read_text() == "# from the child\n"


async def test_a_child_may_not_write_under_a_reading_mode(tmp_path: Path) -> None:
    client = BridgeClient(workspace=tmp_path)
    with pytest.raises(RequestError) as refused:
        await inside_a_run(
            lambda: client.write_text_file("s", "notes.md", "x"), governance=mode(READING)
        )
    assert "reading" in str(refused.value)
    assert not (tmp_path / "notes.md").exists()


async def test_a_child_cannot_write_outside_the_workspace(tmp_path: Path) -> None:
    """Permission and confinement are different questions, and both are asked."""
    root = tmp_path / "root"
    root.mkdir()
    client = BridgeClient(workspace=root)
    with pytest.raises(RequestError) as refused:
        await inside_a_run(
            lambda: client.write_text_file("s", "../escaped.txt", "x"), governance=mode(WRITING)
        )
    assert "outside" in str(refused.value)
    assert not (tmp_path / "escaped.txt").exists()


async def test_a_child_can_read_what_it_wrote(tmp_path: Path) -> None:
    (tmp_path / "there.md").write_text("already here")
    client = BridgeClient(workspace=tmp_path)
    answer = await inside_a_run(
        lambda: client.read_text_file("s", "there.md"), governance=mode(READING)
    )
    assert answer.content == "already here"


async def test_a_bridge_with_no_workspace_offers_no_filesystem() -> None:
    client = BridgeClient()
    with pytest.raises(RequestError) as refused:
        await inside_a_run(lambda: client.read_text_file("s", "x"), governance=mode(READING))
    assert "no filesystem" in str(refused.value)


# ---------------------------------------------------------------- the rest of the surface


async def test_opening_a_terminal_is_judged_before_it_is_declined(tmp_path: Path) -> None:
    client = BridgeClient(workspace=tmp_path, contained=False)
    with pytest.raises(RequestError) as refused:
        await inside_a_run(
            lambda: client.create_terminal("s", "rm -rf /"), governance=mode(WRITING)
        )
    assert "writing" in str(refused.value), "it should be refused by the mode, not by the stub"


async def test_an_extension_nobody_vouched_for_is_the_worst_case() -> None:
    """The refusal must come from **governance**, not from the "no such method" fallback at the
    bottom of the function. Otherwise removing the judgement entirely looks identical — and a
    mutation proved it did. Under a writing mode `ASSUME_WORST` is refused, and the reason names
    the mode that refused it."""
    client = BridgeClient()
    with pytest.raises(RequestError) as refused:
        await inside_a_run(lambda: client.ext_method("vendor/secret", {}), governance=mode(WRITING))
    assert "writing" in str(refused.value), (
        f"refused by the fallback, not by the policy: {refused.value}"
    )


async def test_a_child_asking_a_person_directly_is_told_there_is_nobody_there() -> None:
    client = BridgeClient()
    with pytest.raises(RequestError) as refused:
        await inside_a_run(
            lambda: client.create_elicitation("are you sure?", None), governance=mode(WRITING)
        )
    assert "no person" in str(refused.value)
    assert client.asked


async def test_outside_a_run_there_is_no_governance_and_so_no(tmp_path: Path) -> None:
    """The safe answer to *may this untrusted child write to your disk* with nobody to ask."""
    client = BridgeClient(workspace=tmp_path)
    with pytest.raises(RequestError) as refused:
        await client.write_text_file("s", "notes.md", "x")
    assert "no run" in str(refused.value)
    assert not (tmp_path / "notes.md").exists()


# ---------------------------------------------------------------- money


def test_two_hundred_sub_cent_calls_are_eighty_cents_not_nothing() -> None:
    """The reason money is accumulated and converted **once**. Rounding each call would make two
    hundred charges of 0.004 USD add up to zero, and the meter would never tick."""
    spend = Spend("USD")
    for _ in range(200):
        spend.add_cost(schema.Cost(amount=0.004, currency="USD"))
    assert spend.cents == 80


def test_a_currency_we_were_not_configured_for_is_not_converted() -> None:
    """An exchange rate is policy about a contract. Guessing one would be inventing money."""
    spend = Spend("USD")
    spend.add_cost(schema.Cost(amount=1.5, currency="EUR"))
    assert spend.cents is None
    assert spend.foreign == {"EUR": Decimal("1.5")}


def test_a_mixed_bag_of_currencies_cannot_be_totalled() -> None:
    """The case that actually distinguishes the rule. With **only** a foreign charge the amount is
    zero either way, so a test using one currency passes whether or not the check exists — a
    mutation proved it. A dollar *and* a euro is the shape that has a wrong answer available: 100
    cents, ignoring the euro. The right answer is that it cannot be totalled."""
    spend = Spend("USD")
    spend.add_cost(schema.Cost(amount=1.0, currency="USD"))
    spend.add_cost(schema.Cost(amount=1.5, currency="EUR"))
    assert spend.amount == Decimal("1.0"), "the dollars were still counted"
    assert spend.cents is None, "a total across currencies is a number nobody can stand behind"


def test_nothing_priceable_is_unknown_rather_than_zero() -> None:
    assert Spend("USD").cents is None


def test_tokens_accumulate_across_a_session() -> None:
    spend = Spend("USD")
    spend.add_tokens(schema.Usage(total_tokens=14, input_tokens=10, output_tokens=4))
    spend.add_tokens(schema.Usage(total_tokens=6, input_tokens=4, output_tokens=2))
    assert (spend.input_tokens, spend.output_tokens, spend.total_tokens) == (14, 6, 20)
    assert spend.tokens_seen


def test_usage_that_never_arrives_leaves_no_trace() -> None:
    spend = Spend("USD")
    spend.add_tokens(None)
    assert not spend.tokens_seen


async def test_a_usage_update_over_the_wire_reaches_the_purse() -> None:
    client = BridgeClient()
    await client.session_update(
        "s",
        schema.UsageUpdate(
            session_update="usage_update",
            used=1200,
            size=200_000,
            cost=schema.Cost(amount=0.004, currency="USD"),
        ),
    )
    assert client.spend.amount == Decimal("0.004")


def test_the_worst_case_is_what_an_extension_is_judged_as() -> None:
    assert ASSUME_WORST.reaches and not ASSUME_WORST.reversible and not ASSUME_WORST.contained


# ---------------------------------------------------------------- what we only heard about


async def test_a_tool_call_the_child_made_on_its_own_is_marked_observed() -> None:
    """The other half of posture, and the reason the field exists.

    A child agent does work we never gated — its own file edits, its own shell. ACP tells us about
    it in a `tool_call` notification **after** it happened. We could not have refused it, so it is
    recorded honestly as `observed` rather than dressed up as something we consented to.
    """
    client = BridgeClient()
    await client.session_update(
        "s",
        schema.ToolCallStart(
            session_update="tool_call",
            tool_call_id="native-1",
            title="edit src/main.py",
            kind="edit",
        ),
    )
    assert len(client.overheard) == 1
    heard = client.overheard[0]
    assert heard.provenance.posture == "observed"
    assert heard.kind == "tool_call"
    assert isinstance(heard.payload, dict)
    assert heard.payload["title"] == "edit src/main.py"


async def test_what_we_gated_is_not_marked_observed() -> None:
    """A permission request is the child *asking*, which we can refuse — so it is controlled. If
    both came out observed the field would say nothing."""
    client = BridgeClient()
    await inside_a_run(
        lambda: client.request_permission("s", a_call("read"), options("allow_once")),
        governance=mode(READING),
    )
    assert client.overheard == [], "an request we judged is not something we merely overheard"
