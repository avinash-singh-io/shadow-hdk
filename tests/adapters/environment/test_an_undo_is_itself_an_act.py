"""Checkpointing and undoing are acts the mode judges (ENH-043, D161–D163).

"An undo that bypasses governance is a hole" — our own answer to lane P, and this is it kept.
Restoring **is a write**: it overwrites work that may be on no snapshot, and it deletes files that
exist. So it derives like every other act, from the one derivation, and `ask` stops a person before
it. That is one of the few places where the conservative derivation is also the better product:
an undo is exactly the thing somebody should be asked about.

D162: nothing snapshots automatically. When to checkpoint is a *policy*, and the boundary rule puts
policy on the other side of a port — the kit cannot know whether a turn deserves one. A product
reaches `environment.history` directly for its own per-turn checkpoints (its own act, not the
agent's); the operations here are for when the **agent** wants one, and then the mode judges it.

D161's refuse-not-crash: a root that is not a work tree has no history, and says so.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.environment.local import LocalEnvironment
from shadow_hdk.kernel import Completed, Refused
from shadow_hdk.runtime.environment import OPERATIONS, Isolation, effects_of

pytestmark = pytest.mark.anyio


def a_repository(where: Path) -> Path:
    for args in (
        ("init", "-q"),
        ("config", "user.email", "test@example.com"),
        ("config", "user.name", "A Test"),
    ):
        subprocess.run(["git", *args], cwd=where, check=True, capture_output=True)
    (where / "app.py").write_text("original\n")
    subprocess.run(["git", "add", "-A"], cwd=where, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "first"], cwd=where, check=True, capture_output=True
    )
    return where


def told(observation: Any) -> dict[str, Any]:
    assert isinstance(observation, Completed), observation
    assert isinstance(observation.output, dict), observation.output
    return observation.output


# ------------------------------------------------------------------ the round trip


async def test_an_agent_can_checkpoint_and_then_undo_its_own_work(tmp_path: Path) -> None:
    root = a_repository(tmp_path)
    environment = await LocalEnvironment.open(root, mode="full")
    try:
        taken = told(await environment.invoke("checkpoint", {"label": "before the refactor"}))
        assert taken["snapshot"], taken

        await environment.invoke("write_file", {"path": "app.py", "content": "a bad idea\n"})
        assert (root / "app.py").read_text() == "a bad idea\n"

        put_back = told(await environment.invoke("restore", {"snapshot": taken["snapshot"]}))
        assert put_back["restored"] == taken["snapshot"]
        assert (root / "app.py").read_text() == "original\n"
    finally:
        await environment.close()


async def test_checkpoints_can_be_listed(tmp_path: Path) -> None:
    root = a_repository(tmp_path)
    environment = await LocalEnvironment.open(root, mode="full")
    try:
        await environment.invoke("checkpoint", {"label": "one"})
        await environment.invoke("checkpoint", {"label": "two"})

        listed = told(await environment.invoke("list_checkpoints", {}))
        labels = [s["label"] for s in listed["snapshots"]]
        assert labels[:2] == ["two", "one"], listed
    finally:
        await environment.close()


async def test_the_host_reaches_the_history_directly_for_its_own_checkpoints(
    tmp_path: Path,
) -> None:
    """D162. A product checkpointing before every turn is doing its own act, not the agent's, so
    it goes through the port and nothing is judged or asked — which is what makes an automatic
    per-turn checkpoint viable at all."""
    root = a_repository(tmp_path)
    environment = await LocalEnvironment.open(root, mode="full")
    try:
        assert environment.history is not None, "a work tree has a history"

        taken = await environment.history.snapshot("the host's own")
        (root / "app.py").write_text("changed\n")
        await environment.history.restore(taken)

        assert (root / "app.py").read_text() == "original\n"
    finally:
        await environment.close()


# ------------------------------------------------------------------ and it is judged (D163)


def test_a_restore_derives_as_irreversible_so_ask_stops_a_person() -> None:
    """The profile, from the one derivation. `reversible=True` would be a claim the mechanism
    cannot keep: a restore overwrites work that is on no snapshot."""
    kinds = {name: operation for name, operation, _d, _p, _r in OPERATIONS}
    assert kinds["restore"] == "delete", kinds.get("restore")

    isolation = Isolation.none()
    profile = effects_of(isolation, "workspace-write", kinds["restore"])
    assert profile.reversible is False, profile
    assert profile.writes.everything or profile.writes.names, "a restore writes"


def test_a_checkpoint_derives_as_a_write_rather_than_claiming_to_change_nothing() -> None:
    """It writes objects into the repository. Deriving it as a read to spare a person the question
    would be the kind of convenient under-claim `ASSUME_WORST` exists to refuse."""
    kinds = {name: operation for name, operation, _d, _p, _r in OPERATIONS}
    assert kinds["checkpoint"] == "write", kinds.get("checkpoint")
    assert kinds["list_checkpoints"] == "list", kinds.get("list_checkpoints")


async def test_a_restore_is_withheld_in_a_read_only_environment(tmp_path: Path) -> None:
    """With a **real** snapshot, so the only reason left to refuse is the mode.

    Found by a mutation: with a made-up name this passed with the guard deleted, because the
    history refused the unknown name anyway. A test that cannot tell *why* it was refused is not
    testing the guard.
    """
    root = a_repository(tmp_path)
    open_one = await LocalEnvironment.open(root, mode="full")
    try:
        taken = told(await open_one.invoke("checkpoint", {"label": "real"}))["snapshot"]
    finally:
        await open_one.close()
    (root / "app.py").write_text("changed outside\n")

    environment = await LocalEnvironment.open(root, mode="read-only")
    try:
        answer = await environment.invoke("restore", {"snapshot": taken})

        assert isinstance(answer, Refused), answer
        assert "read-only" in answer.reason, answer.reason
        assert (root / "app.py").read_text() == "changed outside\n", "nothing was put back"
    finally:
        await environment.close()


# ------------------------------------------------------------------ and refuses where it cannot


async def test_a_root_that_is_not_a_work_tree_has_no_history_and_says_so(tmp_path: Path) -> None:
    """D161's refuse-not-crash. Cheap where a root is a work tree, and honest where it is not."""
    environment = await LocalEnvironment.open(tmp_path, mode="full")
    try:
        assert environment.history is None

        asks: tuple[tuple[str, dict[str, Any]], ...] = (
            ("checkpoint", {"label": "x"}),
            ("restore", {"snapshot": "x"}),
            ("list_checkpoints", {}),
        )
        for what, inputs in asks:
            answer = await environment.invoke(what, inputs)
            assert isinstance(answer, Refused), (what, answer)
            assert "history" in answer.reason.lower(), answer.reason
    finally:
        await environment.close()


async def test_restoring_a_snapshot_nobody_took_is_refused_not_failed(tmp_path: Path) -> None:
    """A `Failed` would read to a model as *the kit broke*; a `Refused` reads as *not that one*."""
    root = a_repository(tmp_path)
    environment = await LocalEnvironment.open(root, mode="full")
    try:
        answer = await environment.invoke("restore", {"snapshot": "never-existed"})

        assert isinstance(answer, Refused), answer
        assert "never-existed" in answer.reason
    finally:
        await environment.close()
