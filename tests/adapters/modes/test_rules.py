"""A rule is a row, and rows intersect.

`09` §11: *the effect-rules governance engine — rules as rows over effect profiles, composed by
**intersection**, with the narrowing proof.*

Two properties carry the whole design. **Every applicable row applies** — there is no first match
and no ordering, because order is a hidden operator that neither a reader nor the narrowing check
can see. And **the composition can only narrow**, which is `EffectProfile.meet` and is therefore
arithmetic rather than a review comment.

A `Mode` is the one-row case, and `adapters/modes` keeps working.
"""

from __future__ import annotations

import pytest
from shadow_hdk.adapters.modes import Rule, RuleGovernance, RuleSet

from shadow_hdk.kernel.effects import EffectProfile, ScopeSet
from shadow_hdk.kernel.ports import Ask, Context, GovernancePort, Refuse
from tests.adapters.contract import GovernancePortContract

EVERYTHING = ScopeSet(everything=True)
WORKSPACE = ScopeSet.of("workspace")
RECORD = ScopeSet.of("record")


def a_context(**attributes: object) -> Context:
    return Context(run_id="r", step="s", principal=None, attributes=dict(attributes))  # type: ignore[arg-type]


HOUSE = Rule(
    name="house",
    ceiling=EffectProfile(reads=EVERYTHING, writes=EVERYTHING, reversible=False, costs=True),
)
READING = Rule(
    name="reading",
    ceiling=EffectProfile(reads=EVERYTHING, costs=True),
    applies_to=frozenset({"reading"}),
)
FRUGAL = Rule(
    name="frugal",
    ceiling=EffectProfile(reads=EVERYTHING, writes=EVERYTHING, reversible=False),
    applies_to=frozenset({"frugal"}),
)


def test_a_rule_with_no_names_always_applies() -> None:
    rules = RuleSet((HOUSE, READING))
    assert rules.under(frozenset()).ceiling == HOUSE.ceiling


def test_every_applicable_row_applies_and_they_intersect() -> None:
    """Not first-match. Both `reading` and `frugal` are selected, so the result is narrower than
    either: no writes (from reading) **and** no spending (from frugal)."""
    rules = RuleSet((HOUSE, READING, FRUGAL))
    combined = rules.under(frozenset({"reading", "frugal"})).ceiling
    assert combined.writes == ScopeSet(), "reading did not remove writes"
    assert combined.costs is False, "frugal did not remove spending"
    for rule in (HOUSE, READING, FRUGAL):
        assert combined.narrows(rule.ceiling), f"the result is wider than {rule.name!r}"


@pytest.mark.parametrize(
    "selection", [frozenset(), frozenset({"reading"}), frozenset({"reading", "frugal"})]
)
def test_the_result_never_widens_whatever_is_selected(selection: frozenset[str]) -> None:
    """The property the whole design rests on: selecting more can only narrow."""
    rules = RuleSet((HOUSE, READING, FRUGAL))
    assert rules.under(selection).ceiling.narrows(HOUSE.ceiling)


def test_a_name_no_rule_claims_is_refused_rather_than_ignored() -> None:
    """A typo that quietly selects nothing is a typo that quietly widens — the deployment gets the
    house rules and nobody is told the tightening they asked for did not happen."""
    rules = RuleSet((HOUSE, READING))
    with pytest.raises(ValueError, match="reeding"):
        rules.under(frozenset({"reeding"}))


async def test_a_refusal_names_the_rule_that_refused() -> None:
    """R5: *explain any setting's value and where it came from.* A refusal that does not say which
    rule produced it cannot be argued with, corrected, or audited."""
    governance = RuleGovernance(RuleSet((HOUSE, READING)), selects="mode")
    judged = await governance.judge(
        EffectProfile(writes=WORKSPACE, reversible=False), a_context(mode="reading")
    )
    assert isinstance(judged, Refuse)
    assert "reading" in judged.reason, judged.reason


async def test_an_ask_line_composes_the_same_way() -> None:
    """If any applicable rule wants to be asked, it is asked."""
    careful = Rule(
        name="careful",
        ceiling=EffectProfile(reads=EVERYTHING, writes=EVERYTHING, reversible=False, costs=True),
        ask_above=EffectProfile(reads=EVERYTHING),
        applies_to=frozenset({"careful"}),
    )
    governance = RuleGovernance(RuleSet((HOUSE, careful)), selects="mode")
    judged = await governance.judge(EffectProfile(writes=RECORD), a_context(mode="careful"))
    assert isinstance(judged, Ask), judged
    assert "careful" in judged.question, judged.question


async def test_what_is_allowed_is_allowed() -> None:
    from shadow_hdk.kernel.ports import Allow

    governance = RuleGovernance(RuleSet((HOUSE,)), selects="mode")
    judged = await governance.judge(EffectProfile(reads=WORKSPACE), a_context())
    assert isinstance(judged, Allow)


def test_a_mode_is_the_one_row_case() -> None:
    """`adapters/modes` keeps working — this phase generalised it rather than replacing it."""
    from shadow_hdk.adapters.modes import Mode, layer

    narrow = layer(
        Mode("house", HOUSE.ceiling), Mode("reading", EffectProfile(reads=EVERYTHING, costs=True))
    )
    assert narrow.ceiling.writes == ScopeSet()
    assert narrow.ceiling.narrows(HOUSE.ceiling)


def test_a_set_that_grants_nothing_permits_nothing() -> None:
    """Fail closed, and the mutation that found this gap is the reason it is written down.

    Intersecting zero rows has to yield the **empty** profile. The tempting alternative — treat "no
    rules" as "no restrictions" — inverts the whole design at exactly the moment it matters most: a
    rule file that failed to load, a selection that matched nothing, a deployment mid-configuration.
    Every one of those should grant nothing and be noticed, not grant everything and be quiet.
    """
    nothing = RuleSet(()).under(frozenset()).ceiling
    assert nothing == EffectProfile()
    assert nothing.reads == ScopeSet() and nothing.writes == ScopeSet()
    assert not nothing.reaches and not nothing.costs


async def test_governance_over_an_empty_set_refuses_even_a_harmless_step() -> None:
    governance = RuleGovernance(RuleSet(()), selects="mode")
    judged = await governance.judge(EffectProfile(reads=WORKSPACE), a_context())
    assert isinstance(judged, Refuse), judged


class TestRuleGovernanceIsAGovernancePort(GovernancePortContract):
    """The rows, held to the shared shape (TD-004). A rule set that refuses everything is still a
    governance port: it must *answer*, and its answer must round-trip."""

    def port(self) -> GovernancePort:
        return RuleGovernance(RuleSet((HOUSE, READING)))
