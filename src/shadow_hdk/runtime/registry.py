"""What exists, right now — the union of every component port.

The registry is **live** (`09` §4): it is refreshed every step, so an MCP server connected
mid-session is invocable on the next one. It answers *what exists*; whether the agent may see or
invoke any of it is governance's answer, and lives in `StepExecutor`.

A port whose catalogue call fails contributes nothing this step rather than ending the run. That is
the registry shrinking, which the design says must be as ordinary as it growing — one unreachable
MCP server is not a reason to lose a turn's work.

With a `Trust`, the registry is also where a driver proves itself (D27). A registration that cannot
— unsigned where a signature is required, signed by a key unknown or revoked, or not verifying over
what it declares — is **refused**: absent from the catalogue, so the model never sees it, with the
reason kept in `refused`. Checked here, at the one funnel, on every refresh.

An id offered by two ports resolves to the **first** (BUG-037): a registration the run started with
cannot be taken over by a port that came later — a battery wanted second, a server connected
mid-session — which is the safer direction for a catalogue that is live. The hidden offer is named
in `shadowed`, the way a port that would not answer is named in `unreachable`: tolerated, and seen.
"""

from __future__ import annotations

from collections.abc import Sequence

from shadow_hdk.kernel.components import Registration, RegistrationId
from shadow_hdk.kernel.ports import ComponentPort
from shadow_hdk.runtime.trust import Trust


class Registry:
    def __init__(self, ports: Sequence[ComponentPort], *, trust: Trust | None = None) -> None:
        self._ports = tuple(ports)
        self._by_id: dict[RegistrationId, tuple[ComponentPort, Registration]] = {}
        self.trust = trust
        self.unreachable: list[str] = []
        self.refused: list[str] = []
        self.shadowed: list[str] = []

    async def refresh(self) -> None:
        found: dict[RegistrationId, tuple[ComponentPort, Registration]] = {}
        unreachable: list[str] = []
        refused: list[str] = []
        shadowed: list[str] = []
        for port in self._ports:
            try:
                registrations = await port.registrations()
            except Exception as exc:  # noqa: BLE001 — a catalogue that will not answer is empty
                unreachable.append(f"{type(port).__name__}: {type(exc).__name__}: {exc}")
                continue
            for registration in registrations:
                reason = self.trust.refusal(registration) if self.trust is not None else None
                if reason is not None:
                    refused.append(reason)
                    continue
                if registration.id in found:
                    first, _ = found[registration.id]
                    shadowed.append(
                        f"{registration.id}: offered by {type(port).__name__} is hidden behind "
                        f"{type(first).__name__}, which offered it first"
                    )
                    continue
                found[registration.id] = (port, registration)
        self._by_id = found
        self.unreachable = unreachable
        self.refused = refused
        self.shadowed = shadowed

    def resolve(self, registration_id: RegistrationId) -> tuple[ComponentPort, Registration]:
        """Raises `KeyError` for anything not registered — the caller turns that into `Failed`."""
        return self._by_id[registration_id]

    def all(self) -> list[Registration]:
        return [registration for _, registration in self._by_id.values()]
