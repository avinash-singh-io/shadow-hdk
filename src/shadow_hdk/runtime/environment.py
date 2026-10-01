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

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import JsonValue

from shadow_hdk.kernel.capabilities import (
    AccessBoundary,
    CapabilityEvidence,
    EnvironmentCapabilities,
    EnvironmentRequirements,
    ExecutionRequirements,
    IncompatibleCapabilities,
    ProviderCapabilities,
    SecretPosture,
    check_compatibility,
)
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
    secrets_denied: bool | None = None
    """True when denial is established, false when secrets remain reachable, and None when this
    mechanism has not established either. Read confinement alone is not proof of secret denial."""
    mechanism: str = ""
    """What was watched denying — `seatbelt`, `landlock`, `bubblewrap`, a box backend's name — or
    empty where nothing was. A machine may have more than one way to confine a process and the
    proof decides which is in force (Epic 0010, D133); the name is on the evidence so a host reads
    *which*, not only *whether*."""

    @classmethod
    def none(cls) -> Isolation:
        """An ordinary host with nothing around the process: all reachable, nothing proven."""
        return cls(
            writes_confined=False,
            reads_confined=False,
            network_denied=False,
            proven=False,
            secrets_denied=False,
        )


class CannotEnforce(RuntimeError):
    """A mode was asked for that this environment cannot make true. Names the gap."""


MODES: tuple[Mode, ...] = ("read-only", "workspace-write", "full")


def mode_named(name: str) -> Mode | None:
    """The environment mode a string names, or None — the one place a string read from a record
    or a spec becomes a `Mode`, so a caller decides what an unknown name means."""
    for mode in MODES:
        if name == mode:
            return mode
    return None


def requires(isolation: Isolation, mode: Mode) -> None:
    """Enforced or refused. `full` asks for nothing; the other two ask for confined writes, a
    denied network, and a proof that both were watched to hold. The name is checked first: a
    confined isolation would satisfy any name that is not `full`, so an unknown mode reached the
    sandbox as a confined one (found by the spec sync)."""
    if mode not in MODES:
        raise ValueError(f"{mode!r} is not an environment mode; the modes are {list(MODES)}")
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


