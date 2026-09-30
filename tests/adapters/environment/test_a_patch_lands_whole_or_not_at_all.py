"""A patch is one act across many files, or it is nothing (ENH-042, D158/D159).

Lane P confirmed this costs them: refactors touch many files at once, and until now every one was a
separate `edit_file` — so a refactor that failed on its fourth file left three files changed and a
workspace no record describes. That is the failure `edit_file` already refuses *within* one file
(an absent `old`, an ambiguous one), multiplied by the number of files in the batch.

D158: the vocabulary is `edit_file`'s — a list of `{path, edits: [{old, new}]}` — not a diff format
the kit parses. `Dialect` refuses to become a query language for the same reason, and every refusal
`edit_file` already has carries over unchanged rather than being rewritten for a parser.

D159: **read all, validate all, write all.** Nothing is written until every edit in the batch is
known to apply, because atomicity is the whole of what makes this different from a loop.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.environment.local import LocalEnvironment
from shadow_hdk.kernel import Completed, Refused

pytestmark = pytest.mark.anyio


async def _invoke(root: Path, what: str, inputs: dict[str, Any]) -> Any:
    environment = await LocalEnvironment.open(root, mode="workspace-write")
    try:
        return await environment.invoke(what, inputs)
    finally:
        await environment.close()


def _two_files(root: Path) -> None:
    (root / "a.py").write_text("def one():\n    return OLD\n")
    (root / "b.py").write_text("from a import one\n\nprint(OLD)\n")


# ------------------------------------------------------------------ it lands whole


async def test_a_patch_changes_every_file_it_names(tmp_path: Path) -> None:
    _two_files(tmp_path)

    told = await _invoke(
        tmp_path,
        "apply_patch",
        {
            "files": [
                {"path": "a.py", "edits": [{"old": "OLD", "new": "NEW"}]},
                {"path": "b.py", "edits": [{"old": "OLD", "new": "NEW"}]},
            ]
        },
    )

    assert isinstance(told, Completed), told
    assert (tmp_path / "a.py").read_text() == "def one():\n    return NEW\n"
    assert (tmp_path / "b.py").read_text() == "from a import one\n\nprint(NEW)\n"


async def test_a_patch_carries_a_change_for_each_file(tmp_path: Path) -> None:
    """Phase 59's block, per file — so a files-changed panel reads one shape for a patch too."""
    _two_files(tmp_path)

    told = await _invoke(
        tmp_path,
        "apply_patch",
        {
            "files": [
                {"path": "a.py", "edits": [{"old": "OLD", "new": "NEW"}]},
                {"path": "b.py", "edits": [{"old": "OLD", "new": "NEW"}]},
            ]
        },
    )

    assert isinstance(told, Completed) and isinstance(told.output, dict)
    changes = told.output["changed"]
    assert isinstance(changes, list) and len(changes) == 2, changes
    for one in changes:
        assert isinstance(one, dict)
        assert one["path"] in ("a.py", "b.py")
        change = one["change"]
        assert isinstance(change, dict)
        assert change["added"] == 1 and change["removed"] == 1, change


# ------------------------------------------------------------------ or not at all


async def test_an_absent_old_in_the_last_file_leaves_every_earlier_file_untouched(
    tmp_path: Path,
) -> None:
    """D159, and the property measured from the filesystem rather than trusted from the refusal."""
    _two_files(tmp_path)
    before_a = (tmp_path / "a.py").read_text()
    before_b = (tmp_path / "b.py").read_text()

    told = await _invoke(
        tmp_path,
        "apply_patch",
        {
            "files": [
                {"path": "a.py", "edits": [{"old": "OLD", "new": "NEW"}]},
                {"path": "b.py", "edits": [{"old": "NOT THERE", "new": "NEW"}]},
            ]
        },
    )

    assert isinstance(told, Refused), told
    assert "b.py" in told.reason, told.reason
    assert (tmp_path / "a.py").read_text() == before_a, "the first file was written and should not"
    assert (tmp_path / "b.py").read_text() == before_b


async def test_an_ambiguous_old_refuses_the_whole_patch_naming_the_count(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("OLD\nOLD\n")
    (tmp_path / "b.py").write_text("fine\n")

    told = await _invoke(
        tmp_path,
        "apply_patch",
        {
            "files": [
                {"path": "b.py", "edits": [{"old": "fine", "new": "ok"}]},
                {"path": "a.py", "edits": [{"old": "OLD", "new": "NEW"}]},
            ]
        },
    )

    assert isinstance(told, Refused), told
    assert "2 times" in told.reason or "twice" in told.reason, told.reason
    assert (tmp_path / "b.py").read_text() == "fine\n", "nothing was written"


async def test_a_missing_file_refuses_the_whole_patch(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("OLD\n")

    told = await _invoke(
        tmp_path,
        "apply_patch",
        {
            "files": [
                {"path": "a.py", "edits": [{"old": "OLD", "new": "NEW"}]},
                {"path": "gone.py", "edits": [{"old": "x", "new": "y"}]},
            ]
        },
    )

    assert isinstance(told, Refused), told
    assert (tmp_path / "a.py").read_text() == "OLD\n"


# ------------------------------------------------------------------ the shape of the ask


async def test_an_empty_patch_is_refused(tmp_path: Path) -> None:
    told = await _invoke(tmp_path, "apply_patch", {"files": []})

    assert isinstance(told, Refused), told


async def test_the_same_file_twice_is_refused_rather_than_applied_twice(tmp_path: Path) -> None:
    """Two entries for one path is a caller who has lost track of their own batch. Applying both
    in order would work by accident and hide the mistake; naming it does not."""
    (tmp_path / "a.py").write_text("one\ntwo\n")

    told = await _invoke(
        tmp_path,
        "apply_patch",
        {
            "files": [
                {"path": "a.py", "edits": [{"old": "one", "new": "1"}]},
                {"path": "a.py", "edits": [{"old": "two", "new": "2"}]},
            ]
        },
    )

    assert isinstance(told, Refused), told
    assert "a.py" in told.reason
    assert (tmp_path / "a.py").read_text() == "one\ntwo\n"


async def test_a_patch_is_withheld_in_a_read_only_environment(tmp_path: Path) -> None:
    """Before governance is asked, like every other write — a mode is the environment's own
    promise and not one it outsources."""
    (tmp_path / "a.py").write_text("OLD\n")
    environment = await LocalEnvironment.open(tmp_path, mode="read-only")
    try:
        told = await environment.invoke(
            "apply_patch", {"files": [{"path": "a.py", "edits": [{"old": "OLD", "new": "NEW"}]}]}
        )
    finally:
        await environment.close()

    assert isinstance(told, Refused), told
    assert (tmp_path / "a.py").read_text() == "OLD\n"
