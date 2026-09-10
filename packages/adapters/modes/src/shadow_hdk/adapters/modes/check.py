"""The narrowing check, as a library (D24).

`EffectProfile.narrows` answers *may this step proceed*. R5 asks something earlier and stronger:
**may this rule set exist**, given what it was handed.

Checking the rules rather than the run matters because a rule that could never be reached is still
wrong, and a run that never happens to touch it never proves anything. A plain function rather than
a method, because two callers need it that are not each other — the loader, refusing a bad file, and
a host validating rules somebody typed into a form before it stores them.

**What "wider" means here.** Every rule in the set under test is compared against the tightest thing
the given set would ever permit, which is what all of its always-rules come to. A rule the given set
never named is not a loophole: it is checked the same way, or widening would only ever be a matter
of inventing a name nobody had used.
"""

from __future__ import annotations

from dataclasses import dataclass

from shadow_hdk.adapters.modes.rules import RuleSet

from shadow_hdk.kernel.effects import EffectProfile

FIELDS = ("reads", "writes", "reaches", "reversible", "contained", "costs")
"""The closed vocabulary, in the order a person reads them. A seventh field must appear here as
well as in the kernel — `test_the_check_covers_every_field_the_kernel_has` fails until it does."""


@dataclass(frozen=True)
class Wider:
    """One rule, one field, wider than it was allowed to be."""

    rule: str
    field: str
    allowed: object
    asked_for: object

    def __str__(self) -> str:
        return (
            f"rule {self.rule!r} widens {self.field}: "
            f"it may be {self.allowed!r} and asks for {self.asked_for!r}"
        )


def widens(theirs: RuleSet, ours: RuleSet) -> list[Wider]:
    """Every place `theirs` permits more than `ours` does. Empty means it may exist."""
    allowed = ours.under(frozenset()).ceiling
    found: list[Wider] = []
    for rule in theirs.rules:
        found.extend(_compare(rule.name, rule.ceiling, allowed))
    return found


def _compare(name: str, asked: EffectProfile, allowed: EffectProfile) -> list[Wider]:
    found: list[Wider] = []
    if not asked.reads <= allowed.reads:
        found.append(Wider(name, "reads", allowed.reads, asked.reads))
    if not asked.writes <= allowed.writes:
        found.append(Wider(name, "writes", allowed.writes, asked.writes))
    if asked.reaches and not allowed.reaches:
        found.append(Wider(name, "reaches", False, True))
    # The three below read backwards on purpose: `reversible` and `contained` are *safety* flags, so
    # true is the narrow end, while `reaches` and `costs` are *capability* flags and false is.
    if not asked.reversible and allowed.reversible:
        found.append(Wider(name, "reversible", True, False))
    if not asked.contained and allowed.contained:
        found.append(Wider(name, "contained", True, False))
    if asked.costs and not allowed.costs:
        found.append(Wider(name, "costs", False, True))
    return found


__all__ = ["FIELDS", "Wider", "widens"]
