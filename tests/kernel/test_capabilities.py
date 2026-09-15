"""A host asks for properties; providers and environments report evidence-backed facts (D96)."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from shadow_hdk.kernel import (
    CapabilityEvidence,
    EnvironmentCapabilities,
    EnvironmentRequirements,
    ExecutionRequirements,
    ProviderCapabilities,
    ProviderRequirements,
    check_compatibility,
)
from shadow_hdk.kernel.contracts import round_trip


def measured(axis: str) -> CapabilityEvidence:
    return CapabilityEvidence(axis, "measured", "test probe", "2026-09-15")


def test_unknown_is_an_answer_and_never_satisfies_a_strict_requirement() -> None:
    result = check_compatibility(
        ProviderCapabilities(),
        EnvironmentCapabilities(),
        ExecutionRequirements(
            provider=ProviderRequirements(tool_path="controlled", session="resumable"),
            environment=EnvironmentRequirements(
                reads_within="workspace", network="denied", secrets="denied", proven=True
            ),
        ),
    )

    assert not result.ok
    assert [(m.subject, m.axis) for m in result.mismatches] == [
        ("provider", "tool_path"),
        ("provider", "session"),
        ("environment", "reads"),
        ("environment", "network"),
        ("environment", "secrets"),
        ("environment", "proof"),
    ]
    assert all(m.available == "unknown" for m in result.mismatches[:-1])


def test_a_stronger_capability_satisfies_a_weaker_requirement() -> None:
    result = check_compatibility(
        ProviderCapabilities(
            tool_path="controlled",
            session="resumable",
            interrupt="native",
            streaming="live",
            reasoning="yes",
            usage_tokens="yes",
            usage_cost="yes",
            evidence=tuple(
                measured(axis)
                for axis in (
                    "tool_path",
                    "session",
                    "interrupt",
                    "streaming",
                    "reasoning",
                    "usage_tokens",
                    "usage_cost",
                )
            ),
        ),
        EnvironmentCapabilities(
            reads="workspace",
            writes="workspace",
            network="denied",
            secrets="denied",
            proven=True,
            evidence=tuple(
                measured(axis) for axis in ("reads", "writes", "network", "secrets", "proof")
            ),
        ),
        ExecutionRequirements(
            provider=ProviderRequirements(
                tool_path="observed",
                session="process",
                interrupt="terminate",
                streaming="final",
                reasoning=True,
                usage_tokens=True,
            ),
            environment=EnvironmentRequirements(
                reads_within="workspace",
                writes_within="workspace",
                network="denied",
                secrets="denied",
                proven=True,
            ),
        ),
    )

    assert result.ok
    assert result.mismatches == ()


def test_a_mismatch_carries_the_fact_and_its_evidence() -> None:
    result = check_compatibility(
        ProviderCapabilities(
            tool_path="uncontrolled",
            evidence=(CapabilityEvidence("tool_path", "measured", "native tools remained"),),
        ),
        EnvironmentCapabilities(),
        ExecutionRequirements(provider=ProviderRequirements(tool_path="controlled")),
    )

    assert len(result.mismatches) == 1
    mismatch = result.mismatches[0]
    assert (mismatch.subject, mismatch.axis) == ("provider", "tool_path")
    assert (mismatch.required, mismatch.available) == ("controlled", "uncontrolled")
    assert mismatch.evidence.kind == "measured"
    assert mismatch.evidence.source == "native tools remained"


def test_no_requirements_is_explicit_backward_compatibility() -> None:
    assert check_compatibility(
        ProviderCapabilities(), EnvironmentCapabilities(), ExecutionRequirements()
    ).ok


def test_closed_axes_cannot_carry_an_invented_or_contradictory_value() -> None:
    adapter = TypeAdapter(ProviderCapabilities)

    with pytest.raises(ValidationError):
        adapter.validate_python({"tool_path": "controlled-and-uncontrolled"})


def test_the_new_contracts_round_trip_through_json() -> None:
    requirements = ExecutionRequirements(
        provider=ProviderRequirements(tool_path="controlled", session="resumable"),
        environment=EnvironmentRequirements(reads_within="workspace", network="denied"),
    )
    compatibility = check_compatibility(
        ProviderCapabilities(tool_path="observed", session="process"),
        EnvironmentCapabilities(reads="machine", network="available"),
        requirements,
    )

    assert round_trip(requirements, ExecutionRequirements) == requirements
    assert round_trip(compatibility, type(compatibility)) == compatibility
