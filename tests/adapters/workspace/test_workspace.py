"""A workspace the agent can write to, and cannot write outside.

The confinement is the point. Everything else here — reading, listing, creating parents — is
plumbing; the tests that matter are the three ways out of a directory and the fact that each is
**refused as an observation** rather than raised, so an agent sees a `Failed` it can route around
instead of a traceback that ends its run.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from shadow_hdk.adapters.workspace import WorkspaceComponents
from pydantic import JsonValue

from shadow_hdk.kernel import Completed, EffectProfile, Failed, ScopeSet
from shadow_hdk.kernel.ports import ComponentPort
from tests.adapters.contract import ComponentPortContract


def workspace(root: Path, **kw: object) -> WorkspaceComponents:
    return WorkspaceComponents(root, at="2026-09-10T00:00:00+00:00", **kw)  # type: ignore[arg-type]


async def profiles(root: Path, **kw: object) -> dict[str, EffectProfile]:
    components = workspace(root, **kw)
    return {r.id: r.component.effects for r in await components.registrations()}


class TestWorkspaceComponentsIsAComponentPort(ComponentPortContract):
    @asynccontextmanager
    async def using(self) -> AsyncIterator[ComponentPort]:
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "notes.md").write_text("hello")
            yield workspace(Path(tmp))

    def valid_call(self) -> tuple[str, JsonValue]:
        return "read_file", {"path": "notes.md"}


# ---------------------------------------------------------------- it works


async def test_a_file_written_can_be_read_back(tmp_path: Path) -> None:
    components = workspace(tmp_path)
    written = await components.invoke("write_file", {"path": "notes.md", "content": "# Lathe\n"})
    assert isinstance(written, Completed)
    assert (tmp_path / "notes.md").read_text() == "# Lathe\n"
    read = await components.invoke("read_file", {"path": "notes.md"})
    assert read == Completed("# Lathe\n")


async def test_writing_creates_the_directories_on_the_way(tmp_path: Path) -> None:
    components = workspace(tmp_path)
    await components.invoke(
        "write_file", {"path": "out/pages/index.html", "content": "<h1>hi</h1>"}
    )
    assert (tmp_path / "out" / "pages" / "index.html").read_text() == "<h1>hi</h1>"


async def test_listing_shows_what_is_there(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("a")
    (tmp_path / "b").mkdir()
    listed = await workspace(tmp_path).invoke("list_dir", {"path": "."})
    assert isinstance(listed, Completed)
    assert isinstance(listed.output, list)
    assert sorted(str(name) for name in listed.output) == ["a.md", "b/"]


async def test_deleting_removes_a_file(tmp_path: Path) -> None:
    (tmp_path / "gone.md").write_text("x")
    assert isinstance(
        await workspace(tmp_path).invoke("delete_file", {"path": "gone.md"}), Completed
    )
    assert not (tmp_path / "gone.md").exists()


async def test_a_missing_file_is_data_not_a_traceback(tmp_path: Path) -> None:
    observation = await workspace(tmp_path).invoke("read_file", {"path": "nope.md"})
    assert isinstance(observation, Failed)
    assert "nope.md" in observation.error


# ---------------------------------------------------------------- it confines


async def test_climbing_out_with_dot_dot_is_refused(tmp_path: Path) -> None:
    observation = await workspace(tmp_path).invoke("read_file", {"path": "../secrets.txt"})
    assert isinstance(observation, Failed)
    assert "outside" in observation.error


async def test_an_absolute_path_is_refused(tmp_path: Path) -> None:
    observation = await workspace(tmp_path).invoke("read_file", {"path": "/etc/passwd"})
    assert isinstance(observation, Failed)
    assert "outside" in observation.error


async def test_a_symlink_pointing_out_of_the_root_is_refused(tmp_path: Path) -> None:
    """The one that a string check misses. A path can be inside the root and still name a file that
    is not, and a link is how. Resolved before the check, with a real symlink, on a real disk.
    """
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("a secret")
    root = tmp_path / "root"
    root.mkdir()
    os.symlink(outside, root / "innocent.txt")

    observation = await workspace(root).invoke("read_file", {"path": "innocent.txt"})
    assert isinstance(observation, Failed), f"a symlink walked out of the root: {observation!r}"
    assert "outside" in observation.error


async def test_a_symlinked_directory_cannot_be_written_through(tmp_path: Path) -> None:
    elsewhere = tmp_path.parent / "elsewhere"
    elsewhere.mkdir(exist_ok=True)
    root = tmp_path / "root"
    root.mkdir()
    os.symlink(elsewhere, root / "out")

    observation = await workspace(root).invoke(
        "write_file", {"path": "out/planted.txt", "content": "x"}
    )
    assert isinstance(observation, Failed)
    assert not (elsewhere / "planted.txt").exists()


async def test_the_root_itself_is_inside_the_root(tmp_path: Path) -> None:
    """A confinement check that refuses everything is not a confinement check."""
    assert isinstance(await workspace(tmp_path).invoke("list_dir", {"path": "."}), Completed)


# ---------------------------------------------------------------- what it declares


async def test_reading_declares_reading_and_writing_declares_writing(tmp_path: Path) -> None:
    found = await profiles(tmp_path)
    assert found["read_file"].reads == ScopeSet.of("workspace")
    assert found["read_file"].writes == ScopeSet()
    assert found["write_file"].writes == ScopeSet.of("workspace")


async def test_writing_a_file_is_reversible_and_deleting_one_is_not() -> None:
    """The distinction a mode can act on: *change things* and *destroy things* are different
    permissions, and `reversible` is where the difference lives."""
    with TemporaryDirectory() as tmp:
        found = await profiles(Path(tmp))
    assert found["write_file"].reversible is True
    assert found["delete_file"].reversible is False


async def test_a_read_only_workspace_offers_no_way_to_write(tmp_path: Path) -> None:
    """Absent, not refused at call time — the same rule the registry follows everywhere."""
    names = set(await profiles(tmp_path, writable=False))
    assert names == {"read_file", "list_dir"}
