"""An edit names a region, and a move is a move (ENH-042, in part).

With `write_file` as the only way to change anything, a governed agent rewrites the whole file to
alter one line. Lane P measured the cost inside their app: it is slow, it is expensive, and on a
large file the model drops content it never meant to touch — the file comes back shorter and
nobody notices until later.

Two operations close that, and the rules they are held to are all about **what a failure leaves
behind**:

- An edit that cannot be applied exactly leaves the file **untouched**. A half-applied edit is
  worse than none: the file is then in a state neither the model nor the record describes.
- An edit whose `old` appears twice is **refused, naming the count**, not applied to the first
  match. Silently taking the first is how an agent edits the wrong line and reports success.
- A move onto a path that exists is **refused, naming it**. That refusal is what keeps a move
  honestly `write`-class — reversible, because you can move it back. Clobbering would destroy
  content with no record anywhere of what was there.

The diff needs no new machinery: `old` and `new` are the call's own inputs, so they are already on
the record (`Invoked.inputs`) and on the approval card (`ApprovalRequested.inputs`) — a host sees
what an edit would do *before* approving it, without reading the disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.kernel import Completed, Failed, Refused

pytestmark = pytest.mark.anyio

BEFORE = "alpha\nbeta\ngamma\n"


async def _env(root: Path, mode: Any = "full") -> Any:
    return await LocalEnvironment.open(root, mode=mode)


# ------------------------------------------------------------------------------ edit_file


async def test_an_edit_replaces_one_region_and_leaves_the_rest(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text(BEFORE)
    env = await _env(tmp_path)

    done = await env.invoke("edit_file", {"path": "f.txt", "edits": [{"old": "beta", "new": "B"}]})

    assert isinstance(done, Completed)
    assert (tmp_path / "f.txt").read_text() == "alpha\nB\ngamma\n"


async def test_several_edits_in_one_call_all_land(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text(BEFORE)
    env = await _env(tmp_path)

    await env.invoke(
        "edit_file",
        {"path": "f.txt", "edits": [{"old": "alpha", "new": "A"}, {"old": "gamma", "new": "G"}]},
    )

    assert (tmp_path / "f.txt").read_text() == "A\nbeta\nG\n"


async def test_text_that_is_not_there_is_refused_and_the_file_is_untouched(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text(BEFORE)
    env = await _env(tmp_path)

    done = await env.invoke("edit_file", {"path": "f.txt", "edits": [{"old": "delta", "new": "D"}]})

    assert isinstance(done, Refused) and "delta" in done.reason
    assert (tmp_path / "f.txt").read_text() == BEFORE


async def test_text_that_appears_twice_is_refused_naming_the_count(tmp_path: Path) -> None:
    """Taking the first match silently is how an agent edits the wrong line and says it worked."""
    (tmp_path / "f.txt").write_text("x\nsame\ny\nsame\n")
    env = await _env(tmp_path)

    done = await env.invoke("edit_file", {"path": "f.txt", "edits": [{"old": "same", "new": "s"}]})

    assert isinstance(done, Refused)
    assert "2" in done.reason and "same" in done.reason
    assert (tmp_path / "f.txt").read_text() == "x\nsame\ny\nsame\n"


async def test_one_bad_edit_in_a_batch_applies_none_of_them(tmp_path: Path) -> None:
    """Atomicity is the whole reason a call takes a list: a file half-changed is a file whose
    state neither the model nor the record describes."""
    (tmp_path / "f.txt").write_text(BEFORE)
    env = await _env(tmp_path)

    done = await env.invoke(
        "edit_file",
        {
            "path": "f.txt",
            "edits": [{"old": "alpha", "new": "A"}, {"old": "nowhere", "new": "N"}],
        },
    )

    assert isinstance(done, Refused)
    assert (tmp_path / "f.txt").read_text() == BEFORE, "the good edit did not land either"


async def test_edits_apply_in_order_so_a_later_one_sees_the_earlier(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("one\n")
    env = await _env(tmp_path)

    await env.invoke(
        "edit_file",
        {"path": "f.txt", "edits": [{"old": "one", "new": "two"}, {"old": "two", "new": "three"}]},
    )

    assert (tmp_path / "f.txt").read_text() == "three\n"


async def test_an_edit_of_a_file_that_is_not_there_fails_the_way_a_read_does(
    tmp_path: Path,
) -> None:
    """**Refused is a decision; Failed is the world saying no.** A missing file is the second, and
    `read_file` already answers it that way — an edit must not invent a different vocabulary for
    the same cause. The refusals below are the ones this operation *chooses*."""
    env = await _env(tmp_path)

    done = await env.invoke("edit_file", {"path": "gone.txt", "edits": [{"old": "a", "new": "b"}]})

    assert isinstance(done, Failed) and "FileNotFound" in done.error


async def test_no_edits_is_refused_rather_than_a_silent_rewrite(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text(BEFORE)
    env = await _env(tmp_path)

    done = await env.invoke("edit_file", {"path": "f.txt", "edits": []})

    assert isinstance(done, Refused)
    assert (tmp_path / "f.txt").read_text() == BEFORE


# ------------------------------------------------------------------------------ move_file


async def test_a_move_moves(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text(BEFORE)
    env = await _env(tmp_path)

    done = await env.invoke("move_file", {"from": "a.txt", "to": "sub/b.txt"})

    assert isinstance(done, Completed)
    assert (tmp_path / "sub" / "b.txt").read_text() == BEFORE
    assert not (tmp_path / "a.txt").exists()


async def test_a_move_onto_something_that_exists_is_refused_naming_it(tmp_path: Path) -> None:
    """The refusal that keeps a move `write`-class: nothing is destroyed, so it can be
    moved back."""
    (tmp_path / "a.txt").write_text("source\n")
    (tmp_path / "b.txt").write_text("precious\n")
    env = await _env(tmp_path)

    done = await env.invoke("move_file", {"from": "a.txt", "to": "b.txt"})

    assert isinstance(done, Refused) and "b.txt" in done.reason
    assert (tmp_path / "b.txt").read_text() == "precious\n"
    assert (tmp_path / "a.txt").read_text() == "source\n", "and the source is still there"


async def test_moving_something_that_is_not_there_fails_rather_than_being_refused(
    tmp_path: Path,
) -> None:
    """Same rule: the destination check is a decision this operation makes, so it refuses; a
    missing source is the filesystem's answer, so it fails."""
    env = await _env(tmp_path)

    assert isinstance(await env.invoke("move_file", {"from": "gone.txt", "to": "x.txt"}), Failed)


