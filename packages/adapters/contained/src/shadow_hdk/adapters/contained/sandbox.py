"""A sandbox that proves it is contained, or refuses to exist (D25).

Phase 3 made `contained` a deployment fact with no default and said why: *a sandbox that claimed
containment it did not have would be the most dangerous lie in this system.* It then took the
deployment's word, because it had nothing else. This is the version that checks.

**A backend proves itself.** Each knows one thing that is true inside it and false on the host —
gVisor's kernel announces itself, a Firecracker guest's hardware does — and this sandbox runs that
probe *through the backend* before it registers anything. So `contained: true` in the catalogue is
an observation, and the proof rides on the component's provenance so a record can say why.

**A proof that fails refuses construction.** Not a warning and not a fallback to Phase 3's leash. A
warning is a log line; a false `contained` is a governance input that decides what a model is shown
(Phase 3: a mode requiring containment hides what cannot provide it). Those are not the same
severity, and the person who asked for containment has to be told.

**Proven once, at construction.** A probe per call would launch a sandbox to re-learn a fact about
the machine, and a machine that loses its sandbox between two steps has bigger problems than this.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import JsonValue

from shadow_hdk.kernel.components import (
    Component,
    Interface,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.effects import EffectProfile, ScopeSet
from shadow_hdk.kernel.observations import Failed, Observation
from shadow_hdk.kernel.ports import ComponentPort
from shadow_hdk.runtime.leash import run_leashed


@dataclass(frozen=True)
class Proof:
    """What a backend showed, when. A proof with no observation is a flag with a longer name."""

    backend: str
    observed: str
    at: str

    def __str__(self) -> str:
        return f"{self.backend} proved containment: {self.observed}"


class NotContained(RuntimeError):
    """The sandbox asked for could not prove it is one. Raised at construction, on purpose."""


@runtime_checkable
class IsolationBackend(Protocol):
    """One way of putting a program in a box, and one way of showing the box is there."""

    @property
    def name(self) -> str: ...

    @property
    def binary(self) -> str:
        """What has to be on the machine. Named so an absence can be reported as one."""
        ...

    def present(self) -> bool: ...

    def probe(self) -> Proof | None:
        """Run something inside the backend that answers differently than the host would.
        `None` means it could not be shown — the sandbox treats that as absent, not as unknown."""
        ...

    def wrap(self, argv: list[str]) -> list[str]:
        """The argv that runs `argv` inside the backend rather than on the host."""
        ...


class ContainedSandbox(ComponentPort):
    """Phase 3's leash, inside a box that has shown it is there.

    Beside `SubprocessSandbox`, not on top of it: the invariant that no adapter imports another is
    what lets a host install any subset, so the leash the two share lives in the runtime and each
    wraps it its own way. What this one adds is that every argv goes through the backend, and that
    `contained` is a proof rather than an argument.
    """

    def __init__(
        self,
        root: Path,
        *,
        backend: IsolationBackend,
        timeout_s: float = 30.0,
        output_limit: int = 64_000,
        at: str = "",
        source: str = "sandbox",
    ) -> None:
        if not backend.present():
            raise NotContained(
                f"{backend.name!r} cannot contain anything here: {backend.binary!r} is not present"
            )
        proof = backend.probe()
        if proof is None:
            raise NotContained(
                f"{backend.name!r} is present but could not prove it contains anything; "
                "refusing rather than running on the host"
            )
        self._backend = backend
        self.proof: Proof = proof
        self._root = Path(root).resolve()
        self._timeout_s = timeout_s
        self._output_limit = output_limit
        self._at = at
        self._source = source
        # Contained and offline. A backend that routes network is a different component with a
        # different profile, declared as such — not this one with a flag flipped.
        self._effects = EffectProfile(
            reads=ScopeSet.of("workspace"),
            writes=ScopeSet.of("workspace"),
            reaches=False,
            reversible=False,
            contained=True,
            costs=False,
        )

    async def registrations(self) -> Sequence[Registration]:
        return [
            self._registration(
                "run_python",
                "Run a Python script in the workspace, inside the sandbox; return what it printed.",
                {"source": {"type": "string", "description": "The script to run."}},
                ["source"],
            ),
            self._registration(
                "run_shell",
                "Run a shell command in the workspace, inside the sandbox; return what it printed.",
                {"command": {"type": "string", "description": "The command to run."}},
                ["command"],
            ),
        ]

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        arguments = inputs if isinstance(inputs, dict) else {}
        match registration:
            case "run_python":
                source = arguments.get("source")
                if not isinstance(source, str):
                    return Failed("run_python needs `source`, a string")
                argv = [sys.executable, "-c", source]
            case "run_shell":
                command = arguments.get("command")
                if not isinstance(command, str):
                    return Failed("run_shell needs `command`, a string")
                argv = ["/bin/sh", "-c", command]
            case _:
                return Failed(f"no component registered as {registration!r}")
        # Through the backend, never around it. The proof would mean nothing if the real work then
        # ran on the host.
        return await run_leashed(
            self._backend.wrap(argv),
            cwd=self._root,
            timeout_s=self._timeout_s,
            output_limit=self._output_limit,
        )

    def _registration(
        self, name: str, description: str, properties: dict[str, JsonValue], required: list[str]
    ) -> Registration:
        return Registration(
            id=name,
            component=Component(
                interface=Interface(
                    name=name,
                    description=description,
                    input_schema={
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                    output_schema={"type": "object"},
                ),
                effects=self._effects,
                provenance=Provenance(
                    registered_by=self._source,
                    # The proof rides here, so a record can say *why* the profile said contained.
                    adapter=f"sandbox-contained+proof:{self.proof.backend}",
                    at=self._at,
                ),
                labels=frozenset({"program"}),
            ),
        )


__all__ = ["ContainedSandbox", "IsolationBackend", "NotContained", "Proof"]
