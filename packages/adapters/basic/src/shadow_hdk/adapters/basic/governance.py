"""Allow-all, and the one rule about posture that is the runtime's to state.

`AllowAll` is deliberately not called `DefaultGovernance`. A deployment that ships this in
production has no policy, and the name should say so every time someone reads the composition root.

`Controlled` is `08` §4's sentence made executable: *only controlled satisfies
consent-before-effect*. An observed component reports what already happened without us; an effect
it would perform cannot be consented to before it happens, so `Controlled` refuses it — for writes
and reaches, which are the effects consent is about — and admits its reads, because a reading is
evidence. Everything else is the inner policy's.
"""

from __future__ import annotations

from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import Allow, Context, GovernancePort, Judgement, Refuse


class AllowAll(GovernancePort):
    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        return Allow()


class Controlled(GovernancePort):
    def __init__(self, inner: GovernancePort) -> None:
        self._inner = inner

    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        posture = context.attributes.get("posture")
        if posture == "observed" and (
            effects.writes.names or effects.writes.everything or effects.reaches
        ):
            component = context.attributes.get("component", "this component")
            return Refuse(
                f"{component} is observed, not controlled: an effect it performs cannot be "
                "consented to before it happens"
            )
        return await self._inner.judge(effects, context)