def capabilities_of(isolation: Isolation, mode: Mode) -> EnvironmentCapabilities:
    """Project what is true through the selected mode; never promote a claim into proof."""
    writes: AccessBoundary = (
        "none" if mode == "read-only" else ("workspace" if isolation.writes_confined else "machine")
    )
    secrets: SecretPosture = (
        "denied"
        if isolation.secrets_denied is True
        else ("ambient" if isolation.secrets_denied is False else "unknown")
    )
    # The evidence names the mechanism where one was watched: "landlock confines writes" tells a
    # host which of a machine's ways is in force; "isolation confines writes" only that one is.
    by = isolation.mechanism or "isolation"
    evidence = (
        CapabilityEvidence(
            "reads",
            "derived",
            f"{by} confines reads" if isolation.reads_confined else "reads are not confined",
        ),
        CapabilityEvidence(
            "writes",
            "derived",
            "read-only mode offers no writes"
            if mode == "read-only"
            else (f"{by} confines writes" if isolation.writes_confined else "writes are open"),
        ),
        CapabilityEvidence(
            "network",
            "derived",
            f"{by} denies network" if isolation.network_denied else "network is available",
        ),
        CapabilityEvidence(
            "secrets",
            "derived" if isolation.secrets_denied is not None else "unknown",
            (
                "isolation denies ambient secrets"
                if isolation.secrets_denied is True
                else "ambient secrets remain reachable"
                if isolation.secrets_denied is False
                else ""
            ),
        ),
        CapabilityEvidence(
            "proof",
            "measured" if isolation.proven else "unknown",
            "construction-time denial probes" if isolation.proven else "",
        ),
    )
    return EnvironmentCapabilities(
        reads="workspace" if isolation.reads_confined else "machine",
        writes=writes,
        network="denied" if isolation.network_denied else "available",
        secrets=secrets,
        proven=isolation.proven,
        evidence=evidence,
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

_LIMIT: dict[str, JsonValue] = {
    "type": "integer",
    "description": "At most this many results. A trimmed result says so.",
}

OPERATIONS: tuple[tuple[str, Operation, str, dict[str, JsonValue], list[str]], ...] = (
    (
        "read_file",
        "read",
        "Read a text file, or a range of its lines with `offset` (the first line, counting from "
        "1) and `limit` (how many).",
        {
            "path": _PATH,
            "offset": {"type": "integer", "description": "First line to read, counting from 1."},
            "limit": {"type": "integer", "description": "How many lines to read."},
        },
        ["path"],
    ),
    ("list_dir", "list", "List a directory. Directories end in a slash.", {"path": _PATH}, []),
    (
        "edit_file",
        "write",
        "Change regions of a text file. Each edit replaces `old` with `new`, in order. An `old` "
        "that is absent, or that appears more than once, is refused and **nothing is written** — "
        "name more of the surrounding text so it matches exactly once.",
        {
            "path": _PATH,
            "edits": {
                "type": "array",
                "description": "The changes, applied in order. All of them land, or none do.",
                "items": {
                    "type": "object",
                    "properties": {
                        "old": {"type": "string", "description": "Text to find, matching once."},
                        "new": {"type": "string", "description": "What replaces it."},
                    },
                    "required": ["old", "new"],
                },
            },
        },
        ["path", "edits"],
    ),
    (
        "run_background",
        "run",
        "Start a long-running command and return immediately with a job name — a dev server, a "
        "file watcher, a long test suite. Read what it has said with `job_output`; stop it with "
        "`kill_job`. Every job ends when the environment does.",
        {"command": {"type": "string"}},
        ["command"],
    ),
    (
        "job_output",
        "read",
        "What a background job has said since you last asked, and whether it is still running. "
        "`exit_code` is null while it runs.",
        {"job": {"type": "string", "description": "The job name `run_background` gave you."}},
        ["job"],
    ),
    (
        "kill_job",
        "run",
        "Stop a background job and everything it started.",
        {"job": {"type": "string", "description": "The job name `run_background` gave you."}},
        ["job"],
    ),
    (
        "apply_patch",
        "write",
        "Change regions across several files as one act. Every edit in every file is checked "
        "first: if any one of them is absent or ambiguous, **nothing is written anywhere**. Name "
        "each file once.",
        {
            "files": {
                "type": "array",
                "description": "The files to change. All of them land, or none do.",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": _PATH,
                        "edits": {
                            "type": "array",
                            "description": "The changes to this file, applied in order.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "old": {
                                        "type": "string",
                                        "description": "Text to find, matching once.",
                                    },
                                    "new": {"type": "string", "description": "What replaces it."},
                                },
                                "required": ["old", "new"],
                            },
                        },
                    },
                    "required": ["path", "edits"],
                },
            }
        },
        ["files"],
    ),
    (
        "move_file",
        "write",
        "Move or rename a file. A destination that already exists is refused rather than "
        "overwritten.",
        {
            "from": {"type": "string", "description": "The path to move."},
            "to": {"type": "string", "description": "Where it goes. Directories are created."},
        },
        ["from", "to"],
    ),
    (
        "glob",
        "list",
        "Find files by a path pattern — `*` within one segment, `**` across segments, `?` one "
        "character. Files only; paths come back relative to the workspace root.",
        {
            "pattern": {"type": "string", "description": "A glob, e.g. `**/*.py`."},
            "path": {"type": "string", "description": "Where to start. Default: the root."},
            "limit": _LIMIT,
        },
        ["pattern"],
    ),
    (
        "grep",
        "read",
        "Search file contents for a regular expression. Each match gives its path, its line "
        "number and the line.",
        {
            "pattern": {"type": "string", "description": "A regular expression."},
            "path": {"type": "string", "description": "Where to start. Default: the root."},
            "glob": {"type": "string", "description": "Only search files matching this glob."},
            "limit": _LIMIT,
        },
        ["pattern"],
    ),
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
"""The operations every environment offers, whatever it is made of.

`glob` and `grep` derive from `list` and `read` (ENH-041), so they are **read-class**: their
profiles carry no writes and the shipped `ask` mode does not stop a person for them. That is the
point of them — a search that asks permission is a search nobody runs, and without one every
search was a `run_shell`, which `ask` rightly does stop."""


