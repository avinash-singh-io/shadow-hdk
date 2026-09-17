"""Frozen evaluator v1 for D107–D109, D111: whole-plan admission, in the kernel, pure.

The JSON corpus is versioned and is not changed while Phase 36 is implemented. These tests define
the public data and the admission function before any implementation exists: a composition is
measured — depth, fan-out, steps — against `PlanLimits`; every named component must be registered;
every mismatch is listed, in a stable order; `PlanLimits` composes by `meet` and only narrows.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from shadow_hdk.kernel.planning import composition_digest, measure

from shadow_hdk.kernel import Admitted as AdmittedPlan
from shadow_hdk.kernel import Composition, PlanLimits, PlanMismatch, PlanRefused, admit
from shadow_hdk.kernel.contracts import CONTRACTS, load, round_trip
from shadow_hdk.runtime.testing import make_registration

CORPUS = json.loads(
    (Path(__file__).parents[1] / "benchmarks" / "plan-admission-v1.json").read_text()
)
REGISTERED = tuple(make_registration(name) for name in CORPUS["registered"])


def limits_of(raw: dict[str, int]) -> PlanLimits:
    return PlanLimits(**raw)


def mismatch_of(raw: dict[str, str]) -> PlanMismatch:
    return PlanMismatch(
        axis=raw["axis"], step=raw["step"], required=raw["required"], found=raw["found"]
    )


@pytest.mark.parametrize("case", CORPUS["cases"], ids=[c["name"] for c in CORPUS["cases"]])
def test_the_corpus_measures_every_composition_as_written(case: dict[str, Any]) -> None:
    composition = load(case["composition"], Composition)
    measured = measure(composition)
    assert (measured.depth, measured.fan_out, measured.steps) == (
        case["measures"]["depth"],
        case["measures"]["fan_out"],
        case["measures"]["steps"],
    )


@pytest.mark.parametrize("case", CORPUS["cases"], ids=[c["name"] for c in CORPUS["cases"]])
def test_the_corpus_admits_or_refuses_exactly_as_written(case: dict[str, Any]) -> None:
    composition = load(case["composition"], Composition)
    outcome = admit(composition, REGISTERED, limits_of(case["limits"]))
    if case["expect"] == "admitted":
        assert isinstance(outcome, AdmittedPlan)
        assert outcome.plan_digest == composition_digest(composition)
        assert outcome.limits == limits_of(case["limits"])
    else:
        assert isinstance(outcome, PlanRefused)
        assert list(outcome.mismatches) == [mismatch_of(m) for m in case["expect"]], (
            "every mismatch, in the stable order depth, fan_out, steps, component"
        )


def test_admission_is_deterministic_and_total() -> None:
    """The same inputs give the same answer, and nothing raises — a malformed plan is a refusal,
    not an exception, the same rule the derivation engine follows (BUG-013)."""
    case = CORPUS["cases"][6]
    composition = load(case["composition"], Composition)
    first = admit(composition, REGISTERED, limits_of(case["limits"]))
    second = admit(composition, REGISTERED, limits_of(case["limits"]))
    assert first == second
    assert admit(Composition(()), REGISTERED, PlanLimits()) == PlanRefused(
        (PlanMismatch(axis="steps", step="", required="at least 1", found="0"),)
    )


def test_the_digest_is_canonical_and_input_sensitive() -> None:
    a = load(CORPUS["cases"][0]["composition"], Composition)
    b = load(CORPUS["cases"][0]["composition"], Composition)
    assert composition_digest(a) == composition_digest(b)
    changed = load(
        {
            "steps": [
                {
                    "kind": "invoke",
                    "id": "s1",
                    "component": "look",
                    "inputs": [{"name": "topic", "value": "y"}],
                }
            ]
        },
        Composition,
    )
    assert composition_digest(a) != composition_digest(changed)
    assert len(composition_digest(a)) == 64, "sha-256 hex, like the staged-effect digest"


@pytest.mark.parametrize("row", CORPUS["meet"])
def test_meet_is_per_field_min_with_none_as_unbounded(row: dict[str, Any]) -> None:
    assert limits_of(row["a"]).meet(limits_of(row["b"])) == limits_of(row["meet"])


bounded = st.one_of(st.none(), st.integers(min_value=1, max_value=64))
limits = st.builds(PlanLimits, depth=bounded, fan_out=bounded, steps=bounded)


@given(limits, limits)
def test_meet_is_commutative(a: PlanLimits, b: PlanLimits) -> None:
    assert a.meet(b) == b.meet(a)


@given(limits)
def test_meet_is_idempotent_and_unbounded_is_identity(a: PlanLimits) -> None:
    assert a.meet(a) == a
    assert a.meet(PlanLimits()) == a


@given(limits, limits)
def test_meet_never_widens(a: PlanLimits, b: PlanLimits) -> None:
    met = a.meet(b)
    assert met.narrower_than(a) and met.narrower_than(b)
    assert not a.narrower_than(met) or a == met


def test_every_admission_value_is_a_published_json_contract() -> None:
    assert {"PlanLimits", "PlanMismatch", "Admitted", "PlanRefused"} <= CONTRACTS.keys()
    assert round_trip(PlanLimits(depth=2, fan_out=3, steps=4), PlanLimits).fan_out == 3
    refused = PlanRefused((PlanMismatch(axis="depth", step="a", required="2", found="3"),))
    assert round_trip(refused, PlanRefused) == refused


def test_the_plan_events_are_public_event_kinds() -> None:
    from shadow_hdk.kernel.events import PlanAdmitted
    from shadow_hdk.kernel.events import PlanRefused as PlanRefusedEvent

    admitted = PlanAdmitted(
        run_id="r",
        seq=1,
        at="2026-01-01T00:00:00+00:00",
        plan_digest="d" * 64,
        authority_digest="",
        limits=PlanLimits(depth=2),
        amendment=False,
    )
    refused = PlanRefusedEvent(
        run_id="r",
        seq=2,
        at="2026-01-01T00:00:00+00:00",
        plan_digest="d" * 64,
        mismatches=(PlanMismatch(axis="depth", step="a", required="2", found="3"),),
        amendment=False,
    )
    assert admitted.kind == "plan_admitted" and refused.kind == "plan_refused"
    assert round_trip(admitted, PlanAdmitted) == admitted
    assert round_trip(refused, PlanRefusedEvent) == refused


def test_the_corpus_is_frozen() -> None:
    """Rule 11: the evaluator is locked before the loop it measures. Editing the corpus while Phase
    36 is implemented fails here; a v2 corpus is a new file with its own digest."""
    import hashlib

    corpus = Path(__file__).parents[1] / "benchmarks" / "plan-admission-v1.json"
    assert (
        hashlib.sha256(corpus.read_bytes()).hexdigest()
        == "c83a347854bc6774c57ff48dd1549cdea1c99baed46fd6a7e6393d9674ba01c7"
    )
