"""An agent comes from the product's store, like a skill does (D174, phase 64).

The last asymmetry in lane P's boundary. Skills, modes, rules, batteries, providers and component
switches all live in the product's database and are read back by the kit; an agent architecture
lived only in a packaged TOML or a file path. A plugin whose Build agent, Reviewer, Test fixer and
Release writer cannot be stored is not a plugin — it is one hardcoded role.

`pattern_from(data, where=)` already existed, so this is the missing source and nothing more: the
same version-gated reload `StoreSkills` has, and the same rule that **a malformed row is skipped
rather than fatal** — one bad agent must not take the other three down.
"""

from __future__ import annotations

from typing import Any

import pytest

from shadow_hdk.adapters.agent.loader import shipped
from shadow_hdk.adapters.agent.patterns import StorePatterns, store_patterns

pytestmark = pytest.mark.anyio


class FakeStore:
    """The `Store` port's shape, with a version that moves only when a row is written."""

    def __init__(self, rows: dict[str, Any] | None = None) -> None:
        self.rows: dict[str, Any] = dict(rows or {})
        self.bumps = 0
        self.listings = 0

    async def version(self, collection: str) -> int:
        return self.bumps

    async def list(self, collection: str) -> list[tuple[str, Any]]:
        self.listings += 1
        return list(self.rows.items())

    async def put(self, collection: str, key: str, row: Any) -> None:
        self.rows[key] = row
        self.bumps += 1

    async def delete(self, collection: str, key: str) -> None:
        self.rows.pop(key, None)
        self.bumps += 1


A_REVIEWER = {
    "name": "reviewer",
    "system": "REVIEWER-ROLE: you review a change and say what is wrong with it.",
    "max_turns": 6,
}


# ------------------------------------------------------------------ it reads the product's rows


async def test_an_agent_in_the_store_is_offered(tmp_path: Any) -> None:
    source = store_patterns(FakeStore({"reviewer": A_REVIEWER}))

    found = await source.patterns()

    assert [p.name for p in found] == ["reviewer"]
    assert found[0].system.startswith("REVIEWER-ROLE")
    assert found[0].max_turns == 6


async def test_several_agents_come_back_sorted_by_key(tmp_path: Any) -> None:
    """A product with four agents gets a predictable order, not merely a repeatable one.

    Asserting *stability* alone was not enough — a mutation that reversed the order passed, because
    reversed is stable too. The contract the code and its comment claim is sorted by key, so that is
    what this asserts.
    """
    store = FakeStore(
        {
            "release-writer": {"name": "release-writer", "system": "s"},
            "build": {"name": "build", "system": "s"},
            "reviewer": A_REVIEWER,
        }
    )

    first = [p.name for p in await store_patterns(store).patterns()]
    second = [p.name for p in await store_patterns(store).patterns()]

    assert first == ["build", "release-writer", "reviewer"], first
    assert first == second, "and the same on a second read"


async def test_an_empty_store_offers_nothing_rather_than_failing(tmp_path: Any) -> None:
    assert await store_patterns(FakeStore()).patterns() == ()


# ------------------------------------------------------------------ and reloads only when it must


async def test_the_store_is_read_once_until_its_version_moves(tmp_path: Any) -> None:
    """The same version gate `StoreSkills` has. An agent listing read on every turn would make a
    per-turn store round trip out of something that changes when a person edits a plugin."""
    store = FakeStore({"reviewer": A_REVIEWER})
    source = store_patterns(store)

    await source.patterns()
    await source.patterns()
    assert store.listings == 1, "it read the store twice for an unchanged collection"

    await store.put("agents", "build", {"name": "build", "system": "s"})
    found = await source.patterns()

    assert store.listings == 2, "a moved version must be re-read"
    assert sorted(p.name for p in found) == ["build", "reviewer"]


async def test_a_deleted_agent_stops_being_offered(tmp_path: Any) -> None:
    store = FakeStore({"reviewer": A_REVIEWER, "build": {"name": "build", "system": "s"}})
    source = store_patterns(store)
    assert len(await source.patterns()) == 2

    await store.delete("agents", "build")

    assert [p.name for p in await source.patterns()] == ["reviewer"]


# ------------------------------------------------------------------ and survives a bad row


async def test_one_malformed_agent_does_not_take_the_others_down(tmp_path: Any) -> None:
    """A product editing four agents must not lose the three that are fine because of the one
    that is not — the rule `StoreSkills` already keeps."""
    store = FakeStore(
        {
            "reviewer": A_REVIEWER,
            "broken": {"name": "broken"},  # no `system`, which pattern_from requires
            "worse": "not even an object",
            "unknown-key": {"name": "u", "system": "s", "invented": True},
        }
    )
    source = store_patterns(store)

    found = await source.patterns()

    assert [p.name for p in found] == ["reviewer"]
    assert len(source.skipped) == 3, source.skipped
    assert any("broken" in why for why in source.skipped), source.skipped


