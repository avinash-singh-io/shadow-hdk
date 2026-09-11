"""File operations stay inside the root, in every mode — the workspace adapter's claims, kept.

The workspace adapter's confinement was real and its tests were good; this file carries them onto
the environment, because a claim that was true and tested must not be lost in a rename. `full`
mode throughout, so they run on any machine: path confinement is by `inside()`, not by the OS
sandbox, and it holds whether or not one exists.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import JsonValue

from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.kernel import Completed, Failed, Refused, ScopeSet
from shadow_hdk.kernel.observations import Observation


async def full(tmp_path: Path) -> tuple[LocalEnvironment, Path]:
    root = tmp_path / "ws"
    root.mkdir()
    return await LocalEnvironment.open(root, mode="full"), root


def refused(observation: Observation) -> str:
    assert isinstance(observation, Refused), observation
    return observation.reason


# ------------------------------------------------------------------ ordinary use


async def test_a_file_written_can_be_read_back(tmp_path: Path) -> None:
    env, _ = await full(tmp_path)
    await env.invoke("write_file", {"path": "notes/a.txt", "content": "twelve"})

    assert await env.invoke("read_file", {"path": "notes/a.txt"}) == Completed("twelve")


async def test_writing_creates_the_directories_on_the_way(tmp_path: Path) -> None:
    env, root = await full(tmp_path)

    await env.invoke("write_file", {"path": "deep/er/x.txt", "content": "x"})

    assert (root / "deep" / "er" / "x.txt").exists()


async def test_listing_shows_what_is_there_and_marks_directories(tmp_path: Path) -> None:
    env, root = await full(tmp_path)
    (root / "d").mkdir()
    (root / "f.txt").write_text("f")

    assert await env.invoke("list_dir", {}) == Completed(["d/", "f.txt"])


async def test_deleting_removes_a_file_and_is_irreversible(tmp_path: Path) -> None:
    env, root = await full(tmp_path)
    (root / "gone.txt").write_text("x")

    await env.invoke("delete_file", {"path": "gone.txt"})

    assert not (root / "gone.txt").exists()
    effects = {r.id: r.component.effects for r in await env.registrations()}
    assert effects["delete_file"].reversible is False
    assert effects["write_file"].reversible is True


async def test_a_missing_file_is_data_not_a_traceback(tmp_path: Path) -> None:
    env, _ = await full(tmp_path)

    assert isinstance(await env.invoke("read_file", {"path": "nope.txt"}), Failed)


async def test_the_root_itself_is_inside_the_root(tmp_path: Path) -> None:
    env, _ = await full(tmp_path)

    assert isinstance(await env.invoke("list_dir", {"path": "."}), Completed)


# ------------------------------------------------------------------ climbing out


async def test_climbing_out_with_dot_dot_is_refused(tmp_path: Path) -> None:
    env, _ = await full(tmp_path)
    (tmp_path / "secret").write_text("s")

    assert "outside" in refused(await env.invoke("read_file", {"path": "../secret"}))


async def test_an_absolute_path_is_refused(tmp_path: Path) -> None:
    env, _ = await full(tmp_path)

    assert "outside" in refused(await env.invoke("read_file", {"path": "/etc/hosts"}))


async def test_a_symlink_pointing_out_of_the_root_is_refused(tmp_path: Path) -> None:
    env, root = await full(tmp_path)
    (tmp_path / "secret").write_text("s")
    (root / "link").symlink_to(tmp_path / "secret")

    assert "outside" in refused(await env.invoke("read_file", {"path": "link"}))


async def test_a_symlinked_directory_cannot_be_written_through(tmp_path: Path) -> None:
    env, root = await full(tmp_path)
    (tmp_path / "elsewhere").mkdir()
    (root / "door").symlink_to(tmp_path / "elsewhere")

    refused(await env.invoke("write_file", {"path": "door/x.txt", "content": "x"}))

    assert not (tmp_path / "elsewhere" / "x.txt").exists()


# ------------------------------------------------------------------ hard links (BUG-008)


async def test_reading_through_a_hard_link_is_refused(tmp_path: Path) -> None:
    """A hard link is the file: `resolve()` returns a path under the root that is the same inode as
    one outside it. The link count is the only tell."""
    env, root = await full(tmp_path)
    outside = tmp_path / "secret"
    outside.write_text("s")
    os.link(outside, root / "hard")

    assert "hard link" in refused(await env.invoke("read_file", {"path": "hard"}))


async def test_writing_through_a_hard_link_leaves_the_outside_file_alone(tmp_path: Path) -> None:
    env, root = await full(tmp_path)
    outside = tmp_path / "secret"
    outside.write_text("original")
    os.link(outside, root / "hard")

    refused(await env.invoke("write_file", {"path": "hard", "content": "overwritten"}))

    assert outside.read_text() == "original"


async def test_deleting_through_a_hard_link_is_refused(tmp_path: Path) -> None:
    env, root = await full(tmp_path)
    outside = tmp_path / "secret"
    outside.write_text("s")
    os.link(outside, root / "hard")

    refused(await env.invoke("delete_file", {"path": "hard"}))

    assert outside.exists()


async def test_a_directory_with_many_links_is_still_listable(tmp_path: Path) -> None:
    """Directories always carry a link count above one — `.` and `..` — and are not files. A rule
    that refused them would refuse every listing."""
    env, root = await full(tmp_path)
    (root / "d" / "e").mkdir(parents=True)

    assert isinstance(await env.invoke("list_dir", {"path": "d"}), Completed)


# ------------------------------------------------------------------ a path that is not a path


async def test_a_nul_byte_in_a_path_is_data_not_a_traceback(tmp_path: Path) -> None:
    env, _ = await full(tmp_path)

    doors: list[tuple[str, dict[str, JsonValue]]] = [
        ("read_file", {"path": "a\x00b"}),
        ("write_file", {"path": "a\x00b", "content": "x"}),
        ("delete_file", {"path": "a\x00b"}),
        ("list_dir", {"path": "a\x00b"}),
    ]
    for door, inputs in doors:
        outcome = await env.invoke(door, inputs)
        assert isinstance(outcome, Failed | Refused), (door, outcome)


# ------------------------------------------------------------------ what the operations declare


async def test_reading_declares_reading_and_writing_declares_writing(tmp_path: Path) -> None:
    env, _ = await full(tmp_path)
    effects = {r.id: r.component.effects for r in await env.registrations()}

    assert effects["read_file"].writes == ScopeSet()
    assert effects["write_file"].writes == ScopeSet(everything=True), "full mode is honest"
