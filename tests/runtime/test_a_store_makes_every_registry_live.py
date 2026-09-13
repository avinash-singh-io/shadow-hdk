"""Data changes live; code changes restart (principle 10, D66).

One `Store` port — collections of JSON rows, a version per collection that moves on every write —
and every registry takes it as a source: a row written now is read at the next read, with no
restart and no file to edit. Modes, act rules, skills, which components are on, providers. The
runtime never imports an adapter, so the store reaches each registry the way the others do: as a
source the host hands in.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.adapters.agent import SkillRegistry, store_skills
from shadow_hdk.adapters.modes import (
    ActRules,
    ModeRegistry,
    modes_in,
    store_modes,
    store_rules,
)
from shadow_hdk.adapters.modes.registry import shipped_modes
from shadow_hdk.kernel import ActRule, Store
from shadow_hdk.runtime.store import InMemoryStore
from shadow_hdk.runtime.switched import Switched, store_switches
from shadow_hdk.runtime.testing import InMemoryComponents, make_registration
from tests.adapters.contract.suites import ComponentPortContract, StoreContract

pytestmark = pytest.mark.anyio


# ------------------------------------------------------------------ the port


async def test_a_store_keeps_rows_by_collection_and_moves_its_version_on_every_write() -> None:
    store: Store = InMemoryStore()
    assert await store.version("modes") == 0
    await store.put("modes", "calm", {"id": "calm", "name": "Calm"})
    assert await store.version("modes") == 1
    assert await store.get("modes", "calm") == {"id": "calm", "name": "Calm"}
    assert await store.version("rules") == 0, "collections have their own versions"
    await store.delete("modes", "calm")
    assert await store.get("modes", "calm") is None
    assert await store.version("modes") == 2
    assert await store.list("modes") == ()


# ------------------------------------------------------------------ modes


async def test_a_mode_row_written_now_is_a_mode_at_the_next_read() -> None:
    store = InMemoryStore()
    registry = ModeRegistry(shipped_modes(), sources=(store_modes(store),))
    assert await registry.find("calm") is None

    await store.put(
        "modes",
        "calm",
        {
            "id": "calm",
            "name": "Calm",
            "description": "Read only, think aloud.",
            "policy": "read-only",
            "behaviour": {"append_system": "Be calm.", "effort": "low"},
        },
    )

    found = await registry.find("calm")
    assert found is not None and found.name == "Calm"
    assert found.behaviour.append_system == "Be calm." and found.behaviour.effort == "low"
    assert found.policy.name == "read-only", "a policy is named, never authored as effects here"
    assert found.source == "store"


async def test_a_mode_row_that_names_no_known_policy_is_reported_not_loaded() -> None:
    store = InMemoryStore()
    registry = ModeRegistry(shipped_modes(), sources=(store_modes(store),))
    await store.put("modes", "odd", {"id": "odd", "policy": "no-such-policy"})

    assert await registry.find("odd") is None
    assert any("no-such-policy" in problem for problem in await registry.problems())


async def test_a_store_mode_can_shadow_a_shipped_one_by_id() -> None:
    store = InMemoryStore()
    registry = ModeRegistry(shipped_modes(), sources=(store_modes(store),))
    await store.put("modes", "full", {"id": "full", "name": "Everything", "policy": "full"})

    found = await registry.find("full")
    assert found is not None and found.name == "Everything" and found.source == "store"


async def test_modes_come_from_files_too_in_the_shape_a_person_writes(tmp_path: Path) -> None:
    """OpenCode's shape: a markdown file with frontmatter, the body the system prompt; or TOML."""
    (tmp_path / "reviewer.md").write_text(
        "---\nname: Reviewer\ndescription: Reads, never writes.\npolicy: read-only\n"
        "model: sonnet\neffort: high\n---\nYou review code. Point at lines; do not edit.\n",
        encoding="utf-8",
    )
    (tmp_path / "builder.toml").write_text(
        'id = "builder"\nname = "Builder"\npolicy = "workspace-write"\n'
        '[behaviour]\nappend_system = "Build it."\ntemperature = 0.2\n',
        encoding="utf-8",
    )
    registry = ModeRegistry(shipped_modes(), sources=(modes_in(tmp_path),))

    reviewer = await registry.find("reviewer")
    assert reviewer is not None
    assert reviewer.name == "Reviewer" and reviewer.policy.name == "read-only"
    assert reviewer.behaviour.model == "sonnet" and reviewer.behaviour.effort == "high"
    assert reviewer.behaviour.append_system.startswith("You review code.")
    builder = await registry.find("builder")
    assert builder is not None and builder.behaviour.temperature == 0.2
    assert reviewer.source == "file"


