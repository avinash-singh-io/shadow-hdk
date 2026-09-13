"""An act rule: "yes, and don't ask again" as data (D65).

Every product has it — Claude Code's "yes, and don't ask again", scoped per repository and
command; Codex's `acceptWithExecpolicyAmendment`. Ours names the **act**: a component and the
inputs it applies to, a decision, and optionally the mode it holds in. Governance consults the
host's rules after its own judgement says *ask*: a matching `allow` rule stands in for the person,
a matching `deny` refuses without asking. A rule is made at answer time (`ApproveAndAddRule`),
kept by the host's registry, read at the next judgement — live — and proposed through the sink so
the record says a rule was made, by what, and about what.

Matching is exact on every input the rule names, or by pattern where the rule's value has one
(D85): `**` matches across `/`; a `*` elsewhere and a `?` match within one path segment; `[…]`
is a character class; a `*` at the very end matches the rest whatever it is — the prefix rule
that always held (`notes/*`, `git *`). Matched against the input as the tool receives it, which
for a path is relative to the primary root or `name/…` for another root. A rule that names no
inputs matches every act of that component. Nothing here is a predicate (D23): a rule is rows a
person can read.

Three decisions (D85), read in Claude Code's order — deny, then ask, then the mode, then allow:
a `deny` refuses in every mode, `full` included; an `ask` puts the act to the person in every
mode; an `allow` stands in for the person only where the mode would have asked, because a rule
never widens a ceiling.

A rule may say who it is for (`scope`, D82): a principal's name, or `attribute:value` in the
product's own words — `tenant:acme`. Empty is everyone. The same word is on a mode.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import JsonValue


def pattern_matches(pattern: str, value: str) -> bool:
    """Whether `value` is one of the things `pattern` names (D85). `**` crosses `/`; `*` and `?`
    stay within a segment; `[…]` is a class; a `*` at the very end takes the rest, as the
    prefix rule always did."""
    out: list[str] = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if pattern.startswith("**", i):
                out.append(".*")
                i += 2
                continue
            out.append(".*" if i == len(pattern) - 1 else "[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "[":
            end = pattern.find("]", i + 1)
            if end == -1:
                out.append(re.escape(c))
            else:
                out.append(pattern[i : end + 1])
                i = end
        else:
            out.append(re.escape(c))
        i += 1
    return re.fullmatch("".join(out), value) is not None


def in_scope(scope: str, *, principal: str | None, attributes: Any) -> bool:
    """Whether a row scoped `scope` is for this principal with these attributes (D82). Empty is
    everyone; `name` is that principal; `key:value` is any principal whose attribute `key` is
    exactly `value` — a string, not a list of them, so a row cannot be widened by a shape."""
    if not scope:
        return True
    if ":" in scope:
        key, wanted = scope.split(":", 1)
        given = attributes if isinstance(attributes, dict) else {}
        return isinstance(given.get(key), str) and given[key] == wanted
    return principal is not None and principal == scope


@dataclass(frozen=True)
class ActRule:
    component: str
    inputs: dict[str, JsonValue] = field(default_factory=dict)
    """The inputs the rule applies to: every named key must match. A string ending in `*`
    matches by prefix; an empty mapping matches every act of the component."""
    decision: Literal["allow", "deny", "ask"] = "allow"
    mode: str = ""
    """The mode this holds in; empty for every mode."""
    note: str = ""
    """Why — the person's words, when they gave any."""
    scope: str = ""
    """Who it is for (D82): empty for everyone, a principal's name, or `attribute:value`."""

    def matches(
        self,
        component: str,
        inputs: Any,
        *,
        mode: str = "",
        principal: str | None = None,
        attributes: Any = None,
    ) -> bool:
        if component != self.component:
            return False
        if self.mode and self.mode != mode:
            return False
        if not in_scope(self.scope, principal=principal, attributes=attributes):
            return False
        given = inputs if isinstance(inputs, dict) else {}
        for key, wanted in self.inputs.items():
            if key not in given:
                return False
            actual = given[key]
            if isinstance(wanted, str) and any(c in wanted for c in "*?["):
                if not (isinstance(actual, str) and pattern_matches(wanted, actual)):
                    return False
            elif actual != wanted:
                return False
        return True


__all__ = ["ActRule", "in_scope", "pattern_matches"]
