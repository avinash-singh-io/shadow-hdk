"""The cap on a change, and the four ways the truth about one can be awkward (ENH-044, D154/D155).

A record that carries content has to say what it left out, or a host reads a short diff as a small
change. And it must never be the reason a write fails: the act the mode admitted and the person
approved happens, and the record says what it could not capture.

The awkward cases, each its own test:

* a diff bigger than the cap — cut, said so, and the counts still exact
* a prior state that is not text — marked, not guessed at as empty
* a prior state that cannot be read at all — the write still happens (D155)
* an act with no content delta at all (a move) — no change block, because `from`/`to` already say
  the whole of what happened and a diff of nothing is noise
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.environment.local import LocalEnvironment
from shadow_hdk.kernel import Completed, Refused
from shadow_hdk.runtime.environment import CHANGE_DIFF_BYTES, changed

pytestmark = pytest.mark.anyio


async def _invoke(root: Path, what: str, inputs: dict[str, Any]) -> Any:
    environment = await LocalEnvironment.open(root, mode="workspace-write")
    try:
        return await environment.invoke(what, inputs)
    finally:
        await environment.close()


def change_of(observation: Any) -> dict[str, Any]:
    assert isinstance(observation, Completed), observation
    assert isinstance(observation.output, dict), observation.output
    got = observation.output.get("change")
    assert isinstance(got, dict), f"no change block on {observation.output!r}"
    return got


# ------------------------------------------------------------------ the same shape for an edit


async def test_an_edit_carries_the_same_change_block_as_a_write(tmp_path: Path) -> None:
    """Four write-class operations, one shape. A panel that reads one shape for three of them and
    a different one for the fourth is a panel with a bug waiting in it."""
    (tmp_path / "names.txt").write_text("alpha\nbeta\n")

    told = await _invoke(
        tmp_path, "edit_file", {"path": "names.txt", "edits": [{"old": "beta", "new": "gamma"}]}
    )

    change = change_of(told)
    assert "-beta" in change["diff"] and "+gamma" in change["diff"], change["diff"]
    assert change["added"] == 1 and change["removed"] == 1, change
    assert change["created"] is False and change["deleted"] is False, change


async def test_a_refused_edit_carries_no_change_because_nothing_was_written(
    tmp_path: Path,
) -> None:
    (tmp_path / "names.txt").write_text("alpha\nbeta\n")

    told = await _invoke(
        tmp_path, "edit_file", {"path": "names.txt", "edits": [{"old": "absent", "new": "x"}]}
    )

    assert isinstance(told, Refused), told
    assert (tmp_path / "names.txt").read_text() == "alpha\nbeta\n", "and the file is untouched"


async def test_a_move_says_what_moved_and_claims_no_content_change(tmp_path: Path) -> None:
    """A move is the one write-class act with no content delta at all. `from` and `to` are the
    whole story, so there is no change block — a zero diff would read as *nothing happened*."""
    (tmp_path / "old.txt").write_text("alpha\n")

    told = await _invoke(tmp_path, "move_file", {"from": "old.txt", "to": "new.txt"})

    assert isinstance(told, Completed) and isinstance(told.output, dict)
    assert told.output == {"from": "old.txt", "to": "new.txt"}, told.output
    assert (tmp_path / "new.txt").read_text() == "alpha\n"


# ------------------------------------------------------------------ the cap


async def test_a_diff_past_the_cap_is_cut_and_says_so(tmp_path: Path) -> None:
    (tmp_path / "big.txt").write_text("".join(f"line {n}\n" for n in range(4000)))

    told = await _invoke(
        tmp_path,
        "write_file",
        {"path": "big.txt", "content": "".join(f"LINE {n}\n" for n in range(4000))},
    )

    change = change_of(told)
    assert change["truncated"] is True, change
    assert len(change["diff"]) <= CHANGE_DIFF_BYTES, len(change["diff"])


async def test_the_counts_stay_exact_when_the_diff_is_cut(tmp_path: Path) -> None:
    """The reason the counts are computed before the cut. A host reading a truncated diff still
    learns the true size of what happened; a count taken from the cut text would understate it."""
    (tmp_path / "big.txt").write_text("".join(f"line {n}\n" for n in range(4000)))

    told = await _invoke(
        tmp_path,
        "write_file",
        {"path": "big.txt", "content": "".join(f"LINE {n}\n" for n in range(4000))},
    )

    change = change_of(told)
    assert change["truncated"] is True
    assert change["added"] == 4000, change["added"]
    assert change["removed"] == 4000, change["removed"]


async def test_a_change_under_the_cap_is_whole(tmp_path: Path) -> None:
    """The pair that keeps the above honest: if everything were truncated, both would pass."""
    (tmp_path / "small.txt").write_text("alpha\n")

    told = await _invoke(tmp_path, "write_file", {"path": "small.txt", "content": "beta\n"})

    assert change_of(told)["truncated"] is False


def test_the_cap_is_one_named_constant() -> None:
    """A cap written into three call sites is three caps, and the first one somebody tunes is the
    one they can find."""
    assert changed("x", "a\n" * 9000, "b\n" * 9000)["truncated"] is True
    assert changed("x", "a\n" * 9000, "b\n" * 9000, cap=10_000_000)["truncated"] is False


# ------------------------------------------------------------------ a prior state that is not text


async def test_a_prior_state_that_is_not_text_is_marked_rather_than_guessed_at(
    tmp_path: Path,
) -> None:
    """Reading it as empty would make the change claim the whole new file was added, which is a
    lie about a file that already had something in it."""
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00\x01binary")

    told = await _invoke(tmp_path, "write_file", {"path": "blob.bin", "content": "now text\n"})

    change = change_of(told)
    assert change["before_unreadable"] is True, change
    assert change["added"] is None, "a count nobody could measure must not read as a number"
    assert change["removed"] is None, change
    assert change["created"] is False, "it existed; it just could not be read"


async def test_a_write_over_an_unreadable_prior_state_still_happens(tmp_path: Path) -> None:
    """D155. A write that failed because the record-keeping failed would be the tail wagging the
    dog — the act the mode admitted and the person approved must still happen."""
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00\x01binary")

    told = await _invoke(tmp_path, "write_file", {"path": "blob.bin", "content": "now text\n"})

    assert isinstance(told, Completed), told
    assert (tmp_path / "blob.bin").read_text() == "now text\n", "the write landed"


async def test_deleting_something_unreadable_still_happens_and_says_what_it_could_not_read(
    tmp_path: Path,
) -> None:
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00\x01binary")

    told = await _invoke(tmp_path, "delete_file", {"path": "blob.bin"})

    change = change_of(told)
    assert change["deleted"] is True and change["before_unreadable"] is True, change
    assert not (tmp_path / "blob.bin").exists(), "the delete landed"


# ------------------------------------------------------------------ the builder, without a disk


def test_the_builder_is_pure_over_two_strings() -> None:
    """So every environment says the same thing about a change — a local root, a sandbox and a
    remote one — and so this is testable without a filesystem at all."""
    change = changed("x.txt", "a\nb\n", "a\nc\n")

    assert change["added"] == 1 and change["removed"] == 1
    diff = change["diff"]
    assert isinstance(diff, str)
    assert "-b" in diff and "+c" in diff
    assert change["created"] is False and change["deleted"] is False
    assert change["before_unreadable"] is False
    assert change["truncated"] is False
