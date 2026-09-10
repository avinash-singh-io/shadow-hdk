"""Rules as rows over effect profiles, composed by intersection (`09` §11).

A `Mode` is the one-row case: one ceiling, one ask line. A real deployment has several — the house
rules, what this tenant tightened, what this run was narrowed to — and they have to compose without
anybody being able to widen anything.

**Every applicable row applies.** There is no first match and no ordering, because order is a hidden
operator: two rule sets with the same rows in different orders would mean different things, and
neither a reader nor the narrowing check could see the difference. Rows intersect, and intersection
is commutative, so a rule set is a *set*.

**A rule selects by name, never by predicate** (D23). `09` §2 refuses a free-form predicate in the
effect vocabulary because it turns a proof into a linter, and a selector inherits the argument: two
rule sets can be compared only if what they say is comparable, and one condition implying another is
undecidable in general. The host decides which names are in play — from its ladder, its tenancy, its
hour of the day — and hands them in. All the conditionality lives on the host's side of the port.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import Allow, Ask, Context, GovernancePort, Judgement, Refuse


@dataclass(frozen=True)
class Rule:
    """One row. What it permits, where it wants to be asked, and when it applies."""

    name: str
    ceiling: EffectProfile
    """The widest thing anything may do while this rule applies. Beyond it is refused."""
    ask_above: EffectProfile | None = None
    """Narrower than the ceiling. Inside it, go ahead; outside it but inside the ceiling, ask.
    `None` means never ask — which has to be said rather than inherited."""
    applies_to: frozenset[str] = field(default_factory=frozenset)
    """Names that select this rule. **Empty means always**, which is how house rules are written."""


@dataclass(frozen=True)
class Selected:
    """The rules in force, and what they add up to."""

    rules: tuple[Rule, ...]
    ceiling: EffectProfile
    ask_above: EffectProfile | None

    def refuses(self, effects: EffectProfile) -> str | None:
        """Why these effects are refused, or `None` if they are not.

        R5 asks that a value can be explained, so when a row refuses, the answer names it. But the
        check is against the **composed** ceiling first, not row by row — because with zero rows in
        force there is no row to blame, and the first version of this looked for one, found none,
        and let the step through. A set that grants nothing must refuse, and say so.
        """
        if effects.narrows(self.ceiling):
            return None
        for rule in self.rules:
            if not effects.narrows(rule.ceiling):
                return f"rule {rule.name!r} does not permit this"
        return "no rule is in force here, so nothing is permitted"

    def who_asks(self, effects: EffectProfile) -> Rule | None:
        for rule in self.rules:
            if rule.ask_above is not None and not effects.narrows(rule.ask_above):
                return rule
        return None


class RuleSet:
    """Several rows, and what any selection of them comes to."""

    def __init__(self, rules: Iterable[Rule]) -> None:
        self.rules = tuple(rules)
        self.names = frozenset().union(*(rule.applies_to for rule in self.rules)) or frozenset()

    def __len__(self) -> int:
        return len(self.rules)

    def under(self, selection: Iterable[str]) -> Selected:
        """Every applicable row, intersected.

        A name no rule claims is an **error**, not a no-op. A typo that quietly selects nothing is a
        typo that quietly widens: the deployment falls back to the house rules and nobody is told
        that the tightening they asked for never happened.
        """
        wanted = frozenset(selection)
        unknown = wanted - self.names
        if unknown:
            raise ValueError(
                f"no rule is selected by {sorted(unknown)}; "
                f"the names this set knows are {sorted(self.names)}"
            )
        applicable = tuple(
            rule for rule in self.rules if not rule.applies_to or rule.applies_to & wanted
        )
        ceiling = _meet_all(rule.ceiling for rule in applicable)
        asks = [rule.ask_above for rule in applicable if rule.ask_above is not None]
        return Selected(
            rules=applicable,
            ceiling=ceiling,
            ask_above=_meet_all(asks) if asks else None,
        )


def _meet_all(profiles: Iterable[EffectProfile]) -> EffectProfile:
    """Intersection over any number of rows, including none.

    With nothing to intersect the answer is the **empty** profile — permitting nothing — rather than
    a permissive one. A rule set that selected no rows granting anything should grant nothing.
    """
    result: EffectProfile | None = None
    for profile in profiles:
        result = profile if result is None else result.meet(profile)
    return result if result is not None else EffectProfile()


class RuleGovernance(GovernancePort):
    """A governance port over a rule set, whose answers name the rule that produced them."""

    def __init__(
        self, rules: RuleSet, *, selects: str = "mode", always: Iterable[str] = ()
    ) -> None:
        self._rules = rules
        self._selects = selects
        self._always = frozenset(always)

    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        try:
            selected = self._rules.under(self._always | _names_in(context, self._selects))
        except ValueError as unknown:
            # Never fall back to a wider set. The dangerous failure is silent widening.
            return Refuse(str(unknown))
        refused = selected.refuses(effects)
        if refused is not None:
            return Refuse(refused)
        asking = selected.who_asks(effects)
        if asking is not None:
            return Ask(f"rule {asking.name!r} asks before this")
        return Allow()


def _names_in(context: Context, key: str) -> frozenset[str]:
    """What the host selected. A list or a single name; anything else selects nothing."""
    value = context.attributes.get(key)
    if isinstance(value, str):
        return frozenset({value})
    if isinstance(value, list):
        return frozenset(item for item in value if isinstance(item, str))
    return frozenset()


__all__ = ["Rule", "RuleGovernance", "RuleSet", "Selected"]