async def test_a_file_written_after_the_registry_was_made_is_read_at_the_next_read(
    tmp_path: Path,
) -> None:
    registry = ModeRegistry(shipped_modes(), sources=(modes_in(tmp_path),))
    assert await registry.find("late") is None
    (tmp_path / "late.md").write_text("---\npolicy: read-only\n---\nLate.\n", encoding="utf-8")
    assert await registry.find("late") is not None


# ------------------------------------------------------------------ rules


async def test_a_rule_row_written_now_decides_at_the_next_judgement() -> None:
    store = InMemoryStore()
    rules = ActRules(sources=(store_rules(store),))
    assert await rules.decide_now("write_file", {"path": "a.txt"}) is None

    await store.put("rules", "r1", {"component": "write_file", "inputs": {"path": "a.txt"}})

    assert await rules.decide_now("write_file", {"path": "a.txt"}) == "allow"


async def test_a_rule_the_person_made_goes_to_the_store_when_there_is_one() -> None:
    """`ActRules.add` writes through: the rule outlives the process, and any other reader of the
    store sees it."""
    store = InMemoryStore()
    rules = ActRules(sources=(store_rules(store),))
    await rules.add_now(ActRule(component="run_shell", inputs={"command": "ls"}))

    rows = await store.list("rules")
    assert [cast(dict[str, Any], row)["component"] for _key, row in rows] == ["run_shell"]
    fresh = ActRules(sources=(store_rules(store),))
    assert await fresh.decide_now("run_shell", {"command": "ls"}) == "allow"


# ------------------------------------------------------------------ skills


async def test_a_skill_row_written_now_is_a_skill_at_the_next_read() -> None:
    store = InMemoryStore()
    registry = SkillRegistry((store_skills(store),))
    assert [s.name for s in await registry.all()] == []

    await store.put(
        "skills",
        "summarise",
        {"name": "summarise", "description": "Sum it up.", "prompt": "Summarise: {text}"},
    )

    assert [s.name for s in await registry.all()] == ["summarise"]


# ------------------------------------------------------------------ components on and off


async def test_a_component_switched_off_in_the_store_is_not_offered_at_the_next_refresh() -> None:
    store = InMemoryStore()
    inner = InMemoryComponents([(make_registration("look"), _ok), (make_registration("wipe"), _ok)])
    switched = Switched(inner, store_switches(store))

    assert sorted(r.id for r in await switched.registrations()) == ["look", "wipe"]
    await store.put("components", "wipe", {"id": "wipe", "on": False})
    assert sorted(r.id for r in await switched.registrations()) == ["look"]
    await store.put("components", "wipe", {"id": "wipe", "on": True})
    assert sorted(r.id for r in await switched.registrations()) == ["look", "wipe"]


async def test_a_switched_off_component_cannot_be_invoked_either() -> None:
    from shadow_hdk.kernel import Refused

    store = InMemoryStore()
    switched = Switched(
        InMemoryComponents([(make_registration("wipe"), _ok)]), store_switches(store)
    )
    await store.put("components", "wipe", {"id": "wipe", "on": False})

    assert isinstance(await switched.invoke("wipe", {}), Refused)


# ------------------------------------------------------------------ providers


async def test_a_provider_row_written_now_is_in_the_library_at_the_next_read() -> None:
    from shadow_hdk.providers import library_from, store_providers

    store = InMemoryStore()
    await store.put(
        "providers",
        "acme",
        {
            "id": "acme",
            "name": "Acme Agent",
            "kind": "agent",
            "bin": "acme",
            "transport": "jsonl",
            "install_hint": "brew install acme",
        },
    )

    found = await library_from(store_providers(store))
    assert "acme" in found and found["acme"].name == "Acme Agent"
    assert "claude-code" in found, "the shipped library is still there underneath"


async def test_a_malformed_provider_row_is_reported_exactly_as_a_file_would_be() -> None:
    from shadow_hdk.providers import store_providers

    store = InMemoryStore()
    await store.put("providers", "odd", {"id": "odd", "called": "Odd", "kind": "agent", "bin": "x"})
    source = store_providers(store)

    assert await source.providers() == {}
    assert any("unknown field" in p and "called" in p for p in await source.problems())


