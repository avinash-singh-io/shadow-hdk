"""The host's own governance — a judgement over effects, and nothing else.

A policy here never sees a tool's *name*. It sees what the tool declared it does — `reads`,
`writes`, `reaches`, `reversible`, `contained`, `costs` — and a component that declared nothing was
registered as doing everything (09 §2). That is the whole of "govern effects, not names".
"""

from __future__ import annotations

from shadow_hdk.kernel import Allow, Ask, Context, EffectProfile, Refuse, ScopeSet
from shadow_hdk.kernel.ports import Judgement

WORKSPACE = ScopeSet.of("workspace")
OURS = ScopeSet.of("workspace", "record")
"""Where this host lets a run write without asking: the workspace it was given, and the host's own
record — a proposal into the ledger (a minted skill, a finding) is the host's to receive, and the
sink is where it decides what becomes of it."""


class Policy:
    """Reads anywhere; writes inside the workspace or to the host's record; a write anywhere else
    is the host's to decide; the network is not on offer.

    An `Ask` at the top of a run parks it until the host answers (proven). An `Ask` for a tool call
    *inside* an agent does not yet reach the host — the child parks and the model is told the step
    did not run (BUG-020) — so a host whose agents may write outside the workspace should run them
    inside an environment that confines the write instead, and let the environment's mode say so.
    """

    def __init__(self, *, allow_network: bool = False) -> None:
        self.allow_network = allow_network
        self.judged = 0

    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        self.judged += 1
        if effects.reaches and not self.allow_network:
            return Refuse("this host allows nothing to reach the network")
        if not (effects.writes <= OURS):
            where = (
                "everything"
                if effects.writes.everything
                else ", ".join(sorted(effects.writes.names))
            )
            return Ask(
                f"step {context.step!r} wants to write outside the workspace ({where}); allow it?"
            )
        return Allow()


__all__ = ["OURS", "Policy", "WORKSPACE"]
