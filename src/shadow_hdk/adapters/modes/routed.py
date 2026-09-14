"""Governance composed by routing (D92): one port per component, another for the rest.

A product often has two governments judging different things — the record's own constitution
over its verbs, the machine's mode over the environment's operations — and wrote a
`GovernancePort` subclass to route between them. This is that, shipped: `Routed` hands each
judgement to the port named for the component in the context (`attributes["component"]`, which
the runtime puts there for exactly this), and everything else — the turn's own step, a
component nobody named — to `otherwise`. Total, like every governance port: a port that raises
is a port failure (D7), never a silent allow.
"""

from __future__ import annotations

from collections.abc import Mapping

from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import Context, GovernancePort, Judgement


class Routed(GovernancePort):
    def __init__(
        self, by_component: Mapping[str, GovernancePort], *, otherwise: GovernancePort
    ) -> None:
        self._by_component = dict(by_component)
        self._otherwise = otherwise

    async def judge(self, effects: EffectProfile, context: Context) -> Judgement:
        component = context.attributes.get("component")
        port = self._by_component.get(component) if isinstance(component, str) else None
        return await (port or self._otherwise).judge(effects, context)


__all__ = ["Routed"]