class Environment(ComponentPort):
    """The shape every environment has: the operations, one derivation, one mode.

    A subclass supplies the mechanism — `_read`, `_write`, `_list`, `_run` — and its `Isolation`.
    Search is **not** among them: `glob` and `grep` are built here on `_list` and `_read`, so every
    environment gains them at once and none has to implement anything (an adapter with something
    faster may override `_glob`/`_grep`; none has to). This class supplies everything else: the
    registrations with their derived profiles, the mode
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
        requirements: EnvironmentRequirements | None = None,
    ) -> None:
        requires(isolation, mode)
        available = capabilities_of(isolation, mode)
        compatibility = check_compatibility(
            ProviderCapabilities(),
            available,
            ExecutionRequirements(environment=requirements or EnvironmentRequirements()),
        )
        if not compatibility.ok:
            raise IncompatibleCapabilities(compatibility, available_environment=available)
        # One root or many (D76): `workspace` names them; `root` alone is the one-root workspace
        # every earlier caller meant, and `self.root` stays the primary's path for them.
        self.workspace: Workspace = resolved(workspace or Workspace.of(root or Path.cwd()))
        self.root = Path(self.workspace.primary.path)
        self.mode: Mode = mode
        self.isolation = isolation
        self._source = source
        self._at = at
        self._requirements = requirements
        self._jobs: dict[str, _Job] = {}
        """Background jobs this environment owns (D157). `close()` ends every one."""

    @property
    def capabilities(self) -> EnvironmentCapabilities:
        return capabilities_of(self.isolation, self.mode)

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
        """Whatever the mechanism holds open, let go — including every background job this
        environment owns (D157). A subclass overriding this calls `super().close()`."""
        await self._end_every_job()

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
        available = capabilities_of(isolation, wanted_mode)
        compatibility = check_compatibility(
            ProviderCapabilities(),
            available,
            ExecutionRequirements(environment=self._requirements or EnvironmentRequirements()),
        )
        if not compatibility.ok:
            raise IncompatibleCapabilities(compatibility, available_environment=available)
        self.workspace = wanted_workspace
        self.root = Path(wanted_workspace.primary.path)
        self.mode = wanted_mode
        self.isolation = isolation

    # ------------------------------------------------- changing part of a file, not all of it

    async def _edit(self, path: str, edits: JsonValue) -> Observation:
        """Replace regions of one file, all of them or none (ENH-042).

        The validation lives in `edited_by`, because `apply_patch` needs exactly the same
        refusals across many files (D158) and two copies of them would drift.
        """
        content = await self._read(path)
        applied = edited_by(path, content, edits)
        if isinstance(applied, Refused):
            return applied
        written = await self._write(path, applied)
        return _completed(
            {
                "path": path,
                "edits": len(edits) if isinstance(edits, list) else 0,
                "bytes": written,
                # The same block a `write_file` carries (ENH-044). `old` and `new` are already on
                # this call's inputs, so a host could assemble the change itself — but only for an
                # edit, and a files-changed panel that reads one shape for four operations and a
                # different one for the fifth is a panel with a bug waiting in it.
                "change": changed(path, content, applied),
            }
        )

    async def _patch(self, files: JsonValue) -> Observation:
        """One act across many files, or nothing (ENH-042, D159).

        **Read all, validate all, write all.** A patch that wrote three files and then refused the
        fourth would leave a workspace no record describes — the failure `edit_file` already
        refuses within one file, multiplied by the size of the batch. Atomicity is the whole of
        what makes this different from a loop over `edit_file`, so the writes do not begin until
        every edit in the batch is known to apply.

        The refusals are `edited_by`'s, unchanged, because a caller who has learnt what an absent
        `old` means for one file should not have to learn it again for many.
        """
        if not isinstance(files, list) or not files:
            return Refused(
                "a patch names the files to change: `files` is a list of {path, edits}, and an "
                "empty list changes nothing"
            )
        planned: list[tuple[str, str, str]] = []
        named: set[str] = set()
        for index, entry in enumerate(files, start=1):
            if not isinstance(entry, dict):
                return Refused(f"file {index} is not an object with `path` and `edits`")
            path, edits = entry.get("path"), entry.get("edits")
            if not isinstance(path, str) or not path:
                return Refused(f"file {index} needs `path`")
            if path in named:
                return Refused(
                    f"{path} is named twice in one patch, so which edits apply to what is not "
                    "said — nothing was written. Put every change to a file in its own entry."
                )
            named.add(path)
            try:
                content = await self._read(path)
            except FileNotFoundError:
                return Refused(f"{path} is not there — nothing was written")
            applied = edited_by(path, content, edits)
            if isinstance(applied, Refused):
                return applied
            planned.append((path, content, applied))
        written: list[JsonValue] = []
        for path, before, after in planned:
            await self._write(path, after)
            written.append({"path": path, "change": changed(path, before, after)})
        return _completed({"files": len(planned), "changed": written})

    async def _relocate(self, source: str, destination: str) -> Observation:
        """Move a file, refusing to overwrite (ENH-042).

        **The refusal is what keeps a move `write`-class.** Nothing is destroyed, so the act is
        reversible by moving it back — which is exactly what `reversible` claims of a write. A
        move that clobbered would be a `delete` wearing a write's profile, and the content it
        destroyed would be on no record anywhere.
        """
        if not source or not destination:
            return Refused("a move needs `from` and `to`")
        if await self._there(destination):
            return Refused(
                f"{destination} already exists and a move does not overwrite — nothing was "
                "moved. Move to another name, or delete that one first."
            )
        await self._move(source, destination)
        return _completed({"from": source, "to": destination})

    # ------------------------------------------------------- a job that outlives its step (D157)

    async def _start_job(self, argv: list[str]) -> Any:
        """Start a process that outlives the step that asked for it, wrapped by whatever confines
        this environment. An environment with no way to do it does not implement this, and
        `run_background` is refused rather than crashing — the refuse-not-crash default every
        port default in this project keeps.
        """
        raise NotImplementedError

    async def _background(self, command: JsonValue) -> Observation:
        """Start a job and hand back its name (ENH-042, D157).

        The environment owns it, not the step — a dev server whose owner was the step that started
        it would be killed the moment that step returned, which is the whole point of not being
        `run_shell`. `close()` ends every job, so the obligation moves up a level rather than
        being dropped: BUG-019 is what dropping it looks like.
        """
        if not isinstance(command, str) or not command:
            return Refused("a background job needs `command`, a string")
        try:
            process = await self._start_job(["/bin/sh", "-c", command])
        except NotImplementedError:
            return Refused(
                "this environment cannot run a job in the background; use `run_shell` and wait"
            )
        except OSError as broken:
            return Failed(f"{type(broken).__name__}: {broken}")
        name = f"job-{len(self._jobs) + 1}"
        self._jobs[name] = _Job(name=name, command=command, process=process)
        self._jobs[name].start_reading(self._output_cap())
        return _completed({"job": name, "command": command, "pid": process.pid})

    def _output_cap(self) -> int:
        """How much of a job's output is kept. A subclass with its own limit says so."""
        return 64_000

    async def _job_told(self, name: JsonValue) -> Observation:
        """What a job has said since last asked, and whether it is still going (D160).

        Status and output arrive together because polling twice to learn one thing is a turn a
        model wasted. The output is **what is new** rather than the whole buffer: re-reading it on
        every poll would bill a product for the same bytes over and over, which is the cost it
        would actually feel on a long build.
        """
        job = self._jobs.get(str(name))
        if job is None:
            return Refused(f"no job called {str(name)!r} was started here")
        return _completed(job.told())

    async def _kill(self, name: JsonValue) -> Observation:
        job = self._jobs.get(str(name))
        if job is None:
            return Refused(f"no job called {str(name)!r} was started here")
        return _completed({"job": job.name, "killed": job.end()})

    async def _end_every_job(self) -> None:
        """Every job this environment started, ended (D157). Called by `close`, so a subclass
        overriding `close` must call `super().close()` — and one test per environment checks the
        operating system rather than this bookkeeping, because BUG-019 was invisible to
        bookkeeping."""
        for job in list(self._jobs.values()):
            job.end()
        self._jobs.clear()

    async def _prior(self, path: str) -> tuple[str, bool, bool]:
        """What is at `path` before a write touches it: `(text, existed, readable)`.

        **This never raises** (D155). Capturing what changed is record-keeping, and a write that
        failed because the record-keeping failed would be the tail wagging the dog — the act the
        mode admitted and the person approved must still happen. A prior state that cannot be read
        as text (a binary file, a denied read) comes back marked rather than thrown, and the change
        says so instead of claiming the file was empty.

        A path the environment will not touch is *also* swallowed here, and safely: this runs
        before the write, so `_write` raises `OutsideTheRoot` a moment later and the act is refused
        by the handler that has always refused it. Nothing is written on the strength of this.
        """
        try:
            return await self._read(path), True, True
        except FileNotFoundError:
            return "", False, True
        except Exception:
            return "", True, False

    async def _there(self, path: str) -> bool:
        """Whether something is already at `path`, asked through `_list` so every environment
        answers it without implementing anything."""
        parent, _, name = path.strip("/").rpartition("/")
        try:
            entries = await self._list(parent or ".")
        except Exception:
            return False
        return name in entries or f"{name}/" in entries

    async def _move(self, source: str, destination: str) -> None:
        """Relocate, on the primitives every environment already has.

        The destination is written **before** the source is removed, so a failure part-way leaves
        the original rather than nothing. This round-trips the content through text, which is what
        this whole surface does (`_read` returns `str`), so it inherits the same limit as
        `read_file`. An adapter that can rename in place should override this — `LocalEnvironment`
        does, which also makes the move atomic.
        """
        content = await self._read(source)
        await self._write(destination, content)
        await self._delete(source)

    # ------------------------------------------------------- search, over the primitives

    async def _walk(self, start: str) -> list[str]:
        """Every file under `start`, as paths relative to the root, sorted.

        Built on `_list` alone, so **no environment has to implement anything** for search to
        work — a sandbox, a remote root and a local directory all gain it at once. An adapter
        that can do better (a real `find`, an index) can override `_glob` and `_grep`; none has
        to. `_list` failing on one directory skips that directory rather than the walk: a tree
        with one unreadable corner still searches.
        """
        base = "" if start in ("", ".") else start.strip("/")
        found: list[str] = []
        pending = [base]
        seen: set[str] = set()
        while pending:
            here = pending.pop()
            if here in seen or len(found) > _WALK_CEILING:
                continue
            seen.add(here)
            try:
                entries = await self._list(here or ".")
            except Exception:
                continue  # an unreadable directory is not a failed search
            for entry in entries:
                joined = f"{here}/{entry}" if here else entry
                if entry.endswith("/"):
                    pending.append(joined.rstrip("/"))
                else:
                    found.append(joined)
        return sorted(found)

    async def _glob(self, pattern: str, start: str, limit: int) -> Observation:
        if not pattern:
            return Refused("a glob needs a pattern; `**/*.py` finds every Python file")
        base = "" if start in ("", ".") else start.strip("/")
        matcher = _glob_matcher(pattern)
        # Matched **relative to where the search started**, returned relative to the root: the
        # pattern is about the shape of the tree under `path`, and a path is one vocabulary.
        hits = [
            found
            for found in await self._walk(start)
            if matcher.match(found[len(base) + 1 :] if base else found)
        ]
        if len(hits) > limit:
            trimmed: list[JsonValue] = list(hits[:limit])
            return _completed({"paths": trimmed, "truncated": True, "found": len(hits)})
        return _completed(list(hits))

    async def _grep(self, pattern: str, start: str, only: JsonValue, limit: int) -> Observation:
        if not pattern:
            return Refused("a grep needs a pattern; it is a regular expression")
        try:
            wanted = re.compile(pattern)
        except re.error as bad:
            return Refused(f"{pattern!r} is not a regular expression: {bad}")
        base = "" if start in ("", ".") else start.strip("/")
        narrowing = _glob_matcher(str(only)) if isinstance(only, str) and only else None
        matches: list[JsonValue] = []
        for found in await self._walk(start):
            relative = found[len(base) + 1 :] if base else found
            if narrowing is not None and not narrowing.match(relative):
                continue
            try:
                content = await self._read(found)
            except Exception:
                continue  # binary, or gone since the walk: skip the file, keep the search
            for number, line in enumerate(content.splitlines(), start=1):
                if wanted.search(line):
                    matches.append({"path": found, "line": number, "text": line})
                    if len(matches) >= limit:
                        return _completed({"matches": matches, "truncated": True})
        return _completed(matches)

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
                            "required": list(required),
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
                    whole = await self._read(str(arguments.get("path", "")))
                    return _ranged(whole, arguments.get("offset"), arguments.get("limit"))
                case "glob":
                    return await self._glob(
                        str(arguments.get("pattern", "")),
                        str(arguments.get("path", "") or "."),
                        _as_limit(arguments.get("limit"), GLOB_LIMIT),
                    )
                case "grep":
                    return await self._grep(
                        str(arguments.get("pattern", "")),
                        str(arguments.get("path", "") or "."),
                        arguments.get("glob"),
                        _as_limit(arguments.get("limit"), GREP_LIMIT),
                    )
                case "list_dir":
                    listed: list[JsonValue] = list(
                        await self._list(str(arguments.get("path", "") or "."))
                    )
                    return _completed(listed)
                case "write_file":
                    if self.mode == "read-only":
                        return Refused("this environment is read-only; a write is not offered")
                    path, content = (
                        str(arguments.get("path", "")),
                        str(arguments.get("content", "")),
                    )
                    before, existed, readable = await self._prior(path)
                    written = await self._write(path, content)
                    return _completed(
                        {
                            "path": path,
                            "bytes": written,
                            "change": changed(
                                path,
                                before,
                                content,
                                created=not existed,
                                before_unreadable=not readable,
                            ),
                        }
                    )
                case "edit_file":
                    if self.mode == "read-only":
                        return Refused("this environment is read-only; an edit is not offered")
                    return await self._edit(str(arguments.get("path", "")), arguments.get("edits"))
                case "apply_patch":
                    if self.mode == "read-only":
                        return Refused("this environment is read-only; a patch is not offered")
                    return await self._patch(arguments.get("files"))
                case "move_file":
                    if self.mode == "read-only":
                        return Refused("this environment is read-only; a move is not offered")
                    return await self._relocate(
                        str(arguments.get("from", "")), str(arguments.get("to", ""))
                    )
                case "delete_file":
                    if self.mode == "read-only":
                        return Refused("this environment is read-only; a delete is not offered")
                    gone = str(arguments.get("path", ""))
                    # The one act whose own inputs say nothing about what it destroyed: a path,
                    # and the content on no record anywhere (ENH-044, lane P's item 7).
                    before, _, readable = await self._prior(gone)
                    await self._delete(gone)
                    return _completed(
                        {
                            "deleted": gone,
                            "change": changed(
                                gone,
                                before,
                                "",
                                deleted=True,
                                before_unreadable=not readable,
                            ),
                        }
                    )
                case "run_background":
                    if self.mode == "read-only":
                        return Refused(
                            "this environment is read-only; running a command is not offered"
                        )
                    return await self._background(arguments.get("command"))
                case "job_output":
                    return await self._job_told(arguments.get("job", ""))
                case "kill_job":
                    if self.mode == "read-only":
                        return Refused(
                            "this environment is read-only; running a command is not offered"
                        )
                    return await self._kill(arguments.get("job", ""))
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
            # Another root's name wins — the rule the tools describe — and never a look at the
            # filesystem: the one spelling this would hide (an entry of the primary named like
            # a root) is refused when the root is named, in `resolved`. The primary's own name is
            # not an address: a relative path is relative to it, so a repository `foo` with a
            # package `foo/` inside keeps meaning what it always meant.
            return (Path(self.workspace.named(head).path) / Path(*as_path.parts[1:])).resolve()
        return (self.root / given).resolve()


