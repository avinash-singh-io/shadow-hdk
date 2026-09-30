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
from typing import Literal

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


__all__ = [
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
