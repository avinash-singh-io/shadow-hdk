"""Frozen evaluator v1 for D99-D104: current authority at one irreversible act.

The JSON corpus is versioned and is not changed while Phase 33 is implemented. These tests define
the public data, journal and recovery semantics before any implementation exists.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest
from shadow_hdk.runtime.effects import (
    EffectTransaction,
    InMemoryEffectJournal,
    JournalConflict,
    TransactionCrash,
    fold_effect,
    recover_effect,
)

from shadow_hdk.kernel import (
    AuthoritySnapshot,
    EffectAuthorization,
    EffectEntry,
    EffectProfile,
    Refuse,
    ScopeSet,
    StagedEffect,
    authority_digest,
    stage_effect,
)
from shadow_hdk.kernel.contracts import round_trip

CORPUS = json.loads(
    (Path(__file__).parents[1] / "benchmarks" / "effect-transaction-v1.json").read_text()
)


def authority(**changes: str | None) -> AuthoritySnapshot:
    values: dict[str, str | None] = {
        "principal": "alice",
        "workspace_revision": "workspace:7",
        "policy_revision": "policy:12",
        "registry_revision": "registry:5",
        "provider_revision": "provider:3",
        "mode_revision": "mode:2",
    }
    values.update(changes)
    return AuthoritySnapshot(**values)  # type: ignore[arg-type]


def staged(snapshot: AuthoritySnapshot | None = None, **changes: object) -> StagedEffect:
    snapshot = snapshot or authority()
    values: dict[str, object] = {
        "run_id": "run-parent",
        "step": "write-1",
        "component": "publish",
        "inputs": {"path": "release.json", "value": 3},
        "effects": EffectProfile(writes=ScopeSet.of("workspace"), reversible=False, contained=True),
        "authority_digest": authority_digest(snapshot),
        "idempotency_key": "run-parent/write-1",
    }
    values.update(changes)
    return stage_effect(**values)  # type: ignore[arg-type]


def grant(
    effect: StagedEffect,
    snapshot: AuthoritySnapshot | None = None,
    **changes: object,
) -> EffectAuthorization:
    snapshot = snapshot or authority()
    values: dict[str, object] = {
        "authorization_id": "grant-1",
        "stage_digest": effect.digest,
        "run_id": effect.run_id,
        "step": effect.step,
        "principal": snapshot.principal,
        "authority_digest": authority_digest(snapshot),
        "expires_at": "2026-09-15T12:01:00+00:00",
        "idempotency_key": effect.idempotency_key,
    }
    values.update(changes)
    return EffectAuthorization(**values)  # type: ignore[arg-type]


def entry(kind: str, sequence: int, effect: StagedEffect, **changes: object) -> EffectEntry:
    values: dict[str, object] = {
        "attempt_id": effect.idempotency_key,
        "sequence": sequence,
        "kind": kind,
        "stage_digest": effect.digest,
        "at": f"2026-09-15T12:00:0{min(sequence, 9)}+00:00",
    }
    values.update(changes)
    return EffectEntry(**values)  # type: ignore[arg-type]


def test_authority_and_stage_digests_are_canonical_complete_and_secret_free() -> None:
    snapshot = authority()
    assert len(authority_digest(snapshot)) == 64
    assert authority_digest(round_trip(snapshot, AuthoritySnapshot)) == authority_digest(snapshot)
    for field in (
        "principal",
        "workspace_revision",
        "policy_revision",
        "registry_revision",
        "provider_revision",
        "mode_revision",
    ):
        changed = replace(snapshot, **{field: f"changed:{field}"})
        assert authority_digest(changed) != authority_digest(snapshot), field
    assert "credential" not in json.dumps(snapshot.__dict__).lower()

    effect = staged(snapshot)
    assert len(effect.digest) == 64
    for field, value in (
        ("run_id", "run-other"),
        ("step", "write-other"),
        ("component", "delete"),
        ("inputs", {"value": 4}),
        ("effects", EffectProfile(reaches=True, reversible=False)),
        ("authority_digest", "0" * 64),
        ("idempotency_key", "other/key"),
    ):
        assert replace(effect, **{field: value}).digest != effect.digest, field


@pytest.mark.parametrize("history", CORPUS["legal_histories"])
def test_the_versioned_evaluator_accepts_only_legal_append_order(history: list[str]) -> None:
    effect = staged()
    folded = fold_effect(tuple(entry(kind, seq, effect) for seq, kind in enumerate(history)))
    assert folded.status == history[-1]


@pytest.mark.parametrize("history", CORPUS["illegal_histories"])
def test_the_versioned_evaluator_rejects_illegal_append_order(history: list[str]) -> None:
    effect = staged()
    with pytest.raises(ValueError):
        fold_effect(tuple(entry(kind, seq, effect) for seq, kind in enumerate(history)))


@pytest.mark.asyncio
async def test_the_journal_is_compare_and_append_and_one_grant_is_consumed_once() -> None:
    effect = staged()
    journal = InMemoryEffectJournal()
    await journal.append(entry("staged", 0, effect), expected_length=0)
    authorized = entry("authorized", 1, effect, authorization_id="grant-1")
    await journal.append(authorized, expected_length=1)
    with pytest.raises(JournalConflict):
        await journal.append(entry("executing", 2, effect), expected_length=1)

    other = staged(run_id="run-other", idempotency_key="run-other/write-1")
    await journal.append(entry("staged", 0, other), expected_length=0)
    with pytest.raises(JournalConflict):
        await journal.append(
            entry("authorized", 1, other, authorization_id="grant-1"), expected_length=1
        )


class MutableAuthority:
    def __init__(self, snapshot: AuthoritySnapshot) -> None:
        self.snapshot = snapshot
        self.reads = 0

    async def current(self, *, run_id: str, step: str) -> AuthoritySnapshot:
        self.reads += 1
        return self.snapshot


class Granting:
    def __init__(self, authority_source: MutableAuthority, *, narrow_after: bool = False) -> None:
        self.authority_source = authority_source
        self.narrow_after = narrow_after

    async def authorize(
        self, effect: StagedEffect, current: AuthoritySnapshot
    ) -> EffectAuthorization | Refuse:
        result = grant(effect, current)
        if self.narrow_after:
            self.authority_source.snapshot = replace(current, policy_revision="policy:13")
        return result


class Clock:
    def now(self) -> str:
        return "2026-09-15T12:00:30+00:00"


@pytest.mark.asyncio
async def test_authority_is_read_again_before_invoke_and_stale_consent_cannot_act() -> None:
    snapshot = authority()
    source = MutableAuthority(snapshot)
    journal = InMemoryEffectJournal()
    transaction = EffectTransaction(
        authority=source,
        authorizer=Granting(source, narrow_after=True),
        journal=journal,
        clock=Clock(),
    )
    calls = 0

    async def invoke() -> dict[str, str]:
        nonlocal calls
        calls += 1
        return {"receipt": "sent"}

    result = await transaction.execute(staged(snapshot), invoke=invoke)
    assert result.kind == "refused"
    assert result.reason == "authority_changed"
    assert calls == 0
    assert source.reads == 2
    assert [row.kind for row in await journal.read("run-parent/write-1")] == [
        "staged",
        "authorized",
        "refused",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("changed", "value"),
    [
        ("stage_digest", "0" * 64),
        ("run_id", "other"),
        ("step", "other"),
        ("principal", "mallory"),
        ("authority_digest", "1" * 64),
        ("expires_at", "2026-09-15T11:59:00+00:00"),
        ("idempotency_key", "other/key"),
    ],
)
async def test_a_mismatched_expired_or_cross_run_grant_never_invokes(
    changed: str, value: object
) -> None:
    snapshot = authority()
    effect = staged(snapshot)
    source = MutableAuthority(snapshot)

    class BadGrant:
        async def authorize(
            self, effect: StagedEffect, current: AuthoritySnapshot
        ) -> EffectAuthorization | Refuse:
            return grant(effect, current, **{changed: value})

    calls = 0

    async def invoke() -> dict[str, str]:
        nonlocal calls
        calls += 1
        return {"receipt": "impossible"}

    result = await EffectTransaction(
        authority=source,
        authorizer=BadGrant(),
        journal=InMemoryEffectJournal(),
        clock=Clock(),
    ).execute(effect, invoke=invoke)
    assert result.kind == "refused"
    assert calls == 0


@pytest.mark.asyncio
async def test_duplicate_and_concurrent_delivery_invokes_once_and_reuses_the_receipt() -> None:
    snapshot = authority()
    source = MutableAuthority(snapshot)
    journal = InMemoryEffectJournal()
    transaction = EffectTransaction(
        authority=source, authorizer=Granting(source), journal=journal, clock=Clock()
    )
    calls = 0

    async def invoke() -> dict[str, str]:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return {"receipt": "one"}

    first, second = await asyncio.gather(
        transaction.execute(staged(snapshot), invoke=invoke),
        transaction.execute(staged(snapshot), invoke=invoke),
    )
    assert calls == 1
    assert first.receipt == second.receipt == {"receipt": "one"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("crash_after", "expected"),
    [
        ("staged", "refused"),
        ("authorized", "refused"),
        ("executing", "unknown"),
        ("invoked", "unknown"),
    ],
)
async def test_crash_recovery_never_blindly_retries_a_non_idempotent_effect(
    crash_after: str, expected: str
) -> None:
    snapshot = authority()
    source = MutableAuthority(snapshot)
    journal = InMemoryEffectJournal()
    calls = 0

    async def invoke() -> dict[str, str]:
        nonlocal calls
        calls += 1
        return {"receipt": "maybe"}

    def crash(point: str) -> None:
        if point == crash_after:
            raise TransactionCrash(point)

    transaction = EffectTransaction(
        authority=source,
        authorizer=Granting(source),
        journal=journal,
        clock=Clock(),
        checkpoint=crash,
    )
    with pytest.raises(TransactionCrash):
        await transaction.execute(staged(snapshot), invoke=invoke)
    recovered = await recover_effect(
        staged(snapshot), journal=journal, clock=Clock(), idempotent=False
    )
    assert recovered.status == expected
    assert calls == (1 if crash_after == "invoked" else 0)


@pytest.mark.asyncio
async def test_only_proven_idempotency_and_external_evidence_can_reconcile_unknown() -> None:
    effect = staged()
    journal = InMemoryEffectJournal()
    for seq, kind in enumerate(("staged", "authorized", "executing")):
        await journal.append(entry(kind, seq, effect), expected_length=seq)
    calls = 0

    async def reconcile(key: str) -> dict[str, str] | None:
        nonlocal calls
        calls += 1
        assert key == effect.idempotency_key
        return {"receipt": "found"}

    unknown = await recover_effect(effect, journal=journal, clock=Clock(), idempotent=False)
    assert unknown.status == "unknown"
    assert calls == 0
    reconciled = await recover_effect(
        effect, journal=journal, clock=Clock(), idempotent=True, reconcile=reconcile
    )
    assert reconciled.status == "reconciled"
    assert reconciled.receipt == {"receipt": "found"}
    assert calls == 1


def test_a_parent_authorization_cannot_be_consumed_by_a_child_step() -> None:
    parent = staged()
    child = staged(run_id="run-child", step="child-write", idempotency_key="run-child/child-write")
    parent_grant = grant(parent)
    assert not parent_grant.permits(child, authority())
    assert parent_grant.permits(parent, authority())
