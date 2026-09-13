"""A team rule that widens is refused before it runs (D24).

R5's middle clause, and the one with teeth: *refuse a team rule that widens*. `narrows` already
answers *may this step proceed*; this answers something earlier and stronger — **may this rule set
exist**, given what it was handed.

Checking the rules rather than the run matters because a rule that could never be reached is still
wrong, and a run that never happens to touch it never proves anything. It is a plain function
because two callers need it that are not each other: the loader refusing a bad file, and a host
validating rules somebody typed into a form.

The six-field sweep below is the point of the file. A check that caught a widening in `writes` and
missed one in `contained` would read as working right up until the day it mattered.
"""

from __future__ import annotations

import pytest

from shadow_hdk.adapters.modes import Rule, RuleSet, widens
from shadow_hdk.kernel.effects import EffectProfile, ScopeSet

EVERYTHING = ScopeSet(everything=True)
WORKSPACE = ScopeSet.of("workspace")
RECORD = ScopeSet.of("record")

CONSTITUTION = RuleSet(
    (
        Rule(
            name="house",
            ceiling=EffectProfile(
                reads=WORKSPACE,
                writes=WORKSPACE,
                reaches=False,
                reversible=True,
                contained=True,
                costs=False,
            ),
        ),
    )
)


def a_set(**changes: object) -> RuleSet:
    base = {
        "reads": WORKSPACE,
        "writes": WORKSPACE,
        "reaches": False,
        "reversible": True,
        "contained": True,
        "costs": False,
    }
    base.update(changes)
    return RuleSet((Rule(name="theirs", ceiling=EffectProfile(**base)),))  # type: ignore[arg-type]


def test_an_identical_set_does_not_widen() -> None:
    assert widens(a_set(), CONSTITUTION) == []


def test_a_narrower_set_does_not_widen() -> None:
    assert widens(a_set(writes=ScopeSet(), costs=False), CONSTITUTION) == []


WIDER = [
    ("reads", {"reads": EVERYTHING}),
    ("writes", {"writes": EVERYTHING}),
    ("reaches", {"reaches": True}),
    ("reversible", {"reversible": False}),
    ("contained", {"contained": False}),
    ("costs", {"costs": True}),
]


@pytest.mark.parametrize(("field", "change"), WIDER, ids=[name for name, _ in WIDER])
def test_widening_any_one_of_the_six_fields_is_caught_and_named(
    field: str, change: dict[str, object]
) -> None:
    """All six, separately. A check that caught `writes` and missed `contained` would read as
    working until the day it mattered — and `contained` is the one that decides whether code runs
    on the host or in a box."""
    found = widens(a_set(**change), CONSTITUTION)
    assert found, f"widening {field} was not caught"
    said = " ".join(f"{f.rule} {f.field}" for f in found)
    assert field in said, said
    assert "theirs" in said, said


def test_a_rule_the_constitution_does_not_have_still_has_to_narrow() -> None:
    """A new row is not a loophole. Nothing in the constitution names `overnight`, and it is still
    checked against what the constitution permits — otherwise widening would only ever be a matter
    of inventing a name nobody had used."""
    theirs = RuleSet(
        (
            Rule(
                name="overnight",
                ceiling=EffectProfile(reads=EVERYTHING, writes=EVERYTHING, costs=True),
                applies_to=frozenset({"overnight"}),
            ),
        )
    )
    found = widens(theirs, CONSTITUTION)
    assert found, "a rule the constitution never named was waved through"
    assert all(f.rule == "overnight" for f in found), found


def test_the_finding_reads_as_a_sentence() -> None:
    """It is shown to whoever wrote the file, so it has to say what to change."""
    found = widens(a_set(reaches=True), CONSTITUTION)
    assert str(found[0]), "a finding with no text is a finding nobody can act on"
    assert "reaches" in str(found[0])
    assert "theirs" in str(found[0])


def test_an_empty_set_never_widens() -> None:
    """Permitting nothing is the narrowest thing there is."""
    assert widens(RuleSet(()), CONSTITUTION) == []


def test_the_check_covers_every_field_the_kernel_has() -> None:
    """The guard for the day the vocabulary grows.

    `09` §2 says the effect vocabulary may grow, and D22 says the same of the port set — so a
    seventh field is expected, not hypothetical. A check that silently ignored it would keep passing
    while quietly permitting anything that field allows, which is the worst way for a safety check
    to fail. This fails the moment the kernel grows one and `check.py` has not caught up.
    """
    from dataclasses import fields as dataclass_fields

    from shadow_hdk.adapters.modes import FIELDS
    from shadow_hdk.kernel.effects import EffectProfile

    assert set(FIELDS) == {f.name for f in dataclass_fields(EffectProfile)}