def resolved(workspace: Workspace) -> Workspace:
    """The kernel's roots with their paths resolved here, where the filesystem is — and refused
    where one root lies inside another, which the kernel cannot know."""
    resolved = Workspace(tuple(Root(r.name, str(Path(r.path).resolve())) for r in workspace.roots))
    for a in resolved.roots:
        for b in resolved.roots:
            if a is not b and a.path != b.path and Path(a.path).is_relative_to(b.path):
                raise ValueError(f"root {a.name!r} is inside root {b.name!r}")
    primary = Path(resolved.primary.path)
    for root in resolved.roots[1:]:
        # Another root's name wins in `inside()`; an entry of the primary spelled the same way
        # would be unreachable by that name — refused here, once, rather than guessed at every
        # path. The primary's own name is not an address, so it is not checked.
        if (primary / root.name).exists():
            raise ValueError(
                f"root {root.name!r} shares its name with `{root.name}/` in the primary "
                f"({primary}); name the root differently"
            )
    return resolved


class OutsideTheRoot(Exception):
    """A path the environment will not touch, and why."""


GLOB_LIMIT = 1000
"""How many paths a `glob` returns before it says it stopped."""

GREP_LIMIT = 200
"""How many matches a `grep` returns before it says it stopped."""

CHANGE_DIFF_BYTES = 4_096
"""How much of a change's diff travels on the record (D154, ENH-044).

**One constant, named once.** A cap written into three call sites is three caps, and the first one
somebody tunes is the one they can find. A host that needs the whole change reads the file; what
this carries is enough to render a files-changed panel and an approval preview, which is what it
was asked for.

Why a **diff** rather than the before and after content: lane P settled the shape — content to a
cap, `truncated` past it, and no per-file version history, because git keeps that for a repository.
Before-and-after cut at this size shows nothing at all of a small change to a large file; a diff of
the same change shows all of it. The line counts beside it are computed from the *whole* diff, so
they stay exact when the text is cut.
"""

