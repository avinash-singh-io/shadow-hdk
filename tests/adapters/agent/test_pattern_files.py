"""A pattern is a file, and a team writes one the same way we do (D17).

`09` §5: *the framework ships a small set and a team adds its own **the same way it adds a skill**.
Nothing in the runtime knows the names.* A dataclass in a module satisfies the second half and fails
the first — adding a pattern would mean editing the package. So the shipped patterns are files, and
`load_pattern` is the same call for ours and for anybody's.

The loader's errors are for a **person**, because a pattern file is something a person edits. Each
kind of mistake is refused by name rather than by a traceback about a dict.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from shadow_hdk.adapters.agent import Pattern, load_pattern, shipped

SHIPPED = {
    "single",
    "plan-and-execute",
    "orchestrator-workers",
    "critic-pair",
    "reflect-until",
    "keeps-helpers",
}


def test_the_framework_ships_its_patterns_as_files() -> None:
    found = shipped()
    assert set(found) == SHIPPED
    assert all(isinstance(pattern, Pattern) for pattern in found.values())


def test_every_shipped_pattern_has_a_role_worth_reading() -> None:
    """A pattern with an empty role is a pattern that decides nothing."""
    for name, pattern in shipped().items():
        assert pattern.name == name
        assert len(pattern.system.strip()) > 80, f"{name} has no role to speak of"


def test_a_teams_own_file_loads_by_the_same_call(tmp_path: Path) -> None:
    """The whole claim of `09` §5. Nothing about this file is ours."""
    written = tmp_path / "house-style.toml"
    written.write_text(
        "\n".join(
            [
                'name = "house-style"',
                'system = """',
                "You are the house reviewer. Read what is proposed and say what is wrong with it,",
                "then say what you would keep.",
                '"""',
                'meta_tools = ["propose", "done"]',
                "max_turns = 4",
                "",
            ]
        )
    )
    pattern = load_pattern(written)
    assert pattern.name == "house-style"
    assert pattern.max_turns == 4
    assert pattern.meta_tools == frozenset({"propose", "done"})
    assert "house reviewer" in pattern.system


@pytest.mark.parametrize(
    ("body", "says"),
    [
        ('name = "x"\nsystem = "s"\nmeta_tools = ["fly"]\n', "fly"),
        ('name = "x"\nsystem = "s"\nmax_turnz = 3\n', "max_turnz"),
        ('system = "s"\n', "name"),
        ('name = "x"\n', "system"),
    ],
    ids=["unknown meta-tool", "unknown key", "no name", "no role"],
)
def test_a_bad_pattern_file_is_refused_by_name(tmp_path: Path, body: str, says: str) -> None:
    """Refused *and told which word is wrong* — the reader is the person who wrote the file."""
    written = tmp_path / "bad.toml"
    written.write_text(body)
    with pytest.raises(ValueError) as refused:
        load_pattern(written)
    message = str(refused.value)
    assert says in message, message
    # And **which file**. `Pattern.__post_init__` already refuses an unknown meta-tool; what the
    # loader adds is the path, so a team with a directory of them knows which one to open.
    assert "bad.toml" in message, message


def test_the_file_name_is_not_the_pattern_name(tmp_path: Path) -> None:
    """The name is in the file. A pattern renamed by moving it is a pattern that cannot be cited."""
    written = tmp_path / "whatever.toml"
    written.write_text('name = "critic"\nsystem = "You criticise, at length, and with feeling."\n')
    assert load_pattern(written).name == "critic"
