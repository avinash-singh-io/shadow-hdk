"""Identity on the thread, scope on the rows (Phase 29 group 3, D82).

A rule or a mode may say who it is for: a principal's name, or `attribute:value` — `tenant:acme`
— in the product's own words. Empty is everyone. Governance reads the thread's principal and
attributes off every judgement's context, so a rule made by one person never speaks for another,
and a tenant's mode is not a mode for anybody else's thread.
"""

from __future__ import annotations

from typing import Any

import pytest

from shadow_hdk.adapters.modes import ActRules, Mode, ModeGovernance, ModeRegistry, store_modes
from shadow_hdk.kernel import ActRule, EffectProfile, ScopeSet
from shadow_hdk.kernel.ports import Allow, Ask, Context, Refuse
from shadow_hdk.kernel.rules import in_scope
from shadow_hdk.runtime.store import InMemoryStore

pytestmark = pytest.mark.anyio

WORKSPACE = ScopeSet.of("workspace")
WRITES = EffectProfile(writes=WORKSPACE, reversible=False)
ASKING = Mode(
    "asking",
    ceiling=EffectProfile(reads=WORKSPACE, writes=WORKSPACE, reversible=False),
    ask_above=EffectProfile(reads=WORKSPACE),
)


# ---------------------------------------------------------------- the kernel's word


@pytest.mark.parametrize(
    ("scope", "principal", "attributes", "expected"),
    [
        ("", None, {}, True),
        ("", "alice", {"tenant": "acme"}, True),
        ("alice", "alice", {}, True),
        ("alice", "bob", {}, False),
        ("alice", None, {}, False),
        ("tenant:acme", "bob", {"tenant": "acme"}, True),
        ("tenant:acme", "bob", {"tenant": "other"}, False),
        ("tenant:acme", "bob", {}, False),
        ("tenant:acme", "tenant:acme", {}, False),  # a principal is not an attribute
        ("tenant:acme", "bob", {"tenant": ["acme"]}, False),  # a value, not a list of them
    ],
)
def test_in_scope(scope: str, principal: str | None, attributes: Any, expected: bool) -> None:
    assert in_scope(scope, principal=principal, attributes=attributes) is expected


def test_a_rule_holds_only_in_its_scope() -> None:
    rule = ActRule(component="write_file", scope="alice")
    assert rule.matches("write_file", {}, principal="alice")
    assert not rule.matches("write_file", {}, principal="bob")
    assert not rule.matches("write_file", {})
    tenant = ActRule(component="write_file", scope="tenant:acme")
    assert tenant.matches("write_file", {}, principal="bob", attributes={"tenant": "acme"})
    assert not tenant.matches("write_file", {}, principal="bob", attributes={"tenant": "x"})
    assert ActRule(component="write_file").matches("write_file", {}, principal="anyone")


# ---------------------------------------------------------------- governance reads the context


def _context(principal: str | None, **attributes: Any) -> Context:
    return Context(
        run_id="r",
        step="s",
        principal=principal,
        attributes={"mode": "asking", "component": "write_file", "inputs": {}, **attributes},
    )


async def test_a_rule_made_by_one_person_does_not_speak_for_another() -> None:
    rules = ActRules([ActRule(component="write_file", scope="alice")])
    governance = ModeGovernance({"asking": ASKING}, default="asking", rules=rules)
    assert isinstance(await governance.judge(WRITES, _context("alice")), Allow)
    assert isinstance(await governance.judge(WRITES, _context("bob")), Ask)
    assert isinstance(await governance.judge(WRITES, _context(None)), Ask)


async def test_a_tenants_deny_rule_holds_for_every_thread_of_that_tenant() -> None:
    rules = ActRules([ActRule(component="write_file", decision="deny", scope="tenant:acme")])
    governance = ModeGovernance({"asking": ASKING}, default="asking", rules=rules)
    assert isinstance(await governance.judge(WRITES, _context("bob", tenant="acme")), Refuse)
    assert isinstance(await governance.judge(WRITES, _context("bob", tenant="beta")), Ask)


async def test_a_mode_scoped_to_a_tenant_is_not_a_mode_for_another() -> None:
    store = InMemoryStore()
    await store.put(
        "modes",
        "acme-open",
        {"id": "acme-open", "policy": "full", "environment": "full", "scope": "tenant:acme"},
    )
    registry = ModeRegistry(sources=(store_modes(store),))
    found = await registry.find("acme-open")
    assert found is not None and found.scope == "tenant:acme"
    assert await registry.find("acme-open", principal="bob", attributes={"tenant": "acme"})
    assert await registry.find("acme-open", principal="bob", attributes={"tenant": "beta"}) is None
    assert [m.id for m in await registry.all(principal="x", attributes={"tenant": "beta"})] == []
    assert [m.id for m in await registry.all(principal="x", attributes={"tenant": "acme"})] == [
        "acme-open"
    ]
    assert [m.id for m in await registry.all()] == ["acme-open"], "nobody named: everything"

    governance = ModeGovernance(registry, default="acme-open")
    judged = await governance.judge(
        WRITES,
        Context(
            run_id="r",
            step="s",
            principal="bob",
            attributes={"mode": "acme-open", "tenant": "beta"},
        ),
    )
    assert isinstance(judged, Refuse) and "not a mode" in judged.reason
    judged = await governance.judge(
        WRITES,
        Context(
            run_id="r",
            step="s",
            principal="bob",
            attributes={"mode": "acme-open", "tenant": "acme"},
        ),
    )
    assert isinstance(judged, Allow)


async def test_rules_and_modes_list_in_scope_when_asked() -> None:
    rules = ActRules(
        [
            ActRule(component="a", scope="alice"),
            ActRule(component="b", scope="tenant:acme"),
            ActRule(component="c"),
        ]
    )
    assert [r.component for r in await rules.all_now()] == ["a", "b", "c"]
    assert [
        r.component for r in await rules.all_now(principal="alice", attributes={"tenant": "beta"})
    ] == ["a", "c"]
    assert [
        r.component for r in await rules.all_now(principal="bob", attributes={"tenant": "acme"})
    ] == ["b", "c"]
