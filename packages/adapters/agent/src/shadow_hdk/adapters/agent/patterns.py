"""The patterns the framework ships. A team adds its own the same way — a file.

`single` is the whole of Phase 0: one reasoning loop over its tools, no ability to change its own
shape. The four that need composition and sub-agents arrive in Phase 8, and each is a `Pattern`
plus a role file, never a runtime change.
"""

from __future__ import annotations

from shadow_hdk.adapters.agent.pattern import DONE, PROPOSE, Pattern

SINGLE_ROLE = """You are working on one task, using the tools you are given.

Call tools to find things out and to act. You may call several at once when they do not depend on
each other. When you have something worth keeping, call `propose`. When the task is finished — or
you are certain it cannot be finished — call `done` and say what happened.

You cannot change how you work: you have these tools and these turns. Use them."""

single = Pattern(
    name="single",
    system=SINGLE_ROLE,
    meta_tools=frozenset({PROPOSE, DONE}),
)
"""One reasoning loop over its tools. No `compose`, so the model cannot change its own shape —
which is what makes a deterministic one-agent product possible on this runtime."""

__all__ = ["SINGLE_ROLE", "single"]