# ------------------------------------------------------------------- how they are governed


async def test_both_are_write_class_like_write_file(tmp_path: Path) -> None:
    env = await _env(tmp_path)

    by_id = {r.id: r for r in await env.registrations()}
    writing = by_id["write_file"].component.effects

    for name in ("edit_file", "move_file"):
        effects = by_id[name].component.effects
        assert effects.writes.names == writing.writes.names
        assert effects.reversible is True, (
            "nothing is destroyed, so it can be undone by another act"
        )
        assert not effects.reaches and not effects.costs


async def test_neither_is_offered_in_a_read_only_environment(tmp_path: Path) -> None:
    env = await _env(tmp_path, mode="read-only")

    offered = {r.id for r in await env.registrations()}

    assert "edit_file" not in offered and "move_file" not in offered
    assert "glob" in offered, "the read-class half is still there"


async def test_a_read_only_environment_refuses_them_before_governance_is_asked(
    tmp_path: Path,
) -> None:
    """A mode is the environment's own promise, not one it outsources."""
    (tmp_path / "f.txt").write_text(BEFORE)
    env = await _env(tmp_path, mode="read-only")

    edited = await env.invoke(
        "edit_file", {"path": "f.txt", "edits": [{"old": "beta", "new": "B"}]}
    )
    moved = await env.invoke("move_file", {"from": "f.txt", "to": "g.txt"})

    assert isinstance(edited, Refused) and isinstance(moved, Refused)
    assert (tmp_path / "f.txt").read_text() == BEFORE