_WALK_CEILING = 50_000
"""A walk this big is a workspace nobody meant to search whole; stop rather than hang."""


def _as_limit(given: JsonValue, fallback: int) -> int:
    """A caller's limit, or the default. A nonsense one is the default rather than a refusal:
    a search is not the place to argue about an argument."""
    if isinstance(given, bool) or not isinstance(given, int) or given < 1:
        return fallback
    return min(given, fallback)


def _glob_matcher(pattern: str) -> re.Pattern[str]:
    """A glob as a regular expression, with `**` crossing separators and `*` not.

    `fnmatch` is no good here: its `*` matches `/` too, so `src/*.py` would find
    `src/deep/c.py`. The distinction between "in this directory" and "anywhere below" is the
    whole of what a caller means by `*` versus `**`.
    """
    out = ["(?s:"]
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    out.append(r")\Z")
    return re.compile("".join(out))


def _ranged(whole: str, offset: JsonValue, limit: JsonValue) -> Observation:
    """A file, or the lines a caller asked for (ENH-041).

    Neither given, this is `read_file` exactly as it always was: the whole file, a plain string.
    A range past the end is **refused, naming the line count** — an empty string would read to a
    model as a file with nothing in it, and it would stop looking.
    """
    if offset is None and limit is None:
        return _completed(whole)
    lines = whole.splitlines(keepends=True)
    first = offset if isinstance(offset, int) and not isinstance(offset, bool) else 1
    if first < 1:
        return Refused(f"offset {first} is not a line number; lines count from 1")
    if first > len(lines):
        return Refused(f"offset {first} is past the end of the file, which has {len(lines)} lines")
    how_many = limit if isinstance(limit, int) and not isinstance(limit, bool) else 0
    start = first - 1
    chosen = lines[start:] if how_many < 1 else lines[start : start + how_many]
    return _completed("".join(chosen))


