"""Allow-all: the policy you start with, and the one the bare-harness test uses.

It is deliberately not called `DefaultGovernance`. A deployment that ships this in production has
no policy, and the name should say so every time someone reads the composition root.
"""

from __future__ import annotations

from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import Allow, Context, GovernancePort, Judgement


class AllowAll(GovernancePort):
    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        return Allow()
