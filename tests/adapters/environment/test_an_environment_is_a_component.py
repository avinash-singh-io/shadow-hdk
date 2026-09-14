"""An environment is a component port, held to the contract every component port is held to.

`full` mode, because that constructs on any machine — the contract is about the port's shape, not
about confinement, which `test_local_is_confined_for_real.py` proves separately.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import JsonValue

from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.kernel.ports import ComponentPort
from shadow_hdk.testing.contracts import ComponentPortContract


class TestALocalEnvironmentIsAComponentPort(ComponentPortContract):
    @asynccontextmanager
    async def using(self) -> AsyncIterator[ComponentPort]:
        with TemporaryDirectory() as tmp:
            yield await LocalEnvironment.open(Path(tmp), mode="full")

    def valid_call(self) -> tuple[str, JsonValue]:
        return "run_python", {"source": "print('hello')"}
