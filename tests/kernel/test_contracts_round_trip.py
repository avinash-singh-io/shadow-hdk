"""Every port argument and return round-trips through JSON in CI (09 §3).

A callable therefore cannot cross a port even in-process; this is what converts "the ports stay
host-agnostic" from a review discipline into a build failure.
"""

from __future__ import annotations

import pytest

from shadow_hdk.kernel import (
    Allow,
    Ask,
    Binding,
    Ceiling,
    Compatibility,
    Completed,
    Component,
    Composed,
    Composition,
    Condition,
    Context,
    EffectProfile,
    Ended,
    EnvironmentCapabilities,
    ExecutionRequirements,
    ExecutionSelection,
    FanOut,
    Floor,
    Interface,
    Invoke,
    Invoked,
    Lease,
    ModelRequest,
    ModelResponse,
    Observed,
    Pending,
    Proposal,
    Proposed,
    Provenance,
    ProviderCapabilities,
    Refused,
    Registration,
    ScopeSet,
    Sequence,
    Started,
    ToolCall,
    Until,
    Usage,
)
from shadow_hdk.kernel.contracts import CONTRACTS, all_schemas, round_trip
from shadow_hdk.kernel.ports import Message
from shadow_hdk.kernel.providers import EnvVar, Provider

PROVENANCE = Provenance(registered_by="tests", adapter="python-callable", at="2026-09-10T00:00:00Z")
COMPONENT = Component(
    interface=Interface("echo", "returns its input", {"type": "object"}, {"type": "object"}),
    effects=EffectProfile(reads=ScopeSet.of("session")),
    provenance=PROVENANCE,
    labels=frozenset({"tool"}),
)
COMPOSITION = Composition(
    steps=(
        Sequence(
            "s1",
            (
                Invoke("i1", "reg-1", (Binding("text", value="hi"),)),
                FanOut(
                    "f1", (Invoke("i2", "reg-2"), Invoke("i3", "reg-2", (Binding("x", ref="i1"),)))
                ),
                Until("u1", Invoke("i4", "reg-3"), Condition("ok", True), max_iterations=5),
            ),
        ),
    )
)
LEASE = Lease(Ceiling(max_steps=10, max_wall_seconds=600, max_cost_cents=100), Floor(2))

PROVIDER = Provider(
    id="claude-code",
    kind="agent",
    bin="claude",
    fallback_bins=("openclaude",),
    auth_probe=("auth", "status"),
    set_env=(EnvVar(name="SHADOW_HDK", value="1"),),
    strip_env=("CLAUDECODE",),
)
"""A provider crosses the wire because a host in another language reads the library too."""

EXAMPLES = {
    "ProviderCapabilities": (ProviderCapabilities(), ProviderCapabilities),
    "EnvironmentCapabilities": (EnvironmentCapabilities(), EnvironmentCapabilities),
    "ExecutionRequirements": (ExecutionRequirements(), ExecutionRequirements),
    "ExecutionSelection": (
        ExecutionSelection(ProviderCapabilities(), EnvironmentCapabilities(), Compatibility()),
        ExecutionSelection,
    ),
    "Compatibility": (Compatibility(), Compatibility),
    "EffectProfile": (
        EffectProfile(reads=ScopeSet(everything=True), reversible=False),
        EffectProfile,
    ),
    "Component": (COMPONENT, Component),
    "Provider": (PROVIDER, Provider),
    "Registration": (Registration("reg-1", COMPONENT), Registration),
    "Composition": (COMPOSITION, Composition),
    "Observation": (Pending(handle="h1"), CONTRACTS["Observation"]),
    "Proposal": (Proposal("claim", {"text": "3 of 1842"}, PROVENANCE, ("i1",)), Proposal),
    "Lease": (LEASE, Lease),
    "Event": (
        Observed("run-1", 3, "2026-09-10T00:00:01Z", "i1", Completed({"n": 1})),
        CONTRACTS["Event"],
    ),
    "ModelRequest": (
        ModelRequest((Message("user", "hello"),), (COMPONENT.interface,), "local"),
        ModelRequest,
    ),
    "ModelResponse": (
        ModelResponse("", (ToolCall("c1", "echo", {"text": "hi"}),), Usage(1, 2, None)),
        ModelResponse,
    ),
    "Context": (Context("run-1", "i1", "person:1", {"mode": "capture"}), Context),
    "Judgement": (Ask("may it reach the network?"), CONTRACTS["Judgement"]),
}


def test_every_contract_has_an_example() -> None:
    assert set(EXAMPLES) == set(CONTRACTS)


@pytest.mark.parametrize("name", sorted(CONTRACTS))
def test_round_trips_through_json(name: str) -> None:
    value, as_type = EXAMPLES[name]
    assert round_trip(value, as_type) == value


def test_every_union_member_round_trips() -> None:
    for observation in (Completed({"a": 1}), Refused("no"), Pending("h")):
        assert round_trip(observation, CONTRACTS["Observation"]) == observation
    for judgement in (Allow(), Ask("why?")):
        assert round_trip(judgement, CONTRACTS["Judgement"]) == judgement
    for event in (
        Started("r", 0, "t", LEASE),
        Composed("r", 1, "t", COMPOSITION),
        Invoked("r", 2, "t", "i1", "reg-1", {"text": "hi"}),
        Proposed("r", 3, "t", Proposal("claim", None, PROVENANCE)),
        Ended("r", 4, "t", "completed", 4),
    ):
        assert round_trip(event, CONTRACTS["Event"]) == event


def test_schemas_publish_and_name_the_discriminator() -> None:
    schemas = all_schemas()
    assert set(schemas) == set(CONTRACTS)
    assert "discriminator" in schemas["Event"] or "oneOf" in schemas["Event"]
