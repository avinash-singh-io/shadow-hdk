"""Search and ranged reads, as governed operations (ENH-041).

A governed CLI runs with its own built-ins off, so the environment's operations are the whole of
what it can do. With six of them — whole-file read, list, whole-file write, delete, shell, python —
a governed Claude Code is *weaker* than the same CLI on its own, and lane P measured how: every
search becomes a `run_shell`, which under `ask` stops a person on what is a read; and every look at
a large file arrives whole, so the context floods.

These three close that, and they are deliberately the **read-class** half: `glob` and `grep` derive
from `list` and `read`, so their profiles carry no writes and the shipped `ask` mode does not
interrupt a person for them. A search that asks permission is a search nobody runs.

Two rules they are held to, because a tool that lies quietly is worse than one that refuses:

- **Every cap is announced.** A result trimmed to its limit says so, in the result, so a model
  reads "there are more" rather than inferring "there are none".
- **A range past the end is refused, naming what is there** — never silently empty, which reads to
  a model exactly like a file with nothing in it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.kernel import Completed, Refused

pytestmark = pytest.mark.anyio


async def _env(root: Path, mode: Any = "full") -> Any:
    return await LocalEnvironment.open(root, mode=mode)


def _tree(root: Path) -> None:
    (root / "src" / "deep").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "src" / "a.py").write_text("import os\ndef go():\n    return 1\n")
    (root / "src" / "b.py").write_text("def stop():\n    return 0\n")
    (root / "src" / "deep" / "c.py").write_text("# nothing here\n")
    (root / "docs" / "notes.md").write_text("go is the entry point\n")
    (root / "top.txt").write_text("plain\n")


async def _call(env: Any, name: str, args: dict[str, Any]) -> Any:
    return await env.invoke(name, args)


# ------------------------------------------------------------------------------- glob


async def test_glob_finds_files_recursively(tmp_path: Path) -> None:
    _tree(tmp_path)
    env = await _env(tmp_path)

    found = await _call(env, "glob", {"pattern": "**/*.py"})

    assert isinstance(found, Completed)
    assert found.output == ["src/a.py", "src/b.py", "src/deep/c.py"], "sorted, relative, files only"


async def test_glob_takes_a_plain_pattern_and_a_starting_path(tmp_path: Path) -> None:
    _tree(tmp_path)
    env = await _env(tmp_path)

    assert (await _call(env, "glob", {"pattern": "*.py", "path": "src"})).output == [
        "src/a.py",
        "src/b.py",
    ], "relative to the root, not to the starting path — one vocabulary for paths"


async def test_glob_names_no_directories(tmp_path: Path) -> None:
    """`list_dir` is how you see directories. A glob that returned them would make every result
    something the caller has to re-check before reading."""
    _tree(tmp_path)
    env = await _env(tmp_path)

    assert (await _call(env, "glob", {"pattern": "*"})).output == ["top.txt"]


async def test_glob_says_when_it_stopped_at_its_limit(tmp_path: Path) -> None:
    (tmp_path / "many").mkdir()
    for i in range(12):
        (tmp_path / "many" / f"f{i:03}.txt").write_text("x")
    env = await _env(tmp_path)

    found = await _call(env, "glob", {"pattern": "many/*.txt", "limit": 5})

    trimmed: Any = found.output
    assert isinstance(trimmed, dict), "a trimmed result is not a list pretending to be whole"
    assert trimmed["paths"] == [f"many/f{i:03}.txt" for i in range(5)]
    assert trimmed["truncated"] is True
    assert trimmed["found"] == 12, "and it says how many there were"


# ------------------------------------------------------------------------------- grep


async def test_grep_gives_the_path_the_line_number_and_the_line(tmp_path: Path) -> None:
    _tree(tmp_path)
    env = await _env(tmp_path)

    found = await _call(env, "grep", {"pattern": "return"})

    assert found.output == [
        {"path": "src/a.py", "line": 3, "text": "    return 1"},
        {"path": "src/b.py", "line": 2, "text": "    return 0"},
    ]


async def test_grep_is_a_regular_expression(tmp_path: Path) -> None:
    _tree(tmp_path)
    env = await _env(tmp_path)

    found = await _call(env, "grep", {"pattern": r"^def \w+\(\):"})

    hits: Any = found.output
    assert [m["path"] for m in hits] == ["src/a.py", "src/b.py"]


async def test_grep_narrows_to_a_glob(tmp_path: Path) -> None:
    _tree(tmp_path)
    env = await _env(tmp_path)

    found = await _call(env, "grep", {"pattern": "go", "glob": "**/*.md"})

    hits: Any = found.output
    assert [m["path"] for m in hits] == ["docs/notes.md"]


async def test_grep_skips_what_it_cannot_read_rather_than_failing(tmp_path: Path) -> None:
    """One unreadable file in a tree must not lose the matches in every other file."""
    _tree(tmp_path)
    (tmp_path / "src" / "blob.py").write_bytes(b"\x00\x01\x02\xff\xfe")
    env = await _env(tmp_path)

    found = await _call(env, "grep", {"pattern": "return"})

    assert isinstance(found, Completed)
    hits: Any = found.output
    assert [m["path"] for m in hits] == ["src/a.py", "src/b.py"]


async def test_grep_says_when_it_stopped_at_its_limit(tmp_path: Path) -> None:
    (tmp_path / "big.txt").write_text("".join(f"hit {i}\n" for i in range(20)))
    env = await _env(tmp_path)

    found = await _call(env, "grep", {"pattern": "hit", "limit": 4})

    trimmed: Any = found.output
    assert isinstance(trimmed, dict)
    assert len(trimmed["matches"]) == 4
    assert trimmed["truncated"] is True


async def test_grep_finding_nothing_is_an_empty_list_not_a_refusal(tmp_path: Path) -> None:
    _tree(tmp_path)
    env = await _env(tmp_path)

    found = await _call(env, "grep", {"pattern": "nowhere-in-this-tree"})

    assert isinstance(found, Completed) and found.output == []


async def test_a_bad_regular_expression_is_refused_by_name(tmp_path: Path) -> None:
    _tree(tmp_path)
    env = await _env(tmp_path)

    found = await _call(env, "grep", {"pattern": "("})

    assert isinstance(found, Refused) and "(" in found.reason


# ------------------------------------------------------------------ read_file, ranged


async def test_read_file_takes_an_offset_and_a_limit_in_lines(tmp_path: Path) -> None:
    (tmp_path / "long.txt").write_text("".join(f"line {i}\n" for i in range(1, 11)))
    env = await _env(tmp_path)

    read = await _call(env, "read_file", {"path": "long.txt", "offset": 3, "limit": 2})

    # offset is a 1-based line number, as the field spells it
    assert read.output == "line 3\nline 4\n"


async def test_read_file_without_a_range_is_exactly_what_it_always_was(tmp_path: Path) -> None:
    """The whole file, as a plain string. Nothing that reads `read_file` today changes."""
    (tmp_path / "long.txt").write_text("a\nb\nc\n")
    env = await _env(tmp_path)

    assert (await _call(env, "read_file", {"path": "long.txt"})).output == "a\nb\nc\n"


async def test_a_range_past_the_end_is_refused_naming_what_is_there(tmp_path: Path) -> None:
    (tmp_path / "short.txt").write_text("one\ntwo\n")
    env = await _env(tmp_path)

    read = await _call(env, "read_file", {"path": "short.txt", "offset": 50})

    assert isinstance(read, Refused) and "2" in read.reason, "silently empty reads as an empty file"


# --------------------------------------------------- what makes them worth having: read-class


async def test_all_three_are_read_class_so_an_asking_mode_does_not_stop_them(
    tmp_path: Path,
) -> None:
    """The whole point. A search that asks a person for permission is a search nobody runs."""
    env = await _env(tmp_path)

    by_id = {r.id: r for r in await env.registrations()}

    for name in ("glob", "grep", "read_file"):
        effects = by_id[name].component.effects
        assert not effects.writes.names, f"{name} writes nothing"
        assert not effects.reaches, f"{name} reaches nothing"
        assert not effects.costs, f"{name} costs nothing"


async def test_they_are_offered_in_a_read_only_environment(tmp_path: Path) -> None:
    env = await _env(tmp_path, mode="read-only")

    offered = {r.id for r in await env.registrations()}

    assert {"glob", "grep", "read_file"} <= offered
    assert "write_file" not in offered, "and the write half is still withheld"
