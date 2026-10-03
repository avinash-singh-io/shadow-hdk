"""The cap on a change's diff is the host's, and a cut diff can be asked for whole (H20, phase 66).

0.38.0 recorded a bounded unified diff for every write-class act, with the bound a constant:
`CHANGE_DIFF_BYTES = 4_096`, and all four call sites took the default. Lane P's workbench therefore
shows 4 KB per file and has no way to show more — not because the product chose that number, but
because nobody could choose it.

Two halves, and they are different asks. **The cap is the host's** — a product showing a diff panel
knows what it can render and the kit does not. And **a cut diff can be asked for whole**, because
raising the cap for every change to suit the largest one makes every record bigger; the honest shape
is a small diff on the record and a door to the rest.

The format stays **unified diff** throughout, from `difflib` in the standard library. It is the
format every diff tool, review UI and patch program already reads, and inventing another would
make a product write a parser for us.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.environment.local import LocalEnvironment
from shadow_hdk.kernel import Completed, Refused
from shadow_hdk.runtime.environment import CHANGE_DIFF_BYTES

pytestmark = pytest.mark.anyio

BIG = "".join(f"line {n}\n" for n in range(600))
"""Comfortably past the default cap, so `truncated` is in play without relying on its size."""


def change_of(observation: Any) -> dict[str, Any]:
    assert isinstance(observation, Completed), observation
    value = observation.output
    assert isinstance(value, dict), value
    got = value.get("change")
    assert isinstance(got, dict), f"no change block on {value!r}"
    return got


async def _wrote(root: Path, content: str, **kw: Any) -> tuple[LocalEnvironment, dict[str, Any]]:
    """An environment left open, so the change can be asked about afterwards."""
    (root / "f.txt").write_text("first\n")
    environment = await LocalEnvironment.open(root, mode="workspace-write", **kw)
    told = await environment.invoke("write_file", {"path": "f.txt", "content": content})
    return environment, change_of(told)


# ------------------------------------------------------------------ the cap is the host's


async def test_the_default_cap_is_what_it_always_was(tmp_path: Path) -> None:
    """Nothing that works today moves. Asserted rather than assumed."""
    environment, change = await _wrote(tmp_path, BIG)
    try:
        assert change["truncated"] is True
        assert len(change["diff"]) <= CHANGE_DIFF_BYTES
    finally:
        await environment.close()


async def test_a_host_may_raise_the_cap(tmp_path: Path) -> None:
    """The whole of H20's first half: the number is the product's to choose."""
    environment, change = await _wrote(tmp_path, BIG, change_diff_bytes=200_000)
    try:
        assert change["truncated"] is False, "a raised cap must not still cut"
        assert len(change["diff"]) > CHANGE_DIFF_BYTES, len(change["diff"])
        assert "line 599" in change["diff"], "the whole change is there"
    finally:
        await environment.close()


async def test_a_host_may_lower_the_cap(tmp_path: Path) -> None:
    """Paired, so the test above cannot pass because the cap is simply ignored."""
    environment, change = await _wrote(tmp_path, BIG, change_diff_bytes=200)
    try:
        assert change["truncated"] is True
        assert len(change["diff"]) <= 200, len(change["diff"])
    finally:
        await environment.close()


async def test_a_host_may_ask_for_no_cap_at_all(tmp_path: Path) -> None:
    environment, change = await _wrote(tmp_path, BIG, change_diff_bytes=None)
    try:
        assert change["truncated"] is False
        assert "line 599" in change["diff"]
    finally:
        await environment.close()


async def test_the_line_counts_are_the_whole_changes_either_way(tmp_path: Path) -> None:
    """D154's rule, which the cap must not break: `added` and `removed` are counted over the whole
    diff before it is cut, so a host reading `truncated` still learns the true size."""
    small, cut = await _wrote(tmp_path, BIG, change_diff_bytes=200)
    try:
        counted = (cut["added"], cut["removed"])
    finally:
        await small.close()

    whole_env, whole = await _wrote(tmp_path, BIG, change_diff_bytes=None)
    try:
        assert (whole["added"], whole["removed"]) == counted, "the counts moved with the cap"
    finally:
        await whole_env.close()


# ------------------------------------------------------------------ and a cut diff can be asked for


async def test_a_cut_change_says_how_to_ask_for_the_rest(tmp_path: Path) -> None:
    """A host cannot ask for something it was given no handle to."""
    environment, change = await _wrote(tmp_path, BIG)
    try:
        assert change.get("handle"), f"a truncated change must carry a handle: {change.keys()}"
    finally:
        await environment.close()


async def test_a_change_that_was_not_cut_carries_no_handle(tmp_path: Path) -> None:
    """Nothing to fetch, so nothing is held — a handle for every write would keep every file's
    content in memory for the life of the environment."""
    environment, change = await _wrote(tmp_path, "second\n")
    try:
        assert change["truncated"] is False
        assert not change.get("handle"), change
    finally:
        await environment.close()


async def test_the_whole_diff_comes_back_through_a_governed_operation(tmp_path: Path) -> None:
    """H20's second half. A registered component, so it is judged like every other read."""
    environment, change = await _wrote(tmp_path, BIG)
    try:
        told = await environment.invoke("change_diff", {"handle": change["handle"]})
        assert isinstance(told, Completed), told
        value = told.output
        assert isinstance(value, dict)
        assert "line 599" in str(value["diff"]), "the rest of the change is not there"
        assert int(str(value["total"])) > CHANGE_DIFF_BYTES, value["total"]
    finally:
        await environment.close()


