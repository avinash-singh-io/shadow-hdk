"""The first devices (D8, D31): fakes that can be told to misbehave the way real ones do."""

from __future__ import annotations

from pydantic import JsonValue

from shadow_hdk.adapters.devices.contract import Ack, Overheard, Reading


class FakeSensor:
    def __init__(self, id: str, *, value: JsonValue, unit: str | None, at: str) -> None:
        self.id, self.value, self.unit, self.at = id, value, unit, at

    async def read(self) -> Reading:
        return Reading(value=self.value, unit=self.unit, at=self.at)


class FakeActuator:
    """Records every command it was given, with the key that came with it. `disconnect_after(n)`
    makes the link drop **after** the n-th further command went out — the world may have moved,
    and the ack never arrives."""

    def __init__(self, id: str) -> None:
        self.id = id
        self.commands: list[tuple[str, JsonValue]] = []
        self._drop_at: int | None = None

    def disconnect_after(self, n: int) -> FakeActuator:
        self._drop_at = len(self.commands) + n
        return self

    async def command(self, argv: JsonValue, *, key: str) -> Ack:
        self.commands.append((key, argv))
        if self._drop_at is not None and len(self.commands) > self._drop_at:
            raise ConnectionError(f"the link to {self.id} dropped before the ack")
        return Ack(foreign_id=f"{self.id}#{len(self.commands)}", exit="acknowledged")


class FakeWitness:
    def __init__(self, id: str, overheard: list[Overheard]) -> None:
        self.id = id
        self._pending = list(overheard)

    async def overheard(self) -> Overheard | None:
        return self._pending.pop(0) if self._pending else None


__all__ = ["FakeActuator", "FakeSensor", "FakeWitness"]
