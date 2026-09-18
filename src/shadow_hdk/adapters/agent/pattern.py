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
from shadow_hdk.kernel.planning import PlanLimits

COMPOSE = "compose"
PROPOSE = "propose"
DONE = "done"
DESCRIBE = "describe"
COMPACT = "compact"
SPAWN = "spawn"
RECALL = "recall"
SEND = "send"
RELEASE = "release"
META_TOOLS = frozenset({COMPOSE, PROPOSE, DONE, DESCRIBE, COMPACT, SPAWN, SEND, RELEASE})

MAILBOX = "mailbox"
"""What a helper parks on, by convention (D16). This adapter cannot import `adapters/basic`, so the
name lives on both sides and a test pins them together — a convention with nothing holding it is a
rename waiting to break a spawn at runtime."""


@dataclass(frozen=True)
class Pattern:
    name: str
    system: str
    meta_tools: frozenset[str] = frozenset({PROPOSE, DONE})
    tool_names: frozenset[str] | None = None
    """`None` means every component the policy leaves visible; a set names this role's own."""
    ceiling: EffectProfile | None = None
    plan: PlanLimits | None = None
    """How much plan this pattern may author (D109) — met with the run's own at admission, so a
    pattern is never admitted a wider plan than its host allows. `None` defers to the run."""
    absorb: bool = True
    """Whether a plan this pattern authors is absorbed into its own turn — the results come back
    to the model as the answer to `compose` (the default, BUG-012) — or runs after the planner
    (D112): the planner's step closes on the admission and the plan runs on as a held child of
    the same parent run, its events on the record, nothing folded back into the transcript."""
    max_turns: int = 12
    offload_over: int | None = None
    """Large-result offloading (D47). A tool result rendering to more than this many characters
    reaches the model as a handle, a size and a preview, and `recall` pages the rest. Held by the
    agent for the run — never written anywhere, because the runtime has no write path and the
    record gets the whole observation regardless. `None` is off, and off is the default: what
    counts as large is the pattern's to say."""
    catalogue_threshold: int = 30
    """D13's fourth mechanism. At or above this many components the model is offered names and
    one-line descriptions, and pulls a schema on demand with `describe`. Below it nothing changes:
    a catalogue small enough to read whole is cheaper read whole than fetched twice."""
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
