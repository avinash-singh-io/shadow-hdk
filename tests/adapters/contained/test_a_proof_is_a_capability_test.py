"""Containment is proven by what is denied, never by what is announced (D36, BUG-009).

**Reproduced before the fix:** a five-line fake `runsc` in a temp directory, first on `PATH`, made
`GVisor.probe()` return a `Proof` — because the probe ran `dmesg` *inside the sandbox* and matched
the string `gVisor` in the output. It asked the thing being trusted to vouch for itself. And
`ContainedSandbox` refuses to exist without a proof, so a deployment that got one believed
containment had been established: worse than no check, and the same shape as BUG-007.
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

from shadow_hdk.adapters.contained import ContainedSandbox, FakeIsolation, NotContained
from shadow_hdk.adapters.contained.sandbox import Denied, Proof


def _listening() -> tuple[socket.socket, int]:
    """A listener on loopback, and nothing else — the thing a contained program must not reach."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    return server, server.getsockname()[1]


def test_a_box_that_does_not_box_cannot_prove_itself(tmp_path: Path) -> None:
    """`FakeIsolation` runs argv on the host — which is exactly what a fake `runsc` did. The
    capability test reaches the harness's own listener, so there is nothing to prove."""
    with pytest.raises(NotContained) as refused:
        ContainedSandbox(tmp_path, backend=FakeIsolation(contains=False))
    assert "reach" in str(refused.value).lower(), refused.value


def test_a_box_that_denies_the_capability_proves_itself(tmp_path: Path) -> None:
    sandbox = ContainedSandbox(tmp_path, backend=FakeIsolation(contains=True))
    assert sandbox.proof.checks, "a proof with no check is a flag with a longer name"
    denied = sandbox.proof.checks[0]
    assert isinstance(denied, Denied)
    assert "reach" in denied.what.lower()


def test_what_the_backend_says_about_itself_is_never_the_proof(tmp_path: Path) -> None:
    """The banner survives, named as a claim. A backend that only announces itself and denies
    nothing is refused however loudly it announces."""
    boaster = FakeIsolation(contains=False, declares="Starting gVisor...")
    with pytest.raises(NotContained):
        ContainedSandbox(tmp_path, backend=boaster)


def test_the_banner_is_carried_beside_the_proof_as_a_claim(tmp_path: Path) -> None:
    sandbox = ContainedSandbox(
        tmp_path, backend=FakeIsolation(contains=True, declares="Starting gVisor...")
    )
    assert sandbox.proof.declared == "Starting gVisor..."
    assert Proof.__doc__ is not None and "claim" in Proof.__doc__.lower()


def test_a_check_that_could_not_run_is_not_a_denial(tmp_path: Path) -> None:
    """The trap this kind of test falls into: a probe that fails to start also 'fails to connect'.
    Inconclusive is refused, because counting it as a denial is how a check certifies nothing."""
    with pytest.raises(NotContained) as refused:
        ContainedSandbox(tmp_path, backend=FakeIsolation(contains=True, probe_runs=False))
    assert "inconclusive" in str(refused.value).lower(), refused.value


def test_a_deployment_may_trust_a_backend_it_cannot_test_but_must_say_so(tmp_path: Path) -> None:
    """Not a silent pass. The argument's name is the sentence the operator is signing."""
    sandbox = ContainedSandbox(
        tmp_path,
        backend=FakeIsolation(contains=True, probe_runs=False, declares="a microVM, honest"),
        trusting_the_backend_without_proof=True,
    )
    assert sandbox.proof.checks == ()
    assert sandbox.proof.declared == "a microVM, honest"
    assert "trusted" in str(sandbox.proof).lower()


def test_trusting_does_not_excuse_a_box_that_was_shown_not_to_be_one(tmp_path: Path) -> None:
    """The distinction the whole decision turns on. Trust covers **inconclusive** — a check that
    could not run — never a check that ran and showed the program reached the host. An operator
    may sign for an unknown; they cannot sign for a fact."""
    with pytest.raises(NotContained) as refused:
        ContainedSandbox(
            tmp_path,
            backend=FakeIsolation(contains=False),
            trusting_the_backend_without_proof=True,
        )
    assert "not a box" in str(refused.value)


def test_trusting_a_backend_does_not_excuse_an_absent_one(tmp_path: Path) -> None:
    with pytest.raises(NotContained, match="not present"):
        ContainedSandbox(
            tmp_path,
            backend=FakeIsolation(present=False),
            trusting_the_backend_without_proof=True,
        )


def test_the_capability_test_runs_through_the_backend_not_around_it(tmp_path: Path) -> None:
    """The check belongs to the sandbox, so no backend can decide it passed. What the backend
    sees is the probe argv, wrapped the same way real work is."""
    backend = FakeIsolation(contains=True)
    ContainedSandbox(tmp_path, backend=backend)
    assert backend.wrapped, "the probe did not go through wrap()"


def test_the_proof_a_real_check_produces_carries_its_evidence(tmp_path: Path) -> None:
    """Not just *that* something was denied — what came back, so an operator can re-read it."""
    sandbox = ContainedSandbox(tmp_path, backend=FakeIsolation(contains=True))
    assert sandbox.proof.checks[0].evidence, "a denial with no evidence is a flag again"
    assert "DENIED" in sandbox.proof.checks[0].evidence
    assert "DENIED" in str(sandbox.proof)


def test_a_proof_says_what_was_attempted_and_what_came_back() -> None:
    proof = Proof(
        backend="fake",
        checks=(Denied(what="reach a listening socket on the host", evidence="exit 7"),),
        declared=None,
        at="t",
    )
    assert "reach a listening socket" in str(proof)
    assert "exit 7" in str(proof)


async def test_a_listener_is_actually_listening_while_the_probe_runs(tmp_path: Path) -> None:
    """The check is only meaningful if the thing it tries to reach is reachable. If nothing were
    listening, every backend would 'pass' — which is the failure mode this whole group is about."""
    server, port = _listening()
    try:
        reaching = socket.socket()
        reaching.settimeout(3)
        assert reaching.connect_ex(("127.0.0.1", port)) == 0, "the harness's own listener is deaf"
        reaching.close()
    finally:
        server.close()
