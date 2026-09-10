"""A sandbox that proves it is contained, or refuses to exist (D25).

Phase 3 said it: *a sandbox that claimed containment it did not have would be the most dangerous
lie in this system.* It then took the deployment's word, because it had nothing else. This is the
version that checks.

A backend proves itself with something that is true inside it and false on the host. The sandbox
runs that probe **through the backend** before it registers anything, so `contained: true` in the
catalogue is an observation rather than a claim. And when the proof fails, the sandbox does not fall
back to a leash and a warning — it refuses to be constructed, because the person who asked for
containment has to be told.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.adapters.contained import (
    ContainedSandbox,
    FakeIsolation,
    NotContained,
    Proof,
)


def test_a_backend_that_proves_itself_yields_a_contained_component(tmp_path: Path) -> None:
    sandbox = ContainedSandbox(tmp_path, backend=FakeIsolation(proves=True))
    assert sandbox.proof is not None
    assert sandbox.proof.backend == "fake"


async def test_the_profile_says_contained_only_because_it_was_proven(tmp_path: Path) -> None:
    sandbox = ContainedSandbox(tmp_path, backend=FakeIsolation(proves=True))
    for registration in await sandbox.registrations():
        assert registration.component.effects.contained is True
        # And the proof rides on provenance, so a record can say *why* the profile said so.
        assert "proof" in (registration.component.provenance.adapter or "")
        assert registration.component.effects.reaches is False, (
            "contained and offline should not reach — that is the whole point of a box"
        )


def test_a_backend_that_fails_its_proof_is_refused_naming_why(tmp_path: Path) -> None:
    """Not a warning, not a fallback. Refused at construction."""
    with pytest.raises(NotContained) as refused:
        ContainedSandbox(tmp_path, backend=FakeIsolation(proves=False))
    message = str(refused.value)
    assert "fake" in message, message
    assert "prove" in message.lower(), message


def test_an_absent_binary_is_refused_naming_the_binary(tmp_path: Path) -> None:
    with pytest.raises(NotContained) as refused:
        ContainedSandbox(tmp_path, backend=FakeIsolation(present=False))
    message = str(refused.value)
    assert "fake-runtime" in message, message
    assert "present" in message.lower() or "found" in message.lower(), message


async def test_a_run_goes_through_the_backend_not_around_it(tmp_path: Path) -> None:
    """The proof would mean nothing if the real work then ran on the host. Every argv must pass
    through `wrap`, and the fake backend records what it wrapped."""
    backend = FakeIsolation(proves=True)
    sandbox = ContainedSandbox(tmp_path, backend=backend)
    result = await sandbox.invoke("run_shell", {"command": "echo hello"})
    assert result.kind == "completed", result
    assert backend.wrapped, "the command never went through the backend"
    assert backend.wrapped[-1][-1] == "echo hello"


async def test_the_proof_is_taken_once_not_per_call(tmp_path: Path) -> None:
    """A probe per step would launch a sandbox to re-learn a fact about the machine."""
    backend = FakeIsolation(proves=True)
    sandbox = ContainedSandbox(tmp_path, backend=backend)
    await sandbox.invoke("run_shell", {"command": "true"})
    await sandbox.invoke("run_shell", {"command": "true"})
    assert backend.probes == 1


def test_a_proof_says_what_was_observed() -> None:
    """A proof with no observation is a flag with a longer name."""
    proof = Proof(backend="fake", observed="the fake kernel announced itself", at="t")
    assert proof.observed
    assert str(proof)


async def test_phase_3s_subprocess_sandbox_is_untouched(tmp_path: Path) -> None:
    """This phase adds a sibling. The leash from Phase 3 keeps its honest `contained=False`."""
    from shadow_hdk.adapters.sandbox_subprocess import SubprocessSandbox

    leash = SubprocessSandbox(tmp_path, contained=False)
    for registration in await leash.registrations():
        assert registration.component.effects.contained is False
