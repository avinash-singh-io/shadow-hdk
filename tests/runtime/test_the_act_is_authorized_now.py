"""A controlled irreversible component crosses one current-authority boundary."""

from __future__ import annotations

import dataclasses
from typing import Any, cast

from shadow_hdk.kernel import (
    AuthoritySnapshot,
    Binding,
    Ceiling,
    Composition,
    EffectAuthorization,
    EffectProfile,
    Floor,
    Invoke,
    Lease,
    Refuse,
    ScopeSet,
    StagedEffect,
)
from shadow_hdk.runtime import InMemoryEffectJournal, RunOptions, run
from shadow_hdk.runtime.testing import make_registration
from tests.runtime.conftest import ports_over

IRREVERSIBLE = EffectProfile(writes=ScopeSet.of("workspace"), reversible=False)
WRITE = make_registration("publish", effects=IRREVERSIBLE)


def snapshot(policy: str = "policy:1") -> AuthoritySnapshot:
    return AuthoritySnapshot("alice", "workspace:1", policy, "registry:1", "provider:1", "mode:1")


class Current:
    def __init__(self) -> None:
        self.value = snapshot()
        self.reads: list[tuple[str, str]] = []

    async def current(self, *, run_id: str, step: str) -> AuthoritySnapshot:
        self.reads.append((run_id, step))
        return self.value


class Grants:
    def __init__(self, current: Current, *, narrow: bool = False) -> None:
        self.current = current
        self.narrow = narrow
        self.calls: list[StagedEffect] = []

    async def authorize(
        self, effect: StagedEffect, authority: AuthoritySnapshot
    ) -> EffectAuthorization | Refuse:
        self.calls.append(effect)
        if self.narrow:
            self.current.value = snapshot("policy:2")
        return EffectAuthorization(
            "grant-1",
            effect.digest,
            effect.run_id,
            effect.step,
            authority.principal,
            authority.digest,
            "2099-01-01T00:00:00+00:00",
            effect.idempotency_key,
        )


async def execute(*, supported: bool, narrow: bool = False, observed: bool = False) -> Any:
    registration = WRITE
    if observed:
        registration = dataclasses.replace(
            WRITE,
            component=dataclasses.replace(
                WRITE.component,
                provenance=dataclasses.replace(WRITE.component.provenance, posture="observed"),
            ),
        )
    ports, components = ports_over([(registration, {"receipt": "one"})])
    current = Current()
    grants = Grants(current, narrow=narrow)
    journal = InMemoryEffectJournal()
    if supported:
        ports = dataclasses.replace(
            ports, authority=current, authorizer=grants, effect_journal=journal
        )
    else:
        ports = dataclasses.replace(ports, authority=None, authorizer=None, effect_journal=None)
    events = [
        event
        async for event in run(
            Composition((Invoke("write-1", "publish", (Binding("value", value=3),)),)),
            ports,
            options=RunOptions(
                lease=Lease(Ceiling(5, 60, 10), Floor(0)),
                principal="alice",
                run_id="run-1",
            ),
        )
    ]
    return events, components, current, grants, journal


async def test_a_controlled_irreversible_path_without_transaction_ports_is_refused() -> None:
    events, components, *_ = await execute(supported=False)
    assert components.calls == []
    assert [event.kind for event in events][-2:] == ["observed", "ended"]
    assert events[-2].observation.kind == "refused"


async def test_stage_authorize_reread_execute_and_receipt_are_in_order() -> None:
    events, components, current, grants, journal = await execute(supported=True)
    assert components.calls == [("publish", {"value": 3})]
    assert current.reads == [("run-1", "write-1"), ("run-1", "write-1")]
    assert len(grants.calls) == 1
    assert [row.kind for row in await journal.read("run-1/write-1")] == [
        "staged",
        "authorized",
        "executing",
        "receipt",
    ]
    assert events[-2].observation.kind == "completed"


async def test_authority_narrowed_after_consent_is_refused_without_invocation() -> None:
    events, components, _, _, journal = await execute(supported=True, narrow=True)
    assert components.calls == []
    assert [row.kind for row in await journal.read("run-1/write-1")] == [
        "staged",
        "authorized",
        "refused",
    ]
    assert events[-2].observation.reason == "authority_changed"


async def test_an_observed_irreversible_path_remains_observed_without_an_authorization() -> None:
    events, components, *_ = await execute(supported=False, observed=True)
    assert components.calls == [("publish", {"value": 3})]
    assert events[-2].posture == "observed"


async def test_a_reused_attempt_key_cannot_return_a_receipt_for_changed_inputs() -> None:
    ports, components = ports_over([(WRITE, {"receipt": "one"})])
    first = Composition((Invoke("write-1", "publish", (Binding("value", value=1),)),))
    changed = Composition((Invoke("write-1", "publish", (Binding("value", value=2),)),))
    options = RunOptions(
        lease=Lease(Ceiling(5, 60, 10), Floor(0)),
        principal="alice",
        run_id="same-run",
    )
    _ = [event async for event in run(first, ports, options=options)]
    replay = [event async for event in run(changed, ports, options=options)]

    assert components.calls == [("publish", {"value": 1})]
    replayed = cast(Any, replay[-2]).observation
    assert replayed.kind == "refused"
    assert replayed.reason == "idempotency_key_reused_for_different_effect"
