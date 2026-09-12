"""An environment is where effects land, and it has a mode (D48).

Three adapters each held an opinion about the same boundary — a file tool that checked paths, a
shell tool that checked nothing, a proven box for a third kind of run — and a policy permitting
workspace writes was told three different truths about what a write reaches. One of them was false
(BUG-018). Every mature agent runtime answers with one concept instead: **an environment with a
mode**, enforced once, true for every operation in it.

Three parts, and the order matters:

* **`Isolation` is what is true.** Whether writes are confined to the root, whether reads are,
  whether the network is denied — and whether any of that was *proven* by watching a denial (D36)
  rather than announced by a wrapper. Never set from a profile; set from a proof or an honest no.
* **`Mode` is what is wanted.** `read-only` · `workspace-write` · `full`, Codex's three, because
  they are the three anyone has ever needed.
* **`effects_of` is the one derivation**, isolation × mode × operation, and it is where every
  operation in an environment gets its profile. The profile is true because the environment makes
  it true, and there is exactly one place to be wrong.

**A mode is enforced or refused.** `requires` raises `CannotEnforce` at construction when the
isolation cannot make the mode true — a host that asked for confinement and cannot have it must
know, not find out. `full` asks for nothing and always works.

This lives in the runtime, below every adapter, the way the leash and the device contract do: so a
second environment never has to import the first, and rule 4 stays a property rather than a habit.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import JsonValue

from shadow_hdk.kernel.components import (
    Component,
    Interface,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.effects import EffectProfile, ScopeSet
from shadow_hdk.kernel.observations import Failed, Observation, Refused
from shadow_hdk.kernel.ports import ComponentPort
from shadow_hdk.kernel.workspace import Root, Workspace

Mode = Literal["read-only", "workspace-write", "full"]
Operation = Literal["read", "write", "delete", "list", "run"]

WORKSPACE = ScopeSet.of("workspace")
EVERYTHING = ScopeSet(everything=True)
NOTHING = ScopeSet()


@dataclass(frozen=True)
class Isolation:
    """What is **true** of an environment — set from a proof or an honest no, never from a wish."""

    writes_confined: bool
    reads_confined: bool
    network_denied: bool
    proven: bool
    """Whether a denial was *watched* (D36). A wrapper that says it confines and was never seen
    denying anything is a claim, and `requires` does not accept a claim for a confined mode."""

    @classmethod
    def none(cls) -> Isolation:
        """An ordinary host with nothing around the process: all reachable, nothing proven."""
        return cls(writes_confined=False, reads_confined=False, network_denied=False, proven=False)


class CannotEnforce(RuntimeError):
    """A mode was asked for that this environment cannot make true. Names the gap."""


def requires(isolation: Isolation, mode: Mode) -> None:
    """Enforced or refused. `full` asks for nothing; the other two ask for confined writes, a
    denied network, and a proof that both were watched to hold."""
    if mode == "full":
        return
    missing = []
    if not isolation.writes_confined:
        missing.append("writes confined to the root")
    if not isolation.network_denied:
        missing.append("the network denied")
    if not isolation.proven:
        missing.append("a proven denial (D36) rather than a claim")
    if missing:
        raise CannotEnforce(
            f"mode {mode!r} needs {', '.join(missing)}, and this environment cannot provide it; "
            f"ask for 'full' and accept that it reaches the machine, or run it somewhere confined"
        )


def effects_of(isolation: Isolation, mode: Mode, operation: Operation) -> EffectProfile:
    """The one derivation. Every operation in an environment gets its profile here and nowhere
    else, from what is true of the environment rather than what the operation claims about
    itself."""
    reads = WORKSPACE if isolation.reads_confined else EVERYTHING
    if mode == "read-only":
        writes = NOTHING
    else:
        writes = WORKSPACE if isolation.writes_confined else EVERYTHING
    reaches = not isolation.network_denied
    contained = isolation.proven and isolation.writes_confined and isolation.network_denied
    match operation:
        case "read" | "list":
            return EffectProfile(reads=reads, contained=contained)
        case "write":
            return EffectProfile(reads=reads, writes=writes, reversible=True, contained=contained)
        case "delete":
            return EffectProfile(reads=reads, writes=writes, reversible=False, contained=contained)
        case "run":
            return EffectProfile(
                reads=reads,
                writes=writes,
                reaches=reaches,
                reversible=False,
                contained=contained,
                costs=False,
            )
    raise AssertionError(f"no such operation {operation!r}")  # pragma: no cover — Literal-typed


_PATH: dict[str, JsonValue] = {"type": "string", "description": "A path inside the environment."}

OPERATIONS: tuple[tuple[str, Operation, str, dict[str, JsonValue], list[str]], ...] = (
    ("read_file", "read", "Read a text file.", {"path": _PATH}, ["path"]),
    ("list_dir", "list", "List a directory. Directories end in a slash.", {"path": _PATH}, []),
    (
        "write_file",
        "write",
        "Write a text file, creating directories as needed.",
        {"path": _PATH, "content": {"type": "string"}},
        ["path", "content"],
    ),
    ("delete_file", "delete", "Delete a file.", {"path": _PATH}, ["path"]),
    (
        "run_shell",
        "run",
        "Run a shell command in the environment and return what it printed.",
        {"command": {"type": "string"}},
        ["command"],
    ),
    (
        "run_python",
        "run",
        "Run a Python script in the environment and return what it printed.",
        {"source": {"type": "string"}},
        ["source"],
    ),
)
"""The six operations every environment offers, whatever it is made of."""


class Environment(ComponentPort):
    """The shape every environment has: five operations, one derivation, one mode.

    A subclass supplies the mechanism — `_read`, `_write`, `_list`, `_run` — and its `Isolation`.
    This class supplies everything else: the registrations with their derived profiles, the mode
    check at construction, and the refusal of a write in `read-only` **before** governance is
    asked, because a mode is the environment's own promise and not one it outsources.
    """

    def __init__(
        self,
        root: Path | None,
        *,
        mode: Mode,
        isolation: Isolation,
        source: str = "environment",
        at: str = "",
        workspace: Workspace | None = None,
    ) -> None:
        requires(isolation, mode)
        # One root or many (D76): `workspace` names them; `root` alone is the one-root workspace
        # every earlier caller meant, and `self.root` stays the primary's path for them.
        self.workspace: Workspace = resolved(workspace or Workspace.of(root or Path.cwd()))
        self.root = Path(self.workspace.primary.path)
        self.mode: Mode = mode
        self.isolation = isolation
        self._source = source
        self._at = at

    @property
    def roots(self) -> tuple[Root, ...]:
        return self.workspace.roots

    def root_path(self, root: Root) -> Path:
        return Path(root.path)

    # ------------------------------------------------------------------ the mechanism

    async def _read(self, path: str) -> str:
        raise NotImplementedError

    async def _write(self, path: str, content: str) -> int:
        raise NotImplementedError

    async def _delete(self, path: str) -> None:
        raise NotImplementedError

    async def _list(self, path: str) -> list[str]:
        raise NotImplementedError

    async def _run(self, argv: list[str]) -> Observation:
        raise NotImplementedError

    async def close(self) -> None:
        """Whatever the mechanism holds open, let go."""

    # ------------------------------------------------------------------ re-opening (D76)

    def _prove_now(self, workspace: Workspace, mode: Mode) -> Isolation:
        """What is true of this mechanism for *that* workspace in *that* mode — watched again,
        never carried over. A subclass whose isolation cannot change answers with what it has."""
        raise NotImplementedError

    async def reopen(self, *, workspace: Workspace | None = None, mode: Mode | None = None) -> None:
        """The same environment on a different workspace or in a different mode — a root added
        while the thread runs, a mode that needs another sandbox — proven before it is believed
        (D36) and refused, unchanged, where it cannot be (`CannotEnforce`)."""
        wanted_workspace = resolved(workspace) if workspace is not None else self.workspace
        wanted_mode: Mode = mode or self.mode
        isolation = self._prove_now(wanted_workspace, wanted_mode)
        requires(isolation, wanted_mode)
        self.workspace = wanted_workspace
        self.root = Path(wanted_workspace.primary.path)
        self.mode = wanted_mode
        self.isolation = isolation

    # ------------------------------------------------------------------ the port

    async def registrations(self) -> Sequence[Registration]:
        return [
            Registration(
                id=name,
                component=Component(
                    interface=Interface(
                        name=name,
                        description=f"{description} Mode: {self.mode}. {self.workspace.describe()}",
                        input_schema={
                            "type": "object",
                            "properties": properties,
                            "required": required,
                        },
                    ),
                    effects=effects_of(self.isolation, self.mode, operation),
                    provenance=Provenance(
                        registered_by=self._source, adapter="environment", at=self._at
                    ),
                ),
            )
            for name, operation, description, properties, required in OPERATIONS
            if not (self.mode == "read-only" and operation in ("write", "delete"))
        ]

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        arguments = inputs if isinstance(inputs, dict) else {}
        try:
            match registration:
                case "read_file":
                    return _completed(await self._read(str(arguments.get("path", ""))))
                case "list_dir":
                    return _completed(await self._list(str(arguments.get("path", "") or ".")))
                case "write_file":
                    if self.mode == "read-only":
                        return Refused("this environment is read-only; a write is not offered")
                    written = await self._write(
                        str(arguments.get("path", "")), str(arguments.get("content", ""))
                    )
                    return _completed({"path": str(arguments.get("path", "")), "bytes": written})
                case "delete_file":
                    if self.mode == "read-only":
                        return Refused("this environment is read-only; a delete is not offered")
                    await self._delete(str(arguments.get("path", "")))
                    return _completed({"deleted": str(arguments.get("path", ""))})
                case "run_shell":
                    command = arguments.get("command")
                    if not isinstance(command, str):
                        return Failed("run_shell needs `command`, a string")
                    return await self._run(["/bin/sh", "-c", command])
                case "run_python":
                    source = arguments.get("source")
                    if not isinstance(source, str):
                        return Failed("run_python needs `source`, a string")
                    return await self._run(["python3", "-c", source])
        except OutsideTheRoot as outside:
            return Refused(str(outside))
        except (OSError, ValueError) as broken:
            # `ValueError` is what a NUL byte in a path raises; a path is data the model made up,
            # and a traceback for it would be D7's "a component raising is a failure" turned on
            # its head.
            return Failed(f"{type(broken).__name__}: {broken}")
        return Failed(f"no component registered as {registration!r}")

    # ------------------------------------------------------------------ paths

    def inside(self, given: str) -> Path:
        """A path resolved against a root and required to stay under one — what the workspace
        adapter did, kept, because a confined mode that resolved `..` out of the root would be a
        confinement the mode did not admit. Hard links are refused for the same reason as before.

        Which root (D76): an absolute path is whichever root it lies under; `name/rest` where
        `name` is a root's name is that root; anything else is relative to the primary."""
        candidate = self._resolve(given)
        if not any(
            candidate == Path(r.path) or candidate.is_relative_to(r.path) for r in self.roots
        ):
            names = ", ".join(r.name for r in self.roots)
            raise OutsideTheRoot(
                f"{given!r} resolves outside the environment's root"
                + (f"s ({names})" if len(self.roots) > 1 else "")
            )
        try:
            found = candidate.lstat()
        except (OSError, ValueError):
            return candidate
        if found.st_nlink > 1 and candidate.is_file():
            raise OutsideTheRoot(
                f"{given!r} is a hard link: {found.st_nlink} names reach this file, and the "
                "environment cannot tell whether one of them is outside it"
            )
        return candidate

    def _resolve(self, given: str) -> Path:
        as_path = Path(given)
        if as_path.is_absolute():
            return as_path.resolve()
        head = as_path.parts[0] if as_path.parts else ""
        if head and self.workspace.has(head) and head != self.workspace.primary.name:
            return (Path(self.workspace.named(head).path) / Path(*as_path.parts[1:])).resolve()
        if head and head == self.workspace.primary.name and len(self.roots) > 1:
            # `finance/x` when finance is the primary: the primary has no directory of its own
            # name unless it really does — prefer the root, as the description promised.
            named = (self.root / Path(*as_path.parts[1:])).resolve()
            literal = (self.root / given).resolve()
            return literal if literal.exists() else named
        return (self.root / given).resolve()


