"""The contained sandbox, held to the component contract (TD-004).

`FakeIsolation(contains=True)` is a backend that really denies the capability the proof tests, so
the sandbox is constructible without gVisor or Firecracker on the machine — which is what makes
this contract runnable at all here, and why the live backends stay `[~]`.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from pydantic import JsonValue

from shadow_hdk.adapters.contained import ContainedSandbox, FakeIsolation
from shadow_hdk.kernel.components import RegistrationId
from shadow_hdk.kernel.ports import ComponentPort
from tests.adapters.contract import ComponentPortContract


class TestContainedSandboxIsAComponentPort(ComponentPortContract):
    def port(self) -> ComponentPort:
        # A directory of its own per construction; the sandbox writes nothing here beyond what the
        # contract's own call asks for, and the suite never runs a program.
        root = Path(tempfile.mkdtemp(prefix="contained-contract-"))
        return ContainedSandbox(
            root, backend=FakeIsolation(contains=True), at="2026-01-01T00:00:00+00:00"
        )

    def valid_call(self) -> tuple[RegistrationId, JsonValue]:
        return "run_code", {"argv": ["true"]}
