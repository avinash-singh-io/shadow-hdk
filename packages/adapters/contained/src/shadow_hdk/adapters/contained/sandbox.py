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

import socket
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
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
class Denied:
    """One thing a contained program must not be able to do, attempted and refused.

    `what` is the capability in words; `evidence` is what came back. Both are on the record,
    because a proof nobody can re-read is a flag with a longer name.
    """

    what: str
    evidence: str


@dataclass(frozen=True)
class Proof:
    """Why this sandbox is believed to contain anything (D36).

    `checks` is the evidence: capabilities attempted **inside** the box by the sandbox itself and
    denied. `declared` is what the backend *says* about itself — a **claim**, kept because it is
    useful in a record, and never treated as evidence. Before D36 the claim was the whole proof:
    `probe()` ran `dmesg` inside the sandbox and matched the string `gVisor`, so a five-line shell
    script produced a proof, and `ContainedSandbox` refuses to exist without one.
    """

    backend: str
    checks: tuple[Denied, ...]
    declared: str | None
    at: str

    def __str__(self) -> str:
        if not self.checks:
            claim = f" — it says: {self.declared}" if self.declared else ""
            return f"{self.backend} is TRUSTED, not proven: nothing was denied under test{claim}"
        denials = "; ".join(f"{check.what} ({check.evidence})" for check in self.checks)
        return f"{self.backend} proved containment by denying: {denials}"


class NotContained(RuntimeError):
    """The sandbox asked for could not prove it is one. Raised at construction, on purpose."""


@runtime_checkable
class IsolationBackend(Protocol):
    """One way of putting a program in a box.

    A backend no longer judges itself (D36). It says what it is, whether it is here, and how to run
    argv inside it; **the sandbox** runs the capability test through `wrap` and decides. A backend
    could still lie about that one operation — it owns the box — but the bar is now *deny the
    thing* rather than *print the right word*, and nothing local can do better than that.
    """

    @property
    def name(self) -> str: ...

    @property
    def binary(self) -> str:
        """What has to be on the machine. Named so an absence can be reported as one."""
        ...

    def present(self) -> bool: ...

    def declares(self) -> str | None:
        """What the backend says about itself, if anything. A claim for the record, never
        evidence: this is the field the old `probe()` mistook for a proof."""
        ...

    def wrap(self, argv: list[str]) -> list[str]:
        """The argv that runs `argv` inside the backend rather than on the host."""
        ...


REACHES_A_LISTENER = "reach a listening socket on the host"

PROBE_TIMEOUT_S = 20.0

_PROBE = (
    "import socket, sys\n"
    "s = socket.socket(); s.settimeout(3)\n"
    "reached = s.connect_ex(('127.0.0.1', {port})) == 0\n"
    "print('REACHED' if reached else 'DENIED')\n"
)


def _probe_argv(port: int) -> list[str]:
    return [sys.executable, "-c", _PROBE.format(port=port)]


class Inconclusive(RuntimeError):
    """The capability test could not be run, which is not the capability being denied.

    The trap this exists to avoid: a probe that fails to *start* also fails to connect, so a check
    that looked only for the absence of success would certify every backend that can run nothing.
    """


def prove(backend: IsolationBackend) -> Denied:
    """Attempt, inside the box, something a contained program must not manage (D36).

    A listener is opened on loopback — a real one, so reaching it is genuinely possible — and the
    sandbox is asked to connect to it. Reaching it means the box is not a box. Failing to reach it
    **while saying so** is the proof. Saying nothing is inconclusive, and inconclusive is not a
    denial.

    The check belongs here rather than to the backend, so no backend decides that it passed. One
    could still lie about this single operation — it owns the box — but the bar is now *deny the
    thing* instead of *print the right word*, and nothing local does better than that.
    """
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = int(listener.getsockname()[1])
    try:
        try:
            seen = subprocess.run(  # noqa: S603 — the argv is ours, not a model's
                backend.wrap(_probe_argv(port)),
                capture_output=True,
                text=True,
                timeout=PROBE_TIMEOUT_S,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as broken:
            raise Inconclusive(
                f"{backend.name!r} could not run the capability test at all ({broken}); "
                "a check that cannot run proves nothing"
            ) from broken
    finally:
        listener.close()
    said = seen.stdout or ""
    if "REACHED" in said:
        raise NotContained(
            f"{backend.name!r} did not contain the probe: inside it, a program could "
            f"{REACHES_A_LISTENER}, so whatever it is, it is not a box"
        )
    if "DENIED" not in said:
        raise Inconclusive(
            f"{backend.name!r} left the capability test inconclusive — the probe neither reached "
            f"the listener nor reported being denied (exit {seen.returncode}); a check that "
            "cannot run proves nothing"
        )
    evidence = f"the probe reported DENIED (exit {seen.returncode})"
    return Denied(what=REACHES_A_LISTENER, evidence=evidence)


def _proven(backend: IsolationBackend, *, trusting: bool) -> Proof:
    declared = backend.declares()
    try:
        denied = prove(backend)
    except Inconclusive:
        if not trusting:
            raise
        return Proof(backend=backend.name, checks=(), declared=declared, at=_now())
    return Proof(backend=backend.name, checks=(denied,), declared=declared, at=_now())


def _now() -> str:
    return datetime.now(UTC).isoformat()


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
        trusting_the_backend_without_proof: bool = False,
    ) -> None:
        """`trusting_the_backend_without_proof` is the sentence an operator signs when the
        capability test cannot run here. It is not a silent pass and it is not a default (D36)."""
        if not backend.present():
            raise NotContained(
                f"{backend.name!r} cannot contain anything here: {backend.binary!r} is not present"
            )
        self._backend = backend
        self._root = Path(root).resolve()
        try:
            self.proof: Proof = _proven(backend, trusting=trusting_the_backend_without_proof)
        except Inconclusive as unproven:
            raise NotContained(str(unproven)) from unproven
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


__all__ = [
    "ContainedSandbox",
    "Denied",
    "Inconclusive",
    "IsolationBackend",
    "NotContained",
    "Proof",
    "prove",
]
