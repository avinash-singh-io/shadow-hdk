"""A pattern is an agent architecture, as data.

What a pattern decides: the role prompt, **which meta-tools the model is even shown** (D3), which
of the visible components this role sees, how many turns it may take, and a ceiling narrowing this
role beyond whatever the deployment's mode already allows.

Everything here is JSON-able on purpose. A pattern is meant to ship as a *file* a team can read and
edit, so it holds no callables — a tool filter is a set of names, not a predicate. Names are for
discovery; permission is still `ceiling`, and still effects (`09` §2).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from shadow_hdk.kernel.effects import EffectProfile

COMPOSE = "compose"
PROPOSE = "propose"
DONE = "done"
META_TOOLS = frozenset({COMPOSE, PROPOSE, DONE})


@dataclass(frozen=True)
class Pattern:
    name: str
    system: str
    meta_tools: frozenset[str] = frozenset({PROPOSE, DONE})
    tool_names: frozenset[str] | None = None
    """`None` means every component the policy leaves visible; a set names this role's own."""
    ceiling: EffectProfile | None = None
    max_turns: int = 12
    nudge: str = field(
        default=(
            "You have not done enough work to say that yet. Try what is still open, "
            "or say done again and it will be accepted as unfinishable."
        )
    )

    def __post_init__(self) -> None:
        unknown = self.meta_tools - META_TOOLS
        if unknown:
            raise ValueError(f"unknown meta-tools: {sorted(unknown)}")

    def shows(self, name: str) -> bool:
        return self.tool_names is None or name in self.tool_names
