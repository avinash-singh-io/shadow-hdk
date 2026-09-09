"""What exists, right now — the union of every component port.

The registry is **live** (`09` §4): it is refreshed every step, so an MCP server connected
mid-session is invocable on the next one. It answers *what exists*; whether the agent may see or
invoke any of it is governance's answer, and lives in `StepExecutor`.

A port whose catalogue call fails contributes nothing this step rather than ending the run. That is
the registry shrinking, which the design says must be as ordinary as it growing — one unreachable
MCP server is not a reason to lose a turn's work.
"""

from __future__ import annotations

from collections.abc import Sequence

from shadow_hdk.kernel.components import Registration, RegistrationId
from shadow_hdk.kernel.ports import ComponentPort


class Registry:
    def __init__(self, ports: Sequence[ComponentPort]) -> None:
        self._ports = tuple(ports)
        self._by_id: dict[RegistrationId, tuple[ComponentPort, Registration]] = {}
        self.unreachable: list[str] = []

    async def refresh(self) -> None:
        found: dict[RegistrationId, tuple[ComponentPort, Registration]] = {}
        unreachable: list[str] = []
        for port in self._ports:
            try:
                registrations = await port.registrations()
            except Exception as exc:  # noqa: BLE001 — a catalogue that will not answer is empty
                unreachable.append(f"{type(port).__name__}: {type(exc).__name__}: {exc}")
                continue
            for registration in registrations:
                found[registration.id] = (port, registration)
        self._by_id = found
        self.unreachable = unreachable

    def resolve(self, registration_id: RegistrationId) -> tuple[ComponentPort, Registration]:
        """Raises `KeyError` for anything not registered — the caller turns that into `Failed`."""
        return self._by_id[registration_id]

    def all(self) -> list[Registration]:
        return [registration for _, registration in self._by_id.values()]
