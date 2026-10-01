"""A root's instruction files, and a folder of `SKILL.md` (ENH-047, lane P's asks 5 and 11).

Both readers are **optional and composed by a product**. The existing default stays: a governed
Claude Code does not read a folder's instruction files, because a run's instructions should be the
mode's behaviour and not a file somebody left in a folder for a different tool (ENH-012, measured).
What was missing is that the kit never *offered* them either — so a team convention written where
the field writes it reached no provider, and a key-backed model never had them at all.

The difference between offering a convention and obeying an unmarked file is that these come back as
**named, attributable fragments** a product chooses to pass, which is what makes them refusable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.adapters.agent.field_formats import (
    MarkdownSkills,
    root_instructions,
    skill_from_markdown,
)

pytestmark = pytest.mark.anyio


# ------------------------------------------------------------------ a root's instruction files


def test_a_root_with_no_instruction_files_offers_nothing(tmp_path: Path) -> None:
    """The common case, and not an error: most roots have neither file."""
    assert root_instructions(tmp_path) == ()


def test_agents_md_comes_back_named_and_attributable(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("Run the linter before you commit.\n")

    found = root_instructions(tmp_path)

    assert len(found) == 1
    assert found[0].name == "AGENTS.md", "named, so a model knows what it is reading"
    assert tmp_path.name in found[0].source, "attributable, so it can be weighed"
    assert found[0].text == "Run the linter before you commit."


def test_both_files_come_back_in_the_readers_order(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("agents\n")
    (tmp_path / "CLAUDE.md").write_text("claude\n")

    assert [f.name for f in root_instructions(tmp_path)] == ["AGENTS.md", "CLAUDE.md"]


def test_a_caller_may_name_its_own_files(tmp_path: Path) -> None:
    (tmp_path / "HOUSE.md").write_text("tabs, never spaces\n")

    found = root_instructions(tmp_path, names=("HOUSE.md",))

    assert [f.name for f in found] == ["HOUSE.md"]


def test_an_empty_file_is_not_a_fragment(tmp_path: Path) -> None:
    """An empty block of context costs tokens and says nothing."""
    (tmp_path / "AGENTS.md").write_text("\n\n   \n")

    assert root_instructions(tmp_path) == ()


def test_a_file_too_large_is_truncated_and_says_so_rather_than_dropped(tmp_path: Path) -> None:
    """Half a convention beats silence — and silence is what a product would have to debug."""
    (tmp_path / "AGENTS.md").write_text("x" * 100)

    found = root_instructions(tmp_path, limit=50)

    assert len(found) == 1
    assert "truncated" in found[0].text
    assert found[0].text.startswith("x" * 50)


def test_an_unreadable_file_is_skipped_rather_than_fatal(tmp_path: Path) -> None:
    """A convention nobody can read is not a convention, and failing the run over one is worse
    than going without it."""
    (tmp_path / "AGENTS.md").write_bytes(b"\xff\xfe\x00not text")
    (tmp_path / "CLAUDE.md").write_text("this one is fine\n")

    found = root_instructions(tmp_path)

    assert [f.name for f in found] == ["CLAUDE.md"]


# ------------------------------------------------------------------ SKILL.md


def test_front_matter_gives_the_name_and_description_and_the_body_is_the_prompt() -> None:
    skill = skill_from_markdown(
        "---\nname: tidy\ndescription: Tidy a file\n---\n\nRead it, sort it, write it back.\n",
        where="SKILL.md",
    )

    assert skill.name == "tidy"
    assert skill.description == "Tidy a file"
    assert skill.prompt == "Read it, sort it, write it back."


def test_needs_is_read_as_a_list_however_it_is_written() -> None:
    skill = skill_from_markdown(
        "---\nname: tidy\nneeds: read_file, write_file\n---\n\nbody\n", where="SKILL.md"
    )

    assert skill.needs == frozenset({"read_file", "write_file"})


def test_a_skill_with_no_body_is_refused_naming_the_file() -> None:
    with pytest.raises(ValueError, match="no body"):
        skill_from_markdown("---\nname: tidy\n---\n\n\n", where="skills/tidy/SKILL.md")


def test_a_skill_with_no_name_anywhere_is_refused() -> None:
    with pytest.raises(ValueError, match="needs a name"):
        skill_from_markdown("---\ndescription: x\n---\n\nbody\n", where="SKILL.md")


async def test_a_folder_of_skills_is_a_skill_source(tmp_path: Path) -> None:
    """The field's layout: `<dir>/<skill-name>/SKILL.md`."""
    for name in ("tidy", "review"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "SKILL.md").write_text(
            f"---\ndescription: does {name}\n---\n\nthe {name} procedure\n"
        )

    found = await MarkdownSkills(tmp_path).skills()

    assert sorted(s.name for s in found) == ["review", "tidy"]
    assert {s.source for s in found} == {"markdown"}


async def test_a_file_with_no_name_takes_its_directorys(tmp_path: Path) -> None:
    """Which is how the field names them, and what makes an existing folder work unchanged."""
    (tmp_path / "deploy-the-thing").mkdir()
    (tmp_path / "deploy-the-thing" / "SKILL.md").write_text("---\ndescription: d\n---\n\nsteps\n")

    found = await MarkdownSkills(tmp_path).skills()

    assert [s.name for s in found] == ["deploy-the-thing"]


async def test_one_malformed_skill_does_not_take_the_others_down(tmp_path: Path) -> None:
    (tmp_path / "good").mkdir()
    (tmp_path / "good" / "SKILL.md").write_text("---\ndescription: d\n---\n\nsteps\n")
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "SKILL.md").write_text("---\ndescription: d\n---\n\n\n")

    source = MarkdownSkills(tmp_path)
    found = await source.skills()

    assert [s.name for s in found] == ["good"]
    assert source.skipped and "bad" in source.skipped[0], source.skipped


async def test_a_directory_that_is_not_there_is_no_skills_rather_than_a_crash(
    tmp_path: Path,
) -> None:
    assert await MarkdownSkills(tmp_path / "nowhere").skills() == ()


async def test_it_plugs_into_the_registry_beside_the_other_sources(tmp_path: Path) -> None:
    """The point of being a `SkillSource`: later shadows earlier, on the record (D54), and this
    takes its turn in that order like any other source."""
    from shadow_hdk.adapters.agent.registry import SkillRegistry

    (tmp_path / "tidy").mkdir()
    (tmp_path / "tidy" / "SKILL.md").write_text("---\ndescription: d\n---\n\nthe procedure\n")

    registry = SkillRegistry((MarkdownSkills(tmp_path),))
    found = await registry.all()

    assert [s.name for s in found] == ["tidy"]