def _completed(output: JsonValue) -> Observation:
    from shadow_hdk.kernel.observations import Completed

    return Completed(output)


@dataclass
class _Job:
    """One background process the environment owns (D157), and what it has said.

    Its output is drained by a task from the moment it starts, and that is not tidiness: a child
    writing more than its pipe holds — 64 KB on Linux and macOS — blocks on `write(2)` until
    somebody reads, and a job nobody drains is a job that hangs. BUG-059 is that bug, found in a
    provider session for the same reason.
    """

    name: str
    command: str
    process: Any
    said: str = ""
    read_to: int = 0
    """How far a caller has already been told, so a poll is billed for new bytes only."""
    lost: bool = False
    """Whether the buffer overflowed and the earliest output is gone."""
    reader: Any = None

    def start_reading(self, cap: int) -> None:
        import asyncio

        async def drain(stream: Any) -> None:
            while chunk := await stream.read(4096):
                self.said += chunk.decode("utf-8", "replace")
                if len(self.said) > cap:
                    cut = len(self.said) - cap
                    self.said = self.said[cut:]
                    self.read_to = max(0, self.read_to - cut)
                    self.lost = True

        streams = [s for s in (self.process.stdout, self.process.stderr) if s is not None]
        self.reader = asyncio.gather(*(drain(s) for s in streams)) if streams else None

    def told(self) -> dict[str, JsonValue]:
        fresh = self.said[self.read_to :]
        self.read_to = len(self.said)
        code = self.process.returncode
        return {
            "job": self.name,
            "command": self.command,
            "running": code is None,
            # Unknown, never zero, while it runs — the rule `Usage` keeps for cache tokens (D141).
            "exit_code": code,
            "output": fresh,
            "truncated": self.lost,
        }

    def end(self) -> bool:
        """`True` if it was still running and had to be ended."""
        from shadow_hdk.runtime.processes import end_the_group

        if self.process.returncode is not None:
            return False
        end_the_group(self.process)
        if self.reader is not None:
            self.reader.cancel()
        return True