async def test_it_pages_by_start_and_length_like_recall_does(tmp_path: Path) -> None:
    """The kit already has one idiom for *a result too large to show whole* — `recall`'s handle,
    start and length (D47). A second idiom for the same problem would be a second thing to learn."""
    environment, change = await _wrote(tmp_path, BIG)
    try:
        first = await environment.invoke("change_diff", {"handle": change["handle"], "length": 50})
        assert isinstance(first, Completed)
        head = first.output
        assert isinstance(head, dict)
        assert len(str(head["diff"])) == 50, head
        assert head["more"] is True

        rest = await environment.invoke(
            "change_diff", {"handle": change["handle"], "start": 50, "length": 50}
        )
        assert isinstance(rest, Completed)
        tail = rest.output
        assert isinstance(tail, dict)
        assert str(tail["diff"]) != str(head["diff"]), "a second page returned the first"
        assert tail["start"] == 50
    finally:
        await environment.close()


async def test_the_last_page_says_there_is_no_more(tmp_path: Path) -> None:
    environment, change = await _wrote(tmp_path, BIG)
    try:
        whole = await environment.invoke(
            "change_diff", {"handle": change["handle"], "length": 10_000_000}
        )
        assert isinstance(whole, Completed)
        value = whole.output
        assert isinstance(value, dict)
        assert value["more"] is False, value
    finally:
        await environment.close()


async def test_the_format_is_still_unified_diff(tmp_path: Path) -> None:
    """The open standard, the whole way through: what comes back from the door is the same format as
    what went on the record, so a product parses one thing."""
    environment, change = await _wrote(tmp_path, BIG, change_diff_bytes=None)
    try:
        told = await environment.invoke("change_diff", {"handle": change.get("handle") or "x"})
        whole = change["diff"]
    finally:
        await environment.close()

    assert whole.startswith("--- a/f.txt"), whole[:40]
    assert "+++ b/f.txt" in whole
    assert isinstance(told, Refused | Completed)


# ------------------------------------------------------------------ and an unknown handle refuses


async def test_an_unknown_handle_is_refused_rather_than_answered_emptily(tmp_path: Path) -> None:
    """An empty diff for a handle nobody holds reads as *nothing changed*, which is a lie."""
    environment, _change = await _wrote(tmp_path, BIG)
    try:
        told = await environment.invoke("change_diff", {"handle": "no-such-handle"})
        assert isinstance(told, Refused), told
        assert "no-such-handle" in told.reason, told.reason
    finally:
        await environment.close()