def resolved(workspace: Workspace) -> Workspace:
    """The kernel's roots with their paths resolved here, where the filesystem is — and refused
    where one root lies inside another, which the kernel cannot know."""
    resolved = Workspace(tuple(Root(r.name, str(Path(r.path).resolve())) for r in workspace.roots))
    for a in resolved.roots:
        for b in resolved.roots:
            if a is not b and a.path != b.path and Path(a.path).is_relative_to(b.path):
                raise ValueError(f"root {a.name!r} is inside root {b.name!r}")
    return resolved


class OutsideTheRoot(Exception):
    """A path the environment will not touch, and why."""


def _completed(output: JsonValue) -> Observation:
    from shadow_hdk.kernel.observations import Completed

    return Completed(output)


__all__ = [
    "resolved",
    "output_activity",
    "OPERATIONS",
    "CannotEnforce",
    "Environment",
    "Isolation",
    "Mode",
    "Operation",
    "OutsideTheRoot",
    "effects_of",
    "requires",
]


def output_activity() -> Callable[[str], None] | None:
    """A running command's output, as it prints, onto the run's activity (D63).

    Bound to the run executing *now* — `run_leashed` calls back from its own reading tasks, where
    no step is executing — so the context is captured here and the chunk goes to it. No run, no
    activity: a command run outside a run prints to nobody, which is right.
    """
    from shadow_hdk.runtime.bindings import current_run

    context = current_run()
    if context is None:
        return None
    step = context.step or ""

    def heard(chunk: str) -> None:
        context.activity_now("output", chunk, step=step)

    return heard