def edited_by(path: str, content: str, edits: JsonValue) -> str | Refused:
    """`content` with every edit applied in order, or the refusal that stopped it (ENH-042).

    Pure, and shared by `edit_file` and `apply_patch` (D158) so the refusals cannot drift apart.

    **Why the refusals are the design.** An `old` that is absent means the caller is working from a
    picture of the file that is out of date, and applying the rest of the batch would act on that
    picture. An `old` that appears twice means it did not say which one it meant, and taking the
    first is how an agent edits the wrong line and reports success. Neither returns a partial
    result, so the file a failed edit leaves behind is the file that was there — the one state both
    the model and the record already describe.
    """
    if not isinstance(edits, list) or not edits:
        return Refused(
            f"an edit names the regions to change: `edits` for {path} is a list of {{old, new}}, "
            "and an empty list would be a whole-file rewrite under another name"
        )
    edited = content
    for index, edit in enumerate(edits, start=1):
        if not isinstance(edit, dict):
            return Refused(f"edit {index} for {path} is not an object with `old` and `new`")
        old, new = edit.get("old"), edit.get("new")
        if not isinstance(old, str) or not isinstance(new, str):
            return Refused(f"edit {index} for {path} needs `old` and `new`, both strings")
        found = edited.count(old)
        if found == 0:
            return Refused(
                f"edit {index}: {old!r} is not in {path} — nothing was written. The file may "
                "not be what you last read; read it again."
            )
        if found > 1:
            return Refused(
                f"edit {index}: {old!r} appears {found} times in {path}, so which one to "
                "change is not said — nothing was written. Name more of the surrounding "
                "text so it matches once."
            )
        edited = edited.replace(old, new, 1)
    return edited


