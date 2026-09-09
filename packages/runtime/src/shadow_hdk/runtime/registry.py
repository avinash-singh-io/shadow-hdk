"""What the agent can see, recomputed rather than listed.

The registry is the union of every component port. `visible` filters it through the governance port,
so a component the policy would refuse for every input is **absent** rather than greyed out (`09`
§4) — a narrowed agent never sees a thing it may not touch, and a narrowed catalogue is also fewer
tokens per turn (D11, D13).
"""

from __future__ import annotations

from shadow_hdk.kernel.components import Registration, RegistrationId
from shadow_hdk.kernel.ports import ComponentPort, Context, GovernancePort, Refuse


class Registry:
    def __init__(self, ports: tuple[ComponentPort, ...]) -> None:
        self._ports = ports
        self._by_id: dict[RegistrationId, tuple[ComponentPort, Registration]] = {}

    async def refresh(self) -> None:
        """Re-read every port: connect an MCP server mid-session and its tools are here
        on the next step. An adapter over something remote caches and decides when to re-read."""
        found: dict[RegistrationId, tuple[ComponentPort, Registration]] = {}
        for port in self._ports:
            for registration in await port.registrations():
                found[registration.id] = (port, registration)
        self._by_id = found

    def resolve(self, registration: RegistrationId) -> tuple[ComponentPort, Registration]:
        return self._by_id[registration]

    def all(self) -> list[Registration]:
        return [registration for _, registration in self._by_id.values()]

    async def visible(self, governance: GovernancePort, context: Context) -> list[Registration]:
        shown = []
        for _, registration in self._by_id.values():
            judgement = await governance.judge(registration.component.effects, context)
            if not isinstance(judgement, Refuse):
                shown.append(registration)
        return shown