async def _ok(_inputs: Any) -> Any:
    from shadow_hdk.kernel import Completed

    return Completed({})


class TestInMemoryStoreIsAStore(StoreContract):
    def store(self) -> InMemoryStore:
        return InMemoryStore()


class TestSwitchedIsAComponentPort(ComponentPortContract):
    def port(self) -> Any:
        return Switched(
            InMemoryComponents([(make_registration("echo"), _ok)]), store_switches(InMemoryStore())
        )

    def valid_call(self) -> tuple[str, Any]:
        return "echo", {}


# ------------------------------------------------------------------ live through a run


async def test_a_mode_added_to_the_store_is_judged_from_at_the_next_step() -> None:
    """The whole claim, end to end: governance over a registry with a store source; a mode row
    written after the run's ports were built selects at the next judgement."""
    from shadow_hdk.adapters.modes import governance_for
    from shadow_hdk.kernel import Binding, Ceiling, Composition, Floor, Invoke, Lease
    from shadow_hdk.runtime import Ports, RunOptions, run
    from shadow_hdk.runtime.testing import FixedClock, ListSink

    store = InMemoryStore()
    registry = ModeRegistry(shipped_modes(), sources=(store_modes(store),))
    ports = Ports(
        model=None,
        components=(InMemoryComponents([(make_registration("look"), _ok)]),),
        governance=governance_for(registry, default="read-only"),
        sink=ListSink(),
        clock=FixedClock(),
    )
    plan = Composition((Invoke("s1", "look", (Binding("brief", value=""),)),))

    def options(mode: str) -> RunOptions:
        return RunOptions(
            lease=Lease(Ceiling(5, 60, None), Floor(0)), run_id=mode, context={"mode": mode}
        )

    before = [e async for e in run(plan, ports, options=options("calm"))]
    assert any(e.kind == "refused" and "not a mode here" in e.reason for e in before)

    await store.put("modes", "calm", {"id": "calm", "policy": "read-only"})

    after = [e async for e in run(plan, ports, options=options("calm"))]
    assert not any(e.kind == "refused" for e in after), "the new mode judged the step"
    assert [e for e in after if e.kind == "ended"][-1].reason == "completed"


async def test_a_rule_made_at_answer_time_is_written_through_to_the_store() -> None:
    """`accept_answer` keeps the rule in the run's registry *and*, through it, in the store."""
    from shadow_hdk.adapters.modes import Mode, ModeGovernance
    from shadow_hdk.kernel import (
        Binding,
        Ceiling,
        Completed,
        Composition,
        EffectProfile,
        Floor,
        Invoke,
        Lease,
        ScopeSet,
    )
    from shadow_hdk.runtime import (
        Approvals,
        ApproveAndAddRule,
        Ports,
        RunOptions,
        current_run,
        run,
    )
    from shadow_hdk.runtime.testing import FixedClock, ListSink

    store = InMemoryStore()
    rules = ActRules(sources=(store_rules(store),))
    approvals = Approvals()
    asking = Mode(
        "asking",
        ceiling=EffectProfile(reads=ScopeSet.of("workspace"), writes=ScopeSet.of("workspace")),
        ask_above=EffectProfile(reads=ScopeSet.of("workspace")),
    )

    async def asks(_inputs: Any) -> Any:
        context = current_run()
        assert context is not None
        judged = await context.request_approval("may it?", about=("write_file", {"path": "a"}))
        return Completed({"judged": judged.kind})

    ports = Ports(
        model=None,
        components=(InMemoryComponents([(make_registration("asks"), asks)]),),
        governance=ModeGovernance({"asking": asking}, default="asking", rules=rules),
        sink=ListSink(),
        clock=FixedClock(),
    )
    import asyncio

    async def answer_it() -> None:
        pending = await approvals.next()
        approvals.answer(
            pending.handle, ApproveAndAddRule(ActRule(component="write_file", inputs={"path": "a"}))
        )

    asyncio.create_task(answer_it())
    [
        e
        async for e in run(
            Composition((Invoke("s1", "asks", (Binding("brief", value=""),)),)),
            ports,
            options=RunOptions(
                lease=Lease(Ceiling(5, 60, None), Floor(0)),
                run_id="r",
                approvals=approvals,
                rules=rules,
            ),
        )
    ]

    assert [cast(dict[str, Any], row)["component"] for _k, row in await store.list("rules")] == [
        "write_file"
    ]
