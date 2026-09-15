"""The Phase 33 data and host seams are public, crossed and product-testable."""

from __future__ import annotations

from shadow_hdk.kernel import (
    AuthorityPort,
    AuthoritySnapshot,
    AuthorizerPort,
    EffectAuthorization,
    EffectEntry,
    EffectJournalPort,
    Refuse,
    StagedEffect,
)
from shadow_hdk.kernel.contracts import CONTRACTS, round_trip
from shadow_hdk.testing import AuthorityPortContract, AuthorizerPortContract, EffectJournalContract


def test_every_effect_transaction_value_is_a_published_json_contract() -> None:
    assert {
        "AuthoritySnapshot",
        "StagedEffect",
        "EffectAuthorization",
        "EffectEntry",
    } <= CONTRACTS.keys()
    assert (
        round_trip(
            AuthoritySnapshot("alice", "w:1", "p:1", "r:1", "provider:1", "mode:1"),
            AuthoritySnapshot,
        ).principal
        == "alice"
    )


def test_the_three_host_ports_and_contract_suites_ship() -> None:
    assert AuthorityPort.__module__.startswith("shadow_hdk.kernel")
    assert AuthorizerPort.__module__.startswith("shadow_hdk.kernel")
    assert EffectJournalPort.__module__.startswith("shadow_hdk.kernel")
    assert AuthorityPortContract.__module__.startswith("shadow_hdk.testing")
    assert AuthorizerPortContract.__module__.startswith("shadow_hdk.testing")
    assert EffectJournalContract.__module__.startswith("shadow_hdk.testing")


def test_an_authorization_contains_only_data_and_round_trips() -> None:
    grant = EffectAuthorization("g", "d", "r", "s", "alice", "a", "2026-09-16", "r/s")
    assert round_trip(grant, EffectAuthorization) == grant
    assert not any(callable(value) for value in grant.__dict__.values())


def test_protocol_return_types_remain_data_unions() -> None:
    annotations = AuthorizerPort.authorize.__annotations__
    assert "EffectAuthorization" in str(annotations["return"])
    assert "Refuse" in str(annotations["return"])
    assert EffectEntry.__annotations__["detail"] is not object
    assert StagedEffect.__annotations__["inputs"] is not object
    assert Refuse("no").kind == "refuse"
