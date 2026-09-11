"""Skills are a registry, not a directory the host hands one file from (Phase 24, D54).

Three sources — shipped as TOML, minted during a run, kept by the host — under one registry the
agent lists by name and line. A skill says what it is for, because a skill nobody can find is a
file; and it says where it came from, because a procedure a model wrote mid-run and a procedure a
team reviewed are different kinds of claim, and the record has to tell them apart.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from shadow_hdk.adapters.agent import Skill, load_skill
from shadow_hdk.adapters.agent.registry import (
    DirectorySkills,
    MintedSkills,
    SkillRegistry,
    shipped_skills,
)

pytestmark = pytest.mark.anyio

CAREFUL = '''
name = "look-before-you-change"
description = "Read what is there before writing anything; say what will change and why."
needs = ["read_file"]
prompt = """
Before any write, read the file you will change and name what you are about to change.
"""
'''


def a_file(where: Path, name: str, body: str) -> Path:
    where.mkdir(parents=True, exist_ok=True)
    made = where / f"{name}.toml"
    made.write_text(body.strip() + "\n", encoding="utf-8")
    return made


# ------------------------------------------------------------------ a skill says what it is for


def test_a_skill_in_a_registry_says_what_it_is_for(tmp_path: Path) -> None:
    skill = load_skill(a_file(tmp_path, "careful", CAREFUL))

    assert skill.description.startswith("Read what is there")
    assert skill.source == "file"


def test_a_skill_file_with_no_line_is_refused(tmp_path: Path) -> None:
    """The line is what the model chooses by. A body alone is a prompt, not a registry entry."""
    body = 'name = "x"\nprompt = "do it"\n'
    with pytest.raises(ValueError, match="description"):
        load_skill(a_file(tmp_path, "bad", body))


def test_a_skill_made_in_code_needs_no_line() -> None:
    """A host that constructs a `Skill` and hands it to one agent — Phase 8's shape — works."""
    assert Skill(name="s", prompt="p").description == ""
    assert Skill(name="s", prompt="p").source == "handed"


# ------------------------------------------------------------------ three sources, one registry


async def test_a_directory_is_a_source_and_says_so(tmp_path: Path) -> None:
    a_file(tmp_path / "skills", "careful", CAREFUL)
    a_file(tmp_path / "skills", "other", CAREFUL.replace("look-before-you-change", "other"))
    (tmp_path / "skills" / "notes.txt").write_text("not a skill")

    found = await DirectorySkills(tmp_path / "skills", source="team").skills()

    assert sorted(s.name for s in found) == ["look-before-you-change", "other"]
    assert {s.source for s in found} == {"team"}


async def test_minted_skills_start_empty_and_remember_what_was_minted() -> None:
    minted = MintedSkills()
    assert await minted.skills() == ()

    minted.add(Skill(name="triage", description="Sort by urgency.", prompt="…"))

    (found,) = await minted.skills()
    assert found.source == "minted"


async def test_the_registry_lists_names_and_lines_and_finds_by_name(tmp_path: Path) -> None:
    a_file(tmp_path / "skills", "careful", CAREFUL)
    minted = MintedSkills()
    minted.add(Skill(name="triage", description="Sort by urgency.", prompt="Sort them."))
    registry = SkillRegistry((DirectorySkills(tmp_path / "skills"), minted))

    listing = await registry.listing()
    assert listing == (
        (
            "look-before-you-change",
            "Read what is there before writing anything; say what will change and why.",
        ),
        ("triage", "Sort by urgency."),
    )
    found = await registry.find("triage")
    assert found is not None and found.prompt == "Sort them."
    assert await registry.find("nothing-called-this") is None


async def test_a_later_source_shadows_an_earlier_one_and_the_registry_says_so(
    tmp_path: Path,
) -> None:
    """A team's version of a shipped skill wins, and a minted one wins over both — later is
    closer to the run. Silent shadowing would be a skill changing under the model's feet with
    nothing on the record, so the registry keeps what was shadowed."""
    a_file(tmp_path / "a", "careful", CAREFUL)
    a_file(tmp_path / "b", "careful", CAREFUL.replace("Read what is there", "The team's version:"))
    registry = SkillRegistry(
        (
            DirectorySkills(tmp_path / "a", source="shipped"),
            DirectorySkills(tmp_path / "b", source="team"),
        )
    )

    found = await registry.find("look-before-you-change")
    assert found is not None and found.source == "team"
    assert [(s.name, s.source) for s in await registry.shadowed()] == [
        ("look-before-you-change", "shipped")
    ]


# ------------------------------------------------------------------ shipped, and generic


async def test_the_shipped_library_is_small_generic_and_says_what_each_is_for() -> None:
    found = await shipped_skills().skills()

    assert 2 <= len(found) <= 8, "a shipped library is a starting point, not a corpus"
    for skill in found:
        assert skill.description and skill.source == "shipped"
        text = f"{skill.name} {skill.description} {skill.prompt}".lower()
        for word in ("python", "typescript", "git ", "compile", "unit test", "pull request"):
            assert word not in text, f"{skill.name!r} is about code; the harness is not"