@pytest.mark.parametrize(
    "field", ["reads", "writes", "reaches", "reversible", "contained", "costs"]
)
def test_every_field_in_the_vocabulary_is_actually_compared(field: str) -> None:
    """Naming a field in `FIELDS` is not the same as comparing it.

    The test above proves the *list* is complete; this proves each entry is wired to a comparison.
    A field added to `FIELDS` and forgotten in `_compare` would pass the first and fail here.
    """
    wider: dict[str, object] = {
        "reads": {"reads": EVERYTHING},
        "writes": {"writes": EVERYTHING},
        "reaches": {"reaches": True},
        "reversible": {"reversible": False},
        "contained": {"contained": False},
        "costs": {"costs": True},
    }[field]  # type: ignore[assignment]
    found = widens(a_set(**wider), CONSTITUTION)
    assert [f.field for f in found] == [field], found


def test_everything_widens_a_constitution_that_permits_nothing() -> None:
    """The other side of failing closed. If the thing being narrowed towards grants nothing, then
    any rule granting anything is a widening — including one that only reads."""
    found = widens(a_set(reads=WORKSPACE, writes=ScopeSet()), RuleSet(()))
    assert [f.field for f in found] == ["reads"], found


# ---------------------------------------------------------------- the ask line (BUG-012)

ASKS = RuleSet(
    (
        Rule(
            name="house",
            ceiling=EffectProfile(reads=EVERYTHING, writes=WORKSPACE, reversible=False),
            ask_above=EffectProfile(reads=WORKSPACE),
        ),
    )
)
"""A constitution that permits a good deal and **pauses** for most of it. The ceiling is what may
happen at all; the ask line is what may happen without anyone being told."""


def with_ask(ask: EffectProfile | None) -> RuleSet:
    return RuleSet(
        (
            Rule(
                name="theirs",
                ceiling=EffectProfile(reads=EVERYTHING, writes=WORKSPACE, reversible=False),
                ask_above=ask,
            ),
        )
    )


def test_a_rule_that_never_asks_widens_one_that_does() -> None:
    """The bug. Both sets have the same ceiling, so the six-field sweep finds nothing — and yet
    one of them pauses before an irreversible write and the other simply does it.

    A check that reads only ceilings says a team may replace every approval in the deployment with
    nothing, which is the widening that matters most to whoever has to sign for it.
    """
    found = widens(with_ask(None), ASKS)

    assert [w.field for w in found] == ["ask_above"]
    assert "never asks" in str(found[0])


def test_a_rule_that_asks_later_widens() -> None:
    """Not only the absent ask line: one drawn further out is the same widening, by degrees. Here
    theirs would act on the whole filesystem before anybody is asked."""
    found = widens(with_ask(EffectProfile(reads=EVERYTHING)), ASKS)

    assert [w.field for w in found] == ["reads"]
    assert "ask" in found[0].rule, f"the finding does not say it is about the ask line: {found[0]}"


def test_a_rule_that_asks_earlier_does_not_widen() -> None:
    """Asking sooner than the house does is narrowing, and must be allowed — a team is free to be
    more cautious than the deployment requires."""
    assert widens(with_ask(EffectProfile()), ASKS) == []


def test_an_identical_ask_line_does_not_widen() -> None:
    assert widens(with_ask(EffectProfile(reads=WORKSPACE)), ASKS) == []


def test_a_set_that_asks_where_the_house_never_does_is_not_wider() -> None:
    """The asymmetry is deliberate. A house that never asks has drawn no line to cross, so a team
    that adds one is adding caution — and a check that called that a widening would refuse the one
    change nobody should ever have to argue for.

    The ceiling here is the constitution's own, so nothing but the ask line is under test.
    """
    cautious = RuleSet(
        (
            Rule(
                name="theirs",
                ceiling=EffectProfile(
                    reads=WORKSPACE,
                    writes=WORKSPACE,
                    reaches=False,
                    reversible=True,
                    contained=True,
                    costs=False,
                ),
                ask_above=EffectProfile(reads=WORKSPACE),
            ),
        )
    )

    assert widens(cautious, CONSTITUTION) == []
