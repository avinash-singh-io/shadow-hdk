"""Evidence-backed execution capabilities and the requirements a host places on them (D96).

Capabilities describe facts. Requirements describe what a host is willing to run. Keeping the two
types separate prevents an omitted fact from becoming permission and makes compatibility a pure,
total decision that crosses any wire.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

EvidenceKind = Literal["measured", "derived", "declared", "unknown"]
ToolPath = Literal["controlled", "observed", "uncontrolled", "unavailable", "unknown"]
SessionContinuity = Literal["resumable", "process", "none", "unknown"]
Interruptibility = Literal["native", "terminate", "none", "unknown"]
Streaming = Literal["live", "final", "none", "unknown"]
Support = Literal["yes", "no", "unknown"]
AccessBoundary = Literal["none", "workspace", "machine", "unknown"]
NetworkPosture = Literal["denied", "available", "unknown"]
SecretPosture = Literal["denied", "ambient", "unknown"]


@dataclass(frozen=True)
class CapabilityEvidence:
    """Why one capability value may be believed, without carrying a secret or probe output."""

    axis: str
    kind: EvidenceKind = "unknown"
    source: str = ""
    at: str = ""

    def __post_init__(self) -> None:
        if not self.axis:
            raise ValueError("capability evidence needs an axis")
        if self.kind != "unknown" and not self.source:
            raise ValueError(f"{self.axis}: {self.kind} evidence needs a source")


_PROVIDER_AXES = frozenset(
    {"tool_path", "session", "interrupt", "streaming", "reasoning", "usage_tokens", "usage_cost"}
)
_ENVIRONMENT_AXES = frozenset({"reads", "writes", "network", "secrets", "proof"})


def _validate_evidence(
    evidence: tuple[CapabilityEvidence, ...], allowed: frozenset[str], subject: str
) -> None:
    axes = [item.axis for item in evidence]
    if repeated := sorted({axis for axis in axes if axes.count(axis) > 1}):
        raise ValueError(f"{subject} capability evidence repeats {', '.join(repeated)}")
    if unknown := sorted(set(axes) - allowed):
        raise ValueError(f"{subject} capability evidence names unknown axis {', '.join(unknown)}")


@dataclass(frozen=True)
class ProviderCapabilities:
    """What a provider can honestly offer to a host. Every omitted axis is unknown."""

    tool_path: ToolPath = "unknown"
    session: SessionContinuity = "unknown"
    interrupt: Interruptibility = "unknown"
    streaming: Streaming = "unknown"
    reasoning: Support = "unknown"
    usage_tokens: Support = "unknown"
    usage_cost: Support = "unknown"
    evidence: tuple[CapabilityEvidence, ...] = ()

    def __post_init__(self) -> None:
        _validate_evidence(self.evidence, _PROVIDER_AXES, "provider")


@dataclass(frozen=True)
class EnvironmentCapabilities:
    """The effective environment boundary for one mode, established by proof or an honest no."""

    reads: AccessBoundary = "unknown"
    writes: AccessBoundary = "unknown"
    network: NetworkPosture = "unknown"
    secrets: SecretPosture = "unknown"
    proven: bool = False
    evidence: tuple[CapabilityEvidence, ...] = ()

    def __post_init__(self) -> None:
        _validate_evidence(self.evidence, _ENVIRONMENT_AXES, "environment")


@dataclass(frozen=True)
class ProviderRequirements:
    """Minimum provider properties a host requires. `None`/`False` means no requirement."""

    tool_path: Literal["controlled", "observed"] | None = None
    session: Literal["resumable", "process"] | None = None
    interrupt: Literal["native", "terminate"] | None = None
    streaming: Literal["live", "final"] | None = None
    reasoning: bool = False
    usage_tokens: bool = False
    usage_cost: bool = False


@dataclass(frozen=True)
class EnvironmentRequirements:
    """Maximum reach a host accepts from the effective environment."""

    reads_within: Literal["none", "workspace", "machine"] | None = None
    writes_within: Literal["none", "workspace", "machine"] | None = None
    network: Literal["denied"] | None = None
    secrets: Literal["denied"] | None = None
    proven: bool = False


@dataclass(frozen=True)
class ExecutionRequirements:
    provider: ProviderRequirements = field(default_factory=ProviderRequirements)
    environment: EnvironmentRequirements = field(default_factory=EnvironmentRequirements)


@dataclass(frozen=True)
class CapabilityMismatch:
    subject: Literal["provider", "environment"]
    axis: str
    required: str
    available: str
    evidence: CapabilityEvidence


@dataclass(frozen=True)
class Compatibility:
    mismatches: tuple[CapabilityMismatch, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.mismatches


@dataclass(frozen=True)
class ExecutionSelection:
    """The provider/environment facts accepted at one construction boundary."""

    provider: ProviderCapabilities
    environment: EnvironmentCapabilities
    compatibility: Compatibility


class IncompatibleCapabilities(RuntimeError):
    """Construction refused with the complete typed result and the facts it compared."""

    def __init__(
        self,
        compatibility: Compatibility,
        *,
        available_provider: ProviderCapabilities | None = None,
        available_environment: EnvironmentCapabilities | None = None,
    ) -> None:
        self.compatibility = compatibility
        self.available_provider = available_provider
        self.available_environment = available_environment
        detail = ", ".join(
            f"{gap.subject}.{gap.axis} needs {gap.required}, has {gap.available}"
            for gap in compatibility.mismatches
        )
        super().__init__(f"execution capabilities are incompatible: {detail}")


def select_execution(
    provider: ProviderCapabilities,
    environment: EnvironmentCapabilities,
    requirements: ExecutionRequirements,
) -> ExecutionSelection:
    """Return the accepted pair or refuse with the same complete result every surface carries."""
    compatibility = check_compatibility(provider, environment, requirements)
    if not compatibility.ok:
        raise IncompatibleCapabilities(
            compatibility,
            available_provider=provider,
            available_environment=environment,
        )
    return ExecutionSelection(provider, environment, compatibility)


def _evidence_for(
    evidence: tuple[CapabilityEvidence, ...], axis: str
) -> CapabilityEvidence:
    return next((item for item in evidence if item.axis == axis), CapabilityEvidence(axis))


def _meets(available: str, required: str, ranks: dict[str, int]) -> bool:
    return available != "unknown" and ranks[available] >= ranks[required]


def check_compatibility(
    provider: ProviderCapabilities,
    environment: EnvironmentCapabilities,
    requirements: ExecutionRequirements,
) -> Compatibility:
    """Return every mismatch in stable provider-then-environment axis order."""

    mismatches: list[CapabilityMismatch] = []

    def need_provider(
        axis: str,
        required: str | None,
        available: str,
        ranks: dict[str, int],
    ) -> None:
        if required is not None and not _meets(available, required, ranks):
            mismatches.append(
                CapabilityMismatch(
                    "provider", axis, required, available, _evidence_for(provider.evidence, axis)
                )
            )

    wanted = requirements.provider
    need_provider(
        "tool_path",
        wanted.tool_path,
        provider.tool_path,
        {"unknown": -1, "unavailable": 0, "uncontrolled": 1, "observed": 2, "controlled": 3},
    )
    need_provider(
        "session",
        wanted.session,
        provider.session,
        {"unknown": -1, "none": 0, "process": 1, "resumable": 2},
    )
    need_provider(
        "interrupt",
        wanted.interrupt,
        provider.interrupt,
        {"unknown": -1, "none": 0, "terminate": 1, "native": 2},
    )
    need_provider(
        "streaming",
        wanted.streaming,
        provider.streaming,
        {"unknown": -1, "none": 0, "final": 1, "live": 2},
    )
    for axis, requires_support, available_support in (
        ("reasoning", wanted.reasoning, provider.reasoning),
        ("usage_tokens", wanted.usage_tokens, provider.usage_tokens),
        ("usage_cost", wanted.usage_cost, provider.usage_cost),
    ):
        if requires_support and available_support != "yes":
            mismatches.append(
                CapabilityMismatch(
                    "provider",
                    axis,
                    "yes",
                    available_support,
                    _evidence_for(provider.evidence, axis),
                )
            )

    environment_wanted = requirements.environment
    boundary_rank = {"none": 0, "workspace": 1, "machine": 2}
    for axis, required_boundary, available_boundary in (
        ("reads", environment_wanted.reads_within, environment.reads),
        ("writes", environment_wanted.writes_within, environment.writes),
    ):
        if required_boundary is not None and (
            available_boundary == "unknown"
            or boundary_rank[available_boundary] > boundary_rank[required_boundary]
        ):
            mismatches.append(
                CapabilityMismatch(
                    "environment",
                    axis,
                    required_boundary,
                    available_boundary,
                    _evidence_for(environment.evidence, axis),
                )
            )
    for axis, required_posture, available_posture in (
        ("network", environment_wanted.network, environment.network),
        ("secrets", environment_wanted.secrets, environment.secrets),
    ):
        if required_posture is not None and available_posture != required_posture:
            mismatches.append(
                CapabilityMismatch(
                    "environment",
                    axis,
                    required_posture,
                    available_posture,
                    _evidence_for(environment.evidence, axis),
                )
            )
    if environment_wanted.proven and not environment.proven:
        mismatches.append(
            CapabilityMismatch(
                "environment",
                "proof",
                "proven",
                "not-proven" if environment.evidence else "unknown",
                _evidence_for(environment.evidence, "proof"),
            )
        )
    return Compatibility(tuple(mismatches))


__all__ = [
    "AccessBoundary",
    "CapabilityEvidence",
    "CapabilityMismatch",
    "Compatibility",
    "EnvironmentCapabilities",
    "EnvironmentRequirements",
    "EvidenceKind",
    "ExecutionRequirements",
    "Interruptibility",
    "NetworkPosture",
    "ProviderCapabilities",
    "ProviderRequirements",
    "SecretPosture",
    "SessionContinuity",
    "Streaming",
    "Support",
    "ToolPath",
    "check_compatibility",
]
