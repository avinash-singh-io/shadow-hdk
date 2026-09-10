"""A hard link is the outside inode with a name inside the root (BUG-008).

`_resolve` follows symlinks and normalises `..` — the bug it was written to avoid — but a hard link
has nothing to resolve: it *is* the file, under a second name. So confinement was being checked by
the name after all. **Reproduced before the fix:** `read_file` returned the outside content and
`write_file` overwrote the outside file. With the subprocess sandbox (`run_shell: ln …`) that is a
two-component escape with no rule broken by either half.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from shadow_hdk.adapters.workspace import WorkspaceComponents

from shadow_hdk.kernel import Completed, Failed


@pytest.fixture
def outside(tmp_path: Path) -> Path:
    beyond = tmp_path / "outside"
    beyond.mkdir()
    secret = beyond / "secret.txt"
    secret.write_text("THE-OUTSIDE-CONTENT")
    return secret


@pytest.fixture
def root(tmp_path: Path) -> Path:
    inside = tmp_path / "workspace"
    inside.mkdir()
    return inside


async def test_reading_through_a_hard_link_is_refused(outside: Path, root: Path) -> None:
    os.link(outside, root / "hl.txt")
    got = await WorkspaceComponents(root).invoke("read_file", {"path": "hl.txt"})
    assert isinstance(got, Failed), got
    assert "THE-OUTSIDE-CONTENT" not in got.error


async def test_writing_through_a_hard_link_leaves_the_outside_file_alone(
    outside: Path, root: Path
) -> None:
    """The half that matters: reading is a leak, writing is a change to somebody else's file."""
    os.link(outside, root / "hl.txt")
    wrote = await WorkspaceComponents(root).invoke(
        "write_file", {"path": "hl.txt", "content": "OVERWRITTEN"}
    )
    assert isinstance(wrote, Failed), wrote
    assert outside.read_text() == "THE-OUTSIDE-CONTENT"


async def test_deleting_through_a_hard_link_is_refused(outside: Path, root: Path) -> None:
    os.link(outside, root / "hl.txt")
    deleted = await WorkspaceComponents(root).invoke("delete_file", {"path": "hl.txt"})
    assert isinstance(deleted, Failed), deleted
    assert outside.exists()


async def test_an_ordinary_file_is_still_readable_and_writable(root: Path) -> None:
    """The refusal is about a second link, not about files."""
    workspace = WorkspaceComponents(root)
    wrote = await workspace.invoke("write_file", {"path": "notes.txt", "content": "hello"})
    assert isinstance(wrote, Completed), wrote
    read = await workspace.invoke("read_file", {"path": "notes.txt"})
    assert read == Completed("hello")


async def test_a_link_made_after_the_file_was_written_is_refused_next_time(
    root: Path, tmp_path: Path
) -> None:
    """A file that was fine can stop being fine: the check is at every use, not at creation."""
    workspace = WorkspaceComponents(root)
    assert isinstance(
        await workspace.invoke("write_file", {"path": "n.txt", "content": "x"}), Completed
    )
    os.link(root / "n.txt", tmp_path / "elsewhere.txt")
    again = await workspace.invoke("read_file", {"path": "n.txt"})
    assert isinstance(again, Failed), again


async def test_a_nul_byte_in_a_path_is_data_not_a_traceback(root: Path) -> None:
    """D7: a component never raises. It raised `ValueError` past the `except` that catches every
    other filesystem refusal, which is a contract breach whatever the cause."""
    got = await WorkspaceComponents(root).invoke("read_file", {"path": "a\0b"})
    assert isinstance(got, Failed), got


@pytest.mark.parametrize("name", ["read_file", "delete_file"])
async def test_a_nul_byte_is_refused_by_every_door(root: Path, name: str) -> None:
    got = await WorkspaceComponents(root).invoke(name, {"path": "a\0b"})
    assert isinstance(got, Failed), got


async def test_a_directory_with_many_links_is_still_listable(root: Path) -> None:
    """A directory's link count is its subdirectories plus two — refusing on `st_nlink > 1` for
    directories would refuse every directory that has one."""
    (root / "sub").mkdir()
    (root / "sub" / "deeper").mkdir()
    listed = await WorkspaceComponents(root).invoke("list_dir", {"path": "sub"})
    assert listed == Completed(["deeper/"])
