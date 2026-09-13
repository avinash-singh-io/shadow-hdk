"""The agent adapter, held to the component contract (TD-004).

An agent *is* a component — that is the whole trick D3 turns, and the reason a sub-agent needs no
machinery a tool does not. So it answers the same four questions every other component does: its
registrations are well formed, they round-trip as JSON, an unknown id is an observation rather than
an exception, and what it returns round-trips too.
"""

from __future__ import annotations

from pydantic import JsonValue

from shadow_hdk.adapters.agent import AgentComponent, Pattern
from shadow_hdk.kernel.components import RegistrationId
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.ports import ComponentPort
from tests.adapters.contract import ComponentPortContract


class TestAgentComponentIsAComponentPort(ComponentPortContract):
    def port(self) -> ComponentPort:
        return AgentComponent(
            pattern=Pattern(name="p", system="work"),
            effects=EffectProfile(costs=True),
            at="2026-01-01T00:00:00+00:00",
        )

    def valid_call(self) -> tuple[RegistrationId, JsonValue]:
        # No run context and no model: the contract asks what a call *returns*, and an agent
        # invoked outside a run must answer rather than raise, like any other component.
        return "agent", {"brief": "say hello"}
