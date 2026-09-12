"""The projection, rendered — what a client shows as "agent steps".

`run_items` folds the event stream into `Item`s (Phase 21): one per step, with what the model
thought first, what the step observed, what it cost, and the steps of every run it spawned nested
under it. This renders each as it completes. A UI would draw the same object; the fold is the
runtime's, the drawing is the host's.
"""

from __future__ import annotations

from shadow_hdk.runtime.items import Item

DIM, OFF = "\033[2m", "\033[0m"
MARK = {"completed": "✓", "failed": "✗", "refused": "✕", "approval_requested": "?", "running": "…"}


def lines_for(step: Item, *, depth: int = 0, tree: bool = True) -> list[str]:
    """One line per step — and, as a `tree`, its children indented under it with what it thought.

    Live, a host renders each step as it closes (`run_items(nested=True)`), the children before the
    parent, and reasoning as it lands; `tree=False` is that one line. `tree=True` is the late
    reader's view of the finished projection.
    """
    pad = "  " * depth
    who = step.component or step.step
    out = []
    if step.reasoning and tree:
        thought = step.reasoning.strip().replace("\n", " ")
        out.append(f"{pad}\033[36m∴ {thought[:160]}{OFF}")
    cost = f" {DIM}({step.usage.cost_cents}¢){OFF}" if step.usage and step.usage.cost_cents else ""
    # A refusal before the step ran carries its reason on the step; a refusal that *answered a
    # question* is the step's observation — the host's own "no", on the record where the step is.
    why = step.reason or getattr(step.observation, "reason", None)
    tail = f" — {why}" if why else ""
    seen = ""
    if step.observation is not None and step.outcome == "completed":
        seen = f" {DIM}→ {str(step.observation)[:100]}{OFF}"
    out.append(f"{pad}{MARK.get(step.outcome, '·')} {who}{tail}{seen}{cost}")
    if tree:
        for child in step.children:
            out.extend(lines_for(child, depth=depth + 1))
    return out


def thought(text: str, *, depth: int = 0) -> str:
    """A `Reasoning` event as it lands — before the act it precedes, which is the whole point."""
    return f"{'  ' * depth}\033[36m∴ {text.strip().replace(chr(10), ' ')[:160]}{OFF}"


__all__ = ["lines_for", "thought"]