async def test_a_handle_dropped_to_stay_bounded_says_so_rather_than_being_unknown(
    tmp_path: Path,
) -> None:
    """Holding every cut diff for an environment's life is a memory leak and a privacy problem,
    so the hold is bounded and the oldest go first. A host that asks for one that was dropped must
    be told *it was dropped*, not *it never existed* — those call for different behaviour."""
    (tmp_path / "f.txt").write_text("first\n")
    environment = await LocalEnvironment.open(
        tmp_path, mode="workspace-write", change_diff_bytes=100, change_diffs_held=1
    )
    try:
        first = change_of(await environment.invoke("write_file", {"path": "f.txt", "content": BIG}))
        assert first.get("handle"), "the first write must be held, or there is nothing to evict"
        # Wholly different content, so the *second* diff is large too and is itself held. Appending
        # one line to BIG produces a diff of about eighty bytes, which the cap never cuts — so
        # nothing would be held and nothing evicted, and the first version of this test passed for
        # that reason rather than for the one it claims.
        other = "".join(f"other {n}\n" for n in range(600))
        second = change_of(
            await environment.invoke("write_file", {"path": "f.txt", "content": other})
        )
        assert second.get("handle") and second["handle"] != first["handle"], second

        told = await environment.invoke("change_diff", {"handle": first["handle"]})

        assert isinstance(told, Refused), told
        assert "dropped" in told.reason.lower() or "no longer" in told.reason.lower(), told.reason
    finally:
        await environment.close()


async def test_a_host_may_hold_nothing_at_all(tmp_path: Path) -> None:
    """`change_diffs_held=0` is a documented choice, and the right one for a product that renders
    the recorded diff and never asks for more: holding a cut diff is only useful to someone who
    will ask, and holding it for someone who will not is a leak with no upside.

    A cut change then carries **no handle** — which is the same signal as *nothing was cut*, and
    correct for the same reason: a host reading no handle has nothing to ask for.
    """
    environment, change = await _wrote(tmp_path, BIG, change_diffs_held=0)
    try:
        assert change["truncated"] is True, "the cap still applies"
        assert not change.get("handle"), f"nothing is held, so nothing is offered: {change}"
    finally:
        await environment.close()


async def test_the_uncut_size_is_reported_whether_or_not_anything_is_held(tmp_path: Path) -> None:
    """`whole` is how a host decides whether to ask at all, so it cannot depend on the hold."""
    environment, change = await _wrote(tmp_path, BIG, change_diffs_held=0)
    try:
        assert int(str(change["whole"])) > CHANGE_DIFF_BYTES, change["whole"]
        assert int(str(change["whole"])) > len(str(change["diff"])), change
    finally:
        await environment.close()


async def test_nonsense_paging_arguments_get_the_whole_thing_rather_than_a_failure(
    tmp_path: Path,
) -> None:
    """A string or a float where a number belongs is a caller's mistake arriving over the wire, and
    paging has an obvious safe answer: the whole thing, from the start. The refusals this operation
    owes are about the **handle**, which is the part only the kit knows."""
    environment, change = await _wrote(tmp_path, BIG)
    try:
        told = await environment.invoke(
            "change_diff", {"handle": change["handle"], "start": "x", "length": None}
        )
        assert isinstance(told, Completed), told
        value = told.output
        assert isinstance(value, dict)
        assert value["start"] == 0
        assert value["more"] is False, "no length given means all of it"

        # `bool` is an `int` subclass in Python, so an unguarded `int(given)` turns `true` into a
        # start of 1 and silently drops the first character. A classic trap, and worth a line.
        booled = await environment.invoke(
            "change_diff", {"handle": change["handle"], "start": True}
        )
        assert isinstance(booled, Completed), booled
        was = booled.output
        assert isinstance(was, dict)
        assert was["start"] == 0, f"a boolean was read as a number: {was['start']}"
    finally:
        await environment.close()
