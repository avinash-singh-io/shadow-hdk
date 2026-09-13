"""An act rule: "yes, and don't ask again" as data (D65).

Every product has it — Claude Code's "yes, and don't ask again", scoped per repository and
command; Codex's `acceptWithExecpolicyAmendment`. Ours names the **act**: a component and the
inputs it applies to, a decision, and optionally the mode it holds in. Governance consults the
host's rules after its own judgement says *ask*: a matching `allow` rule stands in for the person,
a matching `deny` refuses without asking. A rule is made at answer time (`ApproveAndAddRule`),
kept by the host's registry, read at the next judgement — live — and proposed through the sink so
the record says a rule was made, by what, and about what.

Matching is exact on every input the rule names, with one loosening: a string ending in `*`
matches by prefix. A rule that names no inputs matches every act of that component. Nothing
here is a predicate (D23): a rule is rows a person can read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import JsonValue


@dataclass(frozen=True)
class ActRule:
    component: str
    inputs: dict[str, JsonValue] = field(default_factory=dict)
    """The inputs the rule applies to: every named key must match. A string ending in `*`
    matches by prefix; an empty mapping matches every act of the component."""
    decision: Literal["allow", "deny"] = "allow"
    mode: str = ""
    """The mode this holds in; empty for every mode."""
    note: str = ""
    """Why — the person's words, when they gave any."""

    def matches(self, component: str, inputs: Any, *, mode: str = "") -> bool:
        if component != self.component:
            return False
        if self.mode and self.mode != mode:
            return False
        given = inputs if isinstance(inputs, dict) else {}
        for key, wanted in self.inputs.items():
            if key not in given:
                return False
            actual = given[key]
            if isinstance(wanted, str) and wanted.endswith("*"):
                if not (isinstance(actual, str) and actual.startswith(wanted[:-1])):
                    return False
            elif actual != wanted:
                return False
        return True


__all__ = ["ActRule"]
