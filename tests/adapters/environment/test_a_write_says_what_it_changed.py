"""A write-class act says what it changed, so a host never reads the disk to find out (ENH-044).

Lane P's asks 1 and 7. `write_file` recorded `{"path", "bytes"}` and `delete_file` the path, and
`EffectRecorded` carries a digest and a free `detail` — no content anywhere. So a host showing a
files-changed panel or an approval preview had to read the environment's root itself, which lane P
does. That races the agent, it makes the record a weaker account of the run than the filesystem, and
— the reason this is a primitive rather than a nicety — **it cannot work at all** for a contained or
remote environment where the host has no such access.

D154: a bounded unified diff, with exact line counts beside it that stay exact when the diff is cut.
Lane P settled the shape — content to a cap, `truncated` past it, and no per-file version history,
because git keeps that for a repository.

D155: capturing it never fails the write. A write that fails because the record-keeping failed is
the tail wagging the dog.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.environment.local import LocalEnvironment
from shadow_hdk.kernel import Completed

pytestmark = pytest.mark.anyio


async def _invoke(root: Path, what: str, inputs: dict[str, Any]) -> Any:
    environment = await LocalEnvironment.open(root, mode="workspace-write")
    try:
        return await environment.invoke(what, inputs)
    finally:
        await environment.close()


def change_of(observation: Any) -> dict[str, Any]:
    assert isinstance(observation, Completed), observation
    value = observation.output
    assert isinstance(value, dict), value
    got = value.get("change")
    assert isinstance(got, dict), f"no change block on {value!r}"
    return got


# ------------------------------------------------------------------ a write over an existing file


async def test_a_write_over_an_existing_file_carries_a_diff_of_the_change(tmp_path: Path) -> None:
    (tmp_path / "names.txt").write_text("alpha\nbeta\n")

    told = await _invoke(tmp_path, "write_file", {"path": "names.txt", "content": "alpha\ngamma\n"})

    change = change_of(told)
    assert "-beta" in change["diff"], change["diff"]
    assert "+gamma" in change["diff"], change["diff"]


async def test_the_line_counts_are_exact(tmp_path: Path) -> None:
    (tmp_path / "names.txt").write_text("a\nb\nc\n")

    told = await _invoke(tmp_path, "write_file", {"path": "names.txt", "content": "a\nB\nc\nd\n"})

    change = change_of(told)
    assert change["added"] == 2, change  # B and d
    assert change["removed"] == 1, change  # b


async def test_a_write_that_changes_nothing_says_so(tmp_path: Path) -> None:
    """An agent rewriting a file with what was already in it is a real and common act. The record
    should say the file did not move rather than imply it did."""
    (tmp_path / "names.txt").write_text("alpha\n")

    told = await _invoke(tmp_path, "write_file", {"path": "names.txt", "content": "alpha\n"})

    change = change_of(told)
    assert change["added"] == 0 and change["removed"] == 0, change
    assert change["diff"] == "", change


# ------------------------------------------------------------------ creating, and deleting


async def test_creating_a_file_is_marked_created_and_is_all_additions(tmp_path: Path) -> None:
    told = await _invoke(tmp_path, "write_file", {"path": "new.txt", "content": "one\ntwo\n"})

    change = change_of(told)
    assert change["created"] is True, change
    assert change["deleted"] is False, change
    assert change["added"] == 2 and change["removed"] == 0, change
    assert "+one" in change["diff"] and "+two" in change["diff"]


async def test_a_delete_carries_what_was_removed(tmp_path: Path) -> None:
    """The one where the call's own inputs say nothing at all: `delete_file` records a path, and
    the content it destroyed was on no record anywhere."""
    (tmp_path / "gone.txt").write_text("one\ntwo\n")

    told = await _invoke(tmp_path, "delete_file", {"path": "gone.txt"})

    change = change_of(told)
    assert change["deleted"] is True, change
    assert change["created"] is False, change
    assert change["removed"] == 2 and change["added"] == 0, change
    assert "-one" in change["diff"] and "-two" in change["diff"]


# ------------------------------------------------------------------ nothing that was there moved


async def test_the_existing_result_keys_are_untouched(tmp_path: Path) -> None:
    """Contract additions only: everything lane P reads today keeps its place and its meaning."""
    (tmp_path / "names.txt").write_text("alpha\n")

    wrote = await _invoke(tmp_path, "write_file", {"path": "names.txt", "content": "beta\n"})
    removed = await _invoke(tmp_path, "delete_file", {"path": "names.txt"})

    assert isinstance(wrote, Completed) and isinstance(wrote.output, dict)
    assert wrote.output["path"] == "names.txt"
    assert wrote.output["bytes"] == len("beta\n")
    assert isinstance(removed, Completed) and isinstance(removed.output, dict)
    assert removed.output["deleted"] == "names.txt"


async def test_a_read_carries_no_change_because_it_changed_nothing(tmp_path: Path) -> None:
    (tmp_path / "names.txt").write_text("alpha\n")

    told = await _invoke(tmp_path, "read_file", {"path": "names.txt"})

    assert isinstance(told, Completed)
    assert not (isinstance(told.output, dict) and "change" in told.output), told.output


# ------------------------------------------------------------------ and it agrees with the disk


async def test_the_change_agrees_with_what_the_filesystem_actually_holds(tmp_path: Path) -> None:
    """The property that matters. A record agreeing with itself proves nothing; this replays the
    diff's own claim against the bytes on disk."""
    (tmp_path / "names.txt").write_text("alpha\nbeta\ngamma\n")

    told = await _invoke(
        tmp_path, "write_file", {"path": "names.txt", "content": "alpha\ndelta\ngamma\n"}
    )

    change = change_of(told)
    on_disk = (tmp_path / "names.txt").read_text()
    assert on_disk == "alpha\ndelta\ngamma\n"
    for line in change["diff"].splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            assert line[1:] in on_disk, f"the diff added {line[1:]!r}; the file has not got it"
        if line.startswith("-") and not line.startswith("---"):
            assert line[1:] not in on_disk, f"the diff removed {line[1:]!r}; it is still there"
