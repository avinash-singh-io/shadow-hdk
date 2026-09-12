"""Governance as data.

`09` §8 puts the *engine* here and the *rules* in the product. A mode is the smallest useful shape
of a rule: the widest thing anything may do, and the line above which it must ask first. Everything
else — which modes exist, what they are called, who may select one — is the product's.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import Allow, Ask, Context, GovernancePort, Judgement, Refuse


@dataclass(frozen=True)
class Mode:
    name: str
    ceiling: EffectProfile
    """The widest thing anything may do in this mode. Beyond it is refused, never asked."""
    ask_above: EffectProfile | None = None
    """Narrower than the ceiling. Inside it, go ahead; outside it but inside the ceiling, ask.

    `None` means *never ask* — a thing a product may want, and the adapter will not second-guess,
    but it has to be said rather than inherited.
    """


def layer(base: Mode, over: Mode) -> Mode:
    """Compose two modes. **The result can only be narrower than both.**

    That is `EffectProfile.meet`, which the kernel property-tests as a greatest lower bound — so
    "a team may tighten what it was given and never loosen it" is arithmetic here, not a review
    comment. The ask line composes the same way: if either layer wants to be asked, it is asked.
    """
    ask: EffectProfile | None
    if base.ask_above is None:
        ask = over.ask_above
    elif over.ask_above is None:
        ask = base.ask_above
    else:
        ask = base.ask_above.meet(over.ask_above)
    return Mode(name=over.name or base.name, ceiling=base.ceiling.meet(over.ceiling), ask_above=ask)


class ModeGovernance(GovernancePort):
    def __init__(
        self,
        modes: Mapping[str, Mode],
        *,
        default: str,
        key: str = "mode",
        rules: Any = None,
    ) -> None:
        """`rules`: the host's `ActRules` (D65), consulted **after** this mode's own judgement says
        *ask* — a matching `allow` rule stands in for the person, a matching `deny` refuses without
        asking. Read at every judgement, so a rule added at answer time holds at the next step.
        A rule never widens a ceiling: what the mode refuses stays refused."""
        if default not in modes:
            raise ValueError(f"default mode {default!r} is not one of {sorted(modes)}")
        self._modes = dict(modes)
        self._default = default
        self._key = key
        self._rules = rules

    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        selected = context.attributes.get(self._key, self._default)
        name = selected if isinstance(selected, str) else self._default
        mode = self._modes.get(name)
        if mode is None:
            # **Never fall back to a wider mode.** The dangerous failure is silent widening: a typo
            # resolving to whatever the default happens to be. Refuse, and say which name it was.
            return Refuse(f"{name!r} is not a mode here; known modes are {sorted(self._modes)}")
        if not effects.narrows(mode.ceiling):
            return Refuse(f"mode {mode.name!r} does not permit this")
        if mode.ask_above is not None and not effects.narrows(mode.ask_above):
            ruled = self._ruled(context, name)
            if ruled == "allow":
                return Allow()
            if ruled == "deny":
                return Refuse(f"a rule in mode {mode.name!r} refuses this act")
            return Ask(f"mode {mode.name!r} asks before this: {_why(effects, mode.ask_above)}")
        return Allow()

    def _ruled(self, context: Context, mode: str) -> str | None:
        """What the host's rules say about this act, if they know it (D65)."""
        if self._rules is None:
            return None
        component = context.attributes.get("component")
        if not isinstance(component, str):
            return None
        decided = self._rules.decide(component, context.attributes.get("inputs"), mode=mode)
        return decided if isinstance(decided, str) else None


def _why(effects: EffectProfile, line: EffectProfile) -> str:
    """Which field crossed the line — so a person being asked is told what they are answering."""
    reasons = []
    if not effects.reads <= line.reads:
        reasons.append("it reads more than usual")
    if not effects.writes <= line.writes:
        reasons.append("it writes more than usual")
    if effects.reaches and not line.reaches:
        reasons.append("it reaches outside")
    if not effects.reversible and line.reversible:
        reasons.append("it is irreversible")
    if not effects.contained and line.contained:
        reasons.append("it is not contained")
    if effects.costs and not line.costs:
        reasons.append("it costs money")
    return ", ".join(reasons) or "it is outside the usual"


__all__ = ["Mode", "ModeGovernance", "layer"]
