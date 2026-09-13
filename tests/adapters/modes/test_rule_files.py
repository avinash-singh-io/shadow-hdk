"""Rules a team writes, checked when they are read.

D17 made patterns and skills files a team edits, and gave the reasons — TOML because a role is
prose and `tomllib` costs no dependency. Rules follow, with one difference that is the whole point
of D24: a rule file can be handed the constitution it must narrow, and if it widens anywhere it is
**refused at load**, with the rule and the field, rather than discovered three steps into a run.

Every refusal names the word that is wrong, because the reader is the person who wrote the file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.adapters.modes import Rule, RuleSet, load_rules, shipped_example
from shadow_hdk.kernel.effects import EffectProfile, ScopeSet

WORKSPACE = ScopeSet.of("workspace")
EVERYTHING = ScopeSet(everything=True)

HOUSE = RuleSet(
    (
        Rule(
            name="house",
            ceiling=EffectProfile(
                reads=EVERYTHING, writes=WORKSPACE, reaches=True, reversible=False, costs=True
            ),
        ),
    )
)

A_TEAM = """
[[rule]]
name = "reading"
applies_to = ["reading"]

[rule.ceiling]
reads = { everything = true }
costs = true

[[rule]]
name = "careful"
applies_to = ["careful"]

[rule.ceiling]
reads = { everything = true }
writes = { names = ["workspace"] }
reversible = false
costs = true

[rule.ask_above]
reads = { everything = true }
"""


def _written(tmp_path: Path, body: str = A_TEAM, name: str = "team.toml") -> Path:
    path = tmp_path / name
    path.write_text(body.strip() + "\n", encoding="utf-8")
    return path


def test_a_rule_file_loads_into_rows(tmp_path: Path) -> None:
    rules = load_rules(_written(tmp_path))
    assert [r.name for r in rules.rules] == ["reading", "careful"]
    careful = rules.rules[1]
    assert careful.applies_to == frozenset({"careful"})
    assert careful.ceiling.writes == WORKSPACE
    assert careful.ceiling.reversible is False
    assert careful.ask_above is not None and careful.ask_above.reads == EVERYTHING


def test_a_file_that_narrows_its_constitution_is_accepted(tmp_path: Path) -> None:
    rules = load_rules(_written(tmp_path), narrowing=HOUSE)
    assert len(rules) == 2


def test_a_file_that_widens_is_refused_at_load_naming_rule_and_field(tmp_path: Path) -> None:
    """R5, literally: *refuse a team rule that widens.* The house permits writes to the workspace
    only; this file's `overnight` rule writes everywhere."""
    wider = (
        A_TEAM
        + """
[[rule]]
name = "overnight"
applies_to = ["overnight"]

[rule.ceiling]
reads = { everything = true }
writes = { everything = true }
"""
    )
    with pytest.raises(ValueError) as refused:
        load_rules(_written(tmp_path, wider), narrowing=HOUSE)
    message = str(refused.value)
    assert "overnight" in message, message
    assert "writes" in message, message
    assert "team.toml" in message, message


@pytest.mark.parametrize(
    ("body", "says"),
    [
        ('[[rule]]\nname = "x"\nceiling = {}\nextra = 1\n', "extra"),
        ("[[rule]]\nceiling = {}\n", "name"),
        ('[[rule]]\nname = "x"\n', "ceiling"),
        ('[[rule]]\nname = "x"\n[rule.ceiling]\nflies = true\n', "flies"),
        # "list", not "rule" — every label in this loader contains the word rule, so asserting
        # on it cannot tell the right refusal from a wrong one. A mutation that let a string
        # through survived on exactly that.
        ('rule = "not a list"\n', "list"),
    ],
    ids=["unknown key", "no name", "no ceiling", "unknown effect field", "rules not a list"],
)
def test_a_bad_file_is_refused_by_name(tmp_path: Path, body: str, says: str) -> None:
    with pytest.raises(ValueError) as refused:
        load_rules(_written(tmp_path, body, name="bad.toml"))
    message = str(refused.value)
    assert says in message, message
    assert "bad.toml" in message, message


def test_two_rules_with_one_name_are_refused(tmp_path: Path) -> None:
    """A refusal names the rule; two rules sharing a name make that name mean nothing."""
    twice = '[[rule]]\nname = "same"\nceiling = {}\n\n[[rule]]\nname = "same"\nceiling = {}\n'
    with pytest.raises(ValueError, match="same"):
        load_rules(_written(tmp_path, twice, name="twice.toml"))


def test_the_shipped_example_loads_and_narrows_something_permissive() -> None:
    """A file a team can copy, and proof it is not itself wrong."""
    example = shipped_example()
    assert len(example) >= 2, "an example with one rule does not show rows composing"
    permissive = RuleSet(
        (
            Rule(
                name="anything",
                ceiling=EffectProfile(
                    reads=EVERYTHING,
                    writes=EVERYTHING,
                    reaches=True,
                    reversible=False,
                    contained=False,
                    costs=True,
                ),
            ),
        )
    )
    from shadow_hdk.adapters.modes import widens

    assert widens(example, permissive) == []
