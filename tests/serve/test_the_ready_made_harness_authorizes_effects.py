"""The ready-made Shadow Harness owns the same act-time boundary exposed by the HDK."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from shadow_hdk.adapters.basic import CallableComponents, SqliteEffectJournal
from shadow_hdk.adapters.modes import ActRules
from shadow_hdk.kernel import (
    ActRule,
    Binding,
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Floor,
    Invoke,
    Lease,
    Observed,
    ScopeSet,
    Workspace,
)
from shadow_hdk.runtime import RunOptions, run
from shadow_hdk.runtime.testing import make_registration
from shadow_hdk.serve import HostAuthority, modes_for, workshop
from tests.runtime.conftest import ports_over


async def test_live_policy_and_registry_changes_move_reference_authority(tmp_path: Path) -> None:
    rules = ActRules()
    modes = modes_for()
    components = CallableComponents()
    components.add(lambda: "one", effects=EffectProfile(), name="one")
    authority = HostAuthority(
        workspace=Workspace.of(tmp_path),
        modes=modes,
        rules=rules,
        components=(components,),
        provider_revision="provider:1",
        principal="alice",
        mode="full",
    )

    first = await authority.current(run_id="run-1", step="step-1")
    rules.add(ActRule(component="publish", inputs={}, decision="allow"))
    second = await authority.current(run_id="run-1", step="step-1")
    assert second.policy_revision != first.policy_revision

    components.add(lambda: "two", effects=EffectProfile(), name="two")
    third = await authority.current(run_id="run-1", step="step-1")
    assert third.registry_revision != second.registry_revision
    assert third.principal == "alice"


async def test_workshop_executes_an_irreversible_callable_through_its_boundary(
    tmp_path: Path,
) -> None:
    writes: list[str] = []
    callables = CallableComponents()

    def publish(value: str) -> dict[str, bool]:
        writes.append(value)
        return {"published": True}

    callables.add(
        publish,
        effects=EffectProfile(writes=ScopeSet.of("workspace"), reversible=False),
    )
    ports = await workshop(tmp_path, mode="full", batteries=(callables,))
    assert ports.authority is not None
    assert ports.authorizer is not None
    assert ports.effect_journal is not None

    events = [
        event
        async for event in run(
            Composition((Invoke("publish-1", "publish", (Binding("value", value="v1"),)),)),
            ports,
            options=RunOptions(
                lease=Lease(Ceiling(5, 60, None), Floor(0)),
                principal="alice",
                context={"mode": "full"},
                run_id="run-1",
            ),
        )
    ]
    assert writes == ["v1"]
    assert [event for event in events if isinstance(event, Observed)][-1].observation == Completed(
        {"published": True}
    )
    assert [entry.kind for entry in await ports.effect_journal.read("run-1/publish-1")] == [
        "staged",
        "authorized",
        "executing",
        "receipt",
    ]

    for component in ports.components:
        close = getattr(component, "close", None)
        if close is not None:
            await close()


async def test_a_restarted_host_reuses_a_durable_receipt_without_repeating_the_act(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    registration = make_registration(
        "publish",
        effects=EffectProfile(writes=ScopeSet.of("workspace"), reversible=False),
    )

    async def publish(inputs: object) -> Completed:
        assert isinstance(inputs, dict)
        calls.append(str(inputs["value"]))
        return Completed({"published": True})

    journal_path = tmp_path / "effects.sqlite"
    first_ports, _ = ports_over([(registration, publish)])
    first_journal = SqliteEffectJournal(journal_path)
    first_ports = replace(first_ports, effect_journal=first_journal)
    composition = Composition((Invoke("publish-1", "publish", (Binding("value", value="v1"),)),))
    options = RunOptions(
        lease=Lease(Ceiling(5, 60, None), Floor(0)),
        principal="test-principal",
        run_id="durable-run",
    )
    first = [event async for event in run(composition, first_ports, options=options)]
    assert calls == ["v1"], [
        (
            event.kind,
            getattr(event, "reason", None),
            repr(getattr(event, "observation", None)),
        )
        for event in first
    ]
    await first_journal.aclose()

    second_ports, _ = ports_over([(registration, publish)])
    second_journal = SqliteEffectJournal(journal_path)
    second_ports = replace(second_ports, effect_journal=second_journal)
    second = [event async for event in run(composition, second_ports, options=options)]
    await second_journal.aclose()

    assert calls == ["v1"]
    assert [event for event in first if isinstance(event, Observed)][-1].observation == Completed(
        {"published": True}
    )
    assert [event for event in second if isinstance(event, Observed)][-1].observation == Completed(
        {"published": True}
    )