def changed(
    path: str,
    before: str,
    after: str,
    *,
    created: bool = False,
    deleted: bool = False,
    before_unreadable: bool = False,
    cap: int = CHANGE_DIFF_BYTES,
) -> dict[str, JsonValue]:
    """What a write-class act did to one file, bounded (D154, ENH-044).

    Pure over two strings, so it is testable without a filesystem and identical for every
    environment — a local root, a sandbox and a remote one all say the same thing about a change.

    `added` and `removed` are counted over the **whole** diff before it is cut, so a host reading
    `truncated` still learns the true size of what happened. They are `None` only when the prior
    state could not be read at all, because a count nobody measured must not read as zero — the
    rule `EffectProfile` set with `ASSUME_WORST` and `Usage` kept for cache tokens (D141).
    """
    import difflib

    lines = list(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )
    added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))
    diff = "".join(lines)
    over = len(diff) > cap
    return {
        "diff": diff[:cap] if over else diff,
        "truncated": over,
        "added": None if before_unreadable else added,
        "removed": None if before_unreadable else removed,
        "created": created,
        "deleted": deleted,
        "before_unreadable": before_unreadable,
    }


__all__ = [
    "CHANGE_DIFF_BYTES",
    "GLOB_LIMIT",
    "GREP_LIMIT",
    "MODES",
    "mode_named",
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
    "capabilities_of",
    "changed",
    "edited_by",
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
