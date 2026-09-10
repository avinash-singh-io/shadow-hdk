"""A filesystem the agent can write to, and cannot write outside.

This is how an agent makes things — a markdown note, an HTML page, a script for the sandbox to run.
`09` §5 calls a composition and a derivation the two forms of "program" that need no containment;
this adapter is what makes the *output* of either something a person can open.

**The confinement is one function.** Every operation resolves its path and refuses anything outside
the root, and it resolves *before* it checks, because a path can be spelled entirely inside a
directory and still name a file that is not — which is what a symlink is for.

It is not a sandbox. It bounds *where* the agent writes, not what the written thing later does.
"""

from __future__ import annotations

import stat
from collections.abc import Sequence
from pathlib import Path

from pydantic import JsonValue

from shadow_hdk.kernel.components import (
    Component,
    Interface,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.effects import EffectProfile, ScopeSet
from shadow_hdk.kernel.observations import Completed, Failed, Observation
from shadow_hdk.kernel.ports import ComponentPort

WORKSPACE = ScopeSet.of("workspace")

READS = EffectProfile(reads=WORKSPACE)
WRITES = EffectProfile(reads=WORKSPACE, writes=WORKSPACE, reversible=True)
DESTROYS = EffectProfile(reads=WORKSPACE, writes=WORKSPACE, reversible=False)
"""Deleting is a **different permission** from writing, and `reversible` is where the difference
lives: a mode may let an agent change things without letting it destroy them."""

_PATH = {"type": "string", "description": "A path inside the workspace."}


class OutsideTheRoot(Exception):
    """A path that resolved somewhere the workspace does not reach."""


class WorkspaceComponents(ComponentPort):
    def __init__(
        self,
        root: Path,
        *,
        at: str = "",
        writable: bool = True,
        source: str = "workspace",
    ) -> None:
        self._root = Path(root).resolve()
        self._at = at
        self._writable = writable
        self._source = source

    # ------------------------------------------------------------------ confinement

    def _resolve(self, path: JsonValue) -> Path:
        """The only way a path becomes a file here.

        `Path.resolve()` follows symlinks and normalises `..`, so what is compared is the *real*
        destination rather than the spelling. Comparing the spelling is the bug this exists to
        avoid: `innocent.txt` looks confined right up until it is a link to `/etc/passwd`.

        **A hard link has nothing to resolve** (BUG-008). It is not a pointer to the outside file;
        it *is* that file, under a second name inside the root — so `resolve()` returns a path that
        is plainly relative to the root while the inode belongs to somebody else. Reading returned
        the outside content and writing overwrote it. So the filesystem is asked what the file is,
        not what it is called: a regular file reachable by more than one name is refused, because
        the harness cannot tell which of those names is outside the workspace and it only takes one.
        """
        if not isinstance(path, str):
            raise OutsideTheRoot(f"a path must be a string, not {type(path).__name__}")
        try:
            candidate = (self._root / path).resolve()
        except ValueError as malformed:
            # A NUL byte reaches `os.stat` as a `ValueError`, not an `OSError`, and used to escape
            # `invoke` as a traceback. A path the filesystem will not take is data (D7).
            raise OutsideTheRoot(f"{path!r} is not a usable path: {malformed}") from malformed
        if candidate != self._root and not candidate.is_relative_to(self._root):
            raise OutsideTheRoot(f"{path!r} resolves outside the workspace")
        self._one_name_only(candidate, path)
        return candidate

    @staticmethod
    def _one_name_only(candidate: Path, given: JsonValue) -> None:
        """Refuse a regular file that more than one name reaches (BUG-008).

        Directories are exempt: a directory's link count is its subdirectories plus two, so
        refusing on `st_nlink > 1` there would refuse every directory that has one.
        """
        try:
            found = candidate.lstat()
        except (OSError, ValueError):
            return  # it does not exist yet, or the filesystem refuses it; the caller finds out
        if stat.S_ISREG(found.st_mode) and found.st_nlink > 1:
            raise OutsideTheRoot(
                f"{given!r} is a hard link: {found.st_nlink} names reach this file, and the "
                "workspace cannot tell whether one of them is outside it"
            )

    # ------------------------------------------------------------------ the port

    async def registrations(self) -> Sequence[Registration]:
        found = [
            self._registration(
                "read_file",
                "Read a text file from the workspace.",
                READS,
                {"path": _PATH},
                ["path"],
            ),
            self._registration(
                "list_dir",
                "List what is in a directory of the workspace. Directories end in a slash.",
                READS,
                {"path": _PATH},
                [],
            ),
        ]
        if self._writable:
            found.append(
                self._registration(
                    "write_file",
                    "Write a text file into the workspace, creating directories as needed.",
                    WRITES,
                    {"path": _PATH, "content": {"type": "string"}},
                    ["path", "content"],
                )
            )
            found.append(
                self._registration(
                    "delete_file",
                    "Delete a file from the workspace. This cannot be undone.",
                    DESTROYS,
                    {"path": _PATH},
                    ["path"],
                )
            )
        return found

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        arguments = inputs if isinstance(inputs, dict) else {}
        known = {r.id for r in await self.registrations()}
        if registration not in known:
            return Failed(f"no component registered as {registration!r}")
        try:
            return await self._run(registration, arguments)
        except OutsideTheRoot as refused:
            return Failed(str(refused))
        except OSError as broken:
            # A filesystem that says no is data: the agent can try another name, not a traceback.
            return Failed(f"{type(broken).__name__}: {broken}")

    async def _run(self, name: str, arguments: dict[str, JsonValue]) -> Observation:
        match name:
            case "read_file":
                return Completed(self._resolve(arguments.get("path")).read_text())
            case "list_dir":
                target = self._resolve(arguments.get("path", "."))
                return Completed(
                    sorted(f"{p.name}/" if p.is_dir() else p.name for p in target.iterdir())
                )
            case "write_file":
                target = self._resolve(arguments.get("path"))
                content = arguments.get("content")
                if not isinstance(content, str):
                    return Failed("content must be a string")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
                return Completed(
                    {"path": str(target.relative_to(self._root)), "bytes": len(content)}
                )
            case "delete_file":
                target = self._resolve(arguments.get("path"))
                target.unlink()
                return Completed({"deleted": str(target.relative_to(self._root))})
        return Failed(f"no component registered as {name!r}")  # pragma: no cover

    def _registration(
        self,
        name: str,
        description: str,
        effects: EffectProfile,
        properties: dict[str, JsonValue],
        required: list[str],
    ) -> Registration:
        return Registration(
            id=name,
            component=Component(
                interface=Interface(
                    name=name,
                    description=description,
                    input_schema={
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                ),
                effects=effects,
                provenance=Provenance(registered_by=self._source, adapter="workspace", at=self._at),
                labels=frozenset({"tool"}),
            ),
        )


__all__ = ["OutsideTheRoot", "WorkspaceComponents"]