async def test_what_was_skipped_is_said_so_a_product_can_show_it(tmp_path: Any) -> None:
    """Skipping silently would make a product debug an agent that simply never appears."""
    source = store_patterns(FakeStore({"broken": {"name": "broken"}}))

    await source.patterns()

    assert source.skipped and "agents/broken" in source.skipped[0], source.skipped


# ------------------------------------------------------------------ and changes nothing that works


def test_the_packaged_library_is_untouched() -> None:
    """A store source is an addition. Every composition reading the shipped patterns behaves
    exactly as it did."""
    packaged = shipped()

    assert "single" in packaged
    assert packaged["single"].system, "the shipped single pattern still has its role"


async def test_a_store_agent_may_shadow_a_shipped_one_by_name(tmp_path: Any) -> None:
    """A product overriding `single` with its own is a thing it is allowed to want; the source
    reports what it has and the registry above decides. This pins that the source does not
    refuse the name."""
    source = store_patterns(FakeStore({"single": {"name": "single", "system": "ours"}}))

    found = await source.patterns()

    assert [p.name for p in found] == ["single"]
    assert found[0].system == "ours"


def test_the_collection_is_named_agents_by_default() -> None:
    assert StorePatterns(FakeStore())._collection == "agents"  # noqa: SLF001 — the default is the contract


# ------------------------------------------------ the registry, which resolves a name to a loop


async def test_the_registry_offers_the_shipped_library_and_the_products_own(tmp_path: Any) -> None:
    from shadow_hdk.adapters.agent.patterns import PatternRegistry

    registry = PatternRegistry((store_patterns(FakeStore({"reviewer": A_REVIEWER})),))

    names = [p.name for p in await registry.all()]

    assert "single" in names, "the shipped library is still there"
    assert "reviewer" in names, "and the product's own beside it"


async def test_a_products_agent_shadows_a_shipped_one_of_the_same_name(tmp_path: Any) -> None:
    """Later shadows earlier, as the skill registry does (D54) — later is closer to the run.

    Paired against the shipped value on purpose. Asserting only that the override wins cannot tell
    *shadowing* from *the shipped library being absent*, and a mutation that dropped the shipped
    library entirely passed the first version of this test.
    """
    from shadow_hdk.adapters.agent.patterns import PatternRegistry

    assert shipped()["single"].system != "OURS", "the shipped one is a different pattern"

    registry = PatternRegistry(
        (store_patterns(FakeStore({"single": {"name": "single", "system": "OURS"}})),)
    )

    found = await registry.named("single")
    everything = {p.name for p in await registry.all()}

    assert found.system == "OURS", "the product's own did not win"
    assert "plan-and-execute" in everything, "and the shipped library is still there beside it"


async def test_an_unknown_name_is_refused_and_says_what_there_is(tmp_path: Any) -> None:
    """D176, at the unit the refusal lives in. A silent fallback hands a product a run that looks
    right and is not."""
    from shadow_hdk.adapters.agent.patterns import NoSuchAgent, PatternRegistry

    registry = PatternRegistry((store_patterns(FakeStore({"reviewer": A_REVIEWER})),))

    with pytest.raises(NoSuchAgent) as refused:
        await registry.named("reviewr")

    assert "reviewr" in str(refused.value), refused.value
    assert "reviewer" in str(refused.value), "it must name what is available"


async def test_find_answers_none_rather_than_raising(tmp_path: Any) -> None:
    """`find` is the asking form and `named` the demanding one; a caller that wants to branch on
    absence should not have to catch."""
    from shadow_hdk.adapters.agent.patterns import PatternRegistry

    registry = PatternRegistry((store_patterns(FakeStore()),))

    assert await registry.find("nobody") is None
    assert (await registry.find("single")) is not None


async def test_the_listing_gives_a_name_and_one_line(tmp_path: Any) -> None:
    """What a product shows a person choosing an agent."""
    from shadow_hdk.adapters.agent.patterns import PatternRegistry

    registry = PatternRegistry(
        (store_patterns(FakeStore({"reviewer": A_REVIEWER})),), include_shipped=False
    )

    listing = await registry.listing()

    assert listing == (
        ("reviewer", "REVIEWER-ROLE: you review a change and say what is wrong with it."),
    ), listing


# ------------------------------------------------------ and a mode names one (D175)


def test_a_mode_document_names_its_agent() -> None:
    """The row a product writes: `agent` beside `policy`. Without this the name never leaves the
    document and a mode silently runs `single` — which is the whole gap this phase closes."""
    from shadow_hdk.adapters.modes.registry import mode_from_document

    spec = mode_from_document(
        {"id": "reviewing", "policy": "workspace-write", "agent": "reviewer"}, source="store"
    )

    assert spec.agent == "reviewer"


def test_a_mode_document_naming_no_agent_leaves_it_empty() -> None:
    """Empty is `single`, which is what every mode was before this phase."""
    from shadow_hdk.adapters.modes.registry import mode_from_document

    spec = mode_from_document({"id": "plain", "policy": "workspace-write"}, source="store")

    assert spec.agent == ""
