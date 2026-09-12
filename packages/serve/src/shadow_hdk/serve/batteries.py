"""A battery is a file (D70): a tool every agent product asks for first — web search, web fetch —
consumed behind the component port and never built (principle 5).

A battery document names an MCP server (its command, resolved on PATH or through an environment
variable a deployment sets) — or a Python callable — the server's tools to expose *under the
harness's names*, and the effects a deployment vouches for each. The vouching is the point: an
MCP server that annotates nothing is assumed the worst of (the adapter's rule), and a file that
says *this reaches the web from its own process and writes nothing of ours* is what lets a mode
judge it. No rule is added for a battery: the shipped modes judge the profile as they judge any.

A registry over sources — the shipped files, a directory, a store (D66) — later shadowing
earlier by id; a document that will not load is a *problem* the registry reports, and a battery
whose command is absent is a problem naming what would install it, never a silent absence.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import shutil
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from dataclasses import fields as dataclass_fields
from importlib import resources
from pathlib import Path
from typing import Any, Literal, Protocol

from shadow_hdk.kernel import EffectProfile
from shadow_hdk.kernel.contracts import load
from shadow_hdk.kernel.ports import ComponentPort

KINDS = ("mcp", "python")
EFFECT_KEYS = frozenset(f.name for f in dataclass_fields(EffectProfile))
BATTERY_KEYS = frozenset(
    {
        "id",
        "name",
        "kind",
        "command",
        "args",
        "bin_env",
        "callable",
        "requires",
        "licence",
        "install",
        "note",
    }
)


@dataclass(frozen=True)
class BatteryTool:
    """One tool the battery exposes: the server's own name for it, and the vouched effects."""

    tool: str
    effects: EffectProfile


@dataclass(frozen=True)
class Battery:
    id: str
    name: str
    kind: Literal["mcp", "python"]
    tools: dict[str, BatteryTool]
    """The harness's name → the tool. For a Python battery the callable *is* the one tool."""
    source: str = "shipped"
    command: str = ""
    args: tuple[str, ...] = ()
    bin_env: str = ""
    """An environment variable naming the binary, read before PATH — the providers' convention."""
    callable: str = ""
    """`module.path:attribute` for a Python battery."""
    requires: str = ""
    """An import name a Python battery needs; absent, the battery is a reported problem."""
    licence: str = ""
    install: str = ""
    """What would make it run here, in the words a person would type."""
    note: str = ""

    def resolve(self, *, env: dict[str, str] | None = None) -> str | None:
        """The binary this battery runs, or `None` with the reason in `problem_running`."""
        environment = os.environ if env is None else env
        if self.bin_env and environment.get(self.bin_env):
            named = environment[self.bin_env]
            return named if Path(named).exists() else None
        return shutil.which(self.command, path=environment.get("PATH")) if self.command else None

    def problem_running(self, *, env: dict[str, str] | None = None) -> str | None:
        """Why this battery cannot run here, naming what would fix it — or `None`."""
        if self.kind == "python":
            module = self.requires or self.callable.split(":", 1)[0]
            try:
                importlib.import_module(module)
            except ImportError:
                return (
                    f"battery {self.id!r} needs the Python package {module!r}, which is not "
                    f"installed here — {self.install or 'install it'}"
                )
            return None
        if self.resolve(env=env) is None:
            where = f" or ${self.bin_env}" if self.bin_env else ""
            return (
                f"battery {self.id!r} needs {self.command!r} on PATH{where}, which is not here — "
                f"{self.install or 'install it'}"
            )
        return None


def _effects(raw: Any, *, where: str) -> EffectProfile:
    if not isinstance(raw, dict):
        raise ValueError(f"{where}: effects must be a table of effect fields")
    unknown = sorted(set(raw) - EFFECT_KEYS)
    if unknown:
        raise ValueError(
            f"{where}: unknown effect field(s) {unknown}; the vocabulary is {sorted(EFFECT_KEYS)}"
        )
    shaped = dict(raw)
    for scopes in ("reads", "writes"):
        given = shaped.get(scopes)
        if isinstance(given, list):
            shaped[scopes] = {"names": [str(n) for n in given], "everything": False}
        elif given == "everything":
            shaped[scopes] = {"names": [], "everything": True}
    return load(json.dumps(shaped), EffectProfile)


def battery_from_document(document: Any, *, source: str) -> Battery:
    """One battery from its document — a TOML file's tables, or a store's row (the same shape).
    Refused with the reason when it cannot be one."""
    if not isinstance(document, dict) or not isinstance(document.get("battery"), dict):
        raise ValueError("a battery document has a [battery] table")
    head: dict[str, Any] = document["battery"]
    unknown = sorted(set(head) - BATTERY_KEYS)
    if unknown:
        raise ValueError(f"[battery]: unknown key(s) {unknown}; known: {sorted(BATTERY_KEYS)}")
    battery_id = str(head.get("id", "") or "")
    if not battery_id:
        raise ValueError("[battery] needs an id")
    kind = str(head.get("kind", "") or "")
    if kind not in KINDS:
        raise ValueError(f"[battery] {battery_id!r}: kind {kind!r} is not one of {list(KINDS)}")
    command = str(head.get("command", "") or "")
    callable_ = str(head.get("callable", "") or "")
    if kind == "mcp" and not command:
        raise ValueError(f"[battery] {battery_id!r}: an mcp battery needs a command")
    if kind == "python" and (":" not in callable_):
        raise ValueError(
            f"[battery] {battery_id!r}: a python battery needs a callable as module:attribute"
        )
    raw_tools = document.get("tools", {})
    if not isinstance(raw_tools, dict):
        raise ValueError(f"[battery] {battery_id!r}: [tools] must be a table")
    tools: dict[str, BatteryTool] = {}
    for name, raw in raw_tools.items():
        if not isinstance(raw, dict):
            raise ValueError(f"[tools.{name}] must be a table")
        if "effects" not in raw:
            raise ValueError(
                f"[tools.{name}] has no effects: a battery vouches for what each tool does"
            )
        tools[str(name)] = BatteryTool(
            tool=str(raw.get("tool", name) or name),
            effects=_effects(raw["effects"], where=f"[tools.{name}]"),
        )
    if kind == "python" and len(tools) != 1:
        raise ValueError(f"[battery] {battery_id!r}: a python battery exposes exactly one tool")
    return Battery(
        id=battery_id,
        name=str(head.get("name", "") or battery_id),
        kind=kind,  # type: ignore[arg-type]
        tools=tools,
        source=source,
        command=command,
        args=tuple(str(a) for a in head.get("args", []) or []),
        bin_env=str(head.get("bin_env", "") or ""),
        callable=callable_,
        requires=str(head.get("requires", "") or ""),
        licence=str(head.get("licence", "") or ""),
        install=str(head.get("install", "") or ""),
        note=str(head.get("note", "") or ""),
    )


# ---------------------------------------------------------------------------- sources


class BatterySource(Protocol):
    async def batteries(self) -> Sequence[Battery]: ...

    async def problems(self) -> tuple[str, ...]: ...


class FileBatteries:
    """Every `*.toml` in a directory, re-read on each call; a file that will not load is a
    problem, not a crash."""

    def __init__(self, where: Path, *, source: str = "file") -> None:
        self._where = where
        self._source = source
        self._problems: tuple[str, ...] = ()

    def load(self) -> tuple[Battery, ...]:
        found: list[Battery] = []
        problems: list[str] = []
        if self._where.is_dir():
            for path in sorted(self._where.glob("*.toml")):
                try:
                    document = tomllib.loads(path.read_text(encoding="utf-8"))
                    found.append(battery_from_document(document, source=self._source))
                except (tomllib.TOMLDecodeError, ValueError) as wrong:
                    problems.append(f"{path.name}: {wrong}")
        self._problems = tuple(problems)
        return tuple(found)

    async def batteries(self) -> Sequence[Battery]:
        return self.load()

    async def problems(self) -> tuple[str, ...]:
        return self._problems


class StoreBatteries:
    """Batteries from a `Store`'s collection (D66), reloaded when its version moves."""

    def __init__(self, store: Any, collection: str = "batteries") -> None:
        self._store = store
        self._collection = collection
        self._seen = -1
        self._batteries: tuple[Battery, ...] = ()
        self._problems: tuple[str, ...] = ()

    async def batteries(self) -> Sequence[Battery]:
        version = await self._store.version(self._collection)
        if version != self._seen:
            found: list[Battery] = []
            problems: list[str] = []
            for key, row in await self._store.list(self._collection):
                try:
                    found.append(battery_from_document(row, source="store"))
                except ValueError as wrong:
                    problems.append(f"{self._collection}/{key}: {wrong}")
            self._batteries, self._problems, self._seen = tuple(found), tuple(problems), version
        return self._batteries

    async def problems(self) -> tuple[str, ...]:
        return self._problems


def store_batteries(store: Any, collection: str = "batteries") -> StoreBatteries:
    return StoreBatteries(store, collection)


def batteries_in(where: Path) -> FileBatteries:
    return FileBatteries(where)


def shipped_batteries() -> FileBatteries:
    """The batteries this package carries, read from the package so a wheel and a checkout
    agree."""
    with resources.as_file(resources.files(__package__) / "batteries_library") as where:
        return FileBatteries(Path(where), source="shipped")


class BatteryRegistry:
    """Batteries in the order their sources were given; a later source shadows an earlier one
    with the same id."""

    def __init__(self, first: BatterySource, *, sources: Sequence[BatterySource] = ()) -> None:
        self.sources: tuple[BatterySource, ...] = (first, *sources)
        self._problems: tuple[str, ...] = ()

    async def all(self) -> tuple[Battery, ...]:
        by_id: dict[str, Battery] = {}
        problems: list[str] = []
        for source in self.sources:
            for battery in await source.batteries():
                by_id[battery.id] = battery
            problems.extend(await source.problems())
        self._problems = tuple(problems)
        return tuple(by_id.values())

    async def find(self, battery_id: str) -> Battery | None:
        for battery in await self.all():
            if battery.id == battery_id:
                return battery
        return None

    async def problems(self) -> tuple[str, ...]:
        return self._problems


# ---------------------------------------------------------------------------- opening


@dataclass
class OpenedBattery:
    """A battery started, or the reason it could not be."""

    battery: Battery
    port: ComponentPort | None = None
    problem: str | None = None
    _close: Callable[[], Any] | None = field(default=None, repr=False)

    async def close(self) -> None:
        if self._close is not None:
            await self._close()
            self._close = None


async def open_battery(
    battery: Battery, *, env: dict[str, str] | None = None, at: str = ""
) -> OpenedBattery:
    """Start the battery as a component port — an MCP server held open, or a callable — or
    report why it cannot start here."""
    problem = battery.problem_running(env=env)
    if problem is not None:
        return OpenedBattery(battery, problem=problem)
    registered_by = f"battery:{battery.id}"
    if battery.kind == "python":
        from shadow_hdk.adapters.basic import CallableComponents

        module_name, attribute = battery.callable.split(":", 1)
        function = getattr(importlib.import_module(module_name), attribute)
        ((name, tool),) = battery.tools.items()
        port = CallableComponents(registered_by=registered_by, at=at)
        port.add(function, effects=tool.effects, name=name, registration_id=name)
        return OpenedBattery(battery, port=port)
    from shadow_hdk.adapters.mcp import McpComponents, StdioServerParameters

    binary = battery.resolve(env=env)
    assert binary is not None, "problem_running said it resolves"
    environment = dict(os.environ if env is None else env)
    environment.pop("CLAUDECODE", None)  # a child that is Claude Code must not think it is nested
    server = McpComponents(
        StdioServerParameters(command=binary, args=list(battery.args), env=environment),
        source=registered_by,
        at=at,
        only=[tool.tool for tool in battery.tools.values()],
        aliases={tool.tool: name for name, tool in battery.tools.items()},
        effects={tool.tool: tool.effects for tool in battery.tools.values()},
    )
    # **Held by one task for its lifetime** (D67's lesson, again): the MCP client is an anyio
    # cancel scope, and the task that opens a battery — a `thread/start` handler — is never the
    # one that closes it. So a holder task enters and leaves it, and `close` only asks.
    ready: asyncio.Future[str | None] = asyncio.get_running_loop().create_future()
    let_go = asyncio.Event()

    async def hold() -> None:
        try:
            await server.start()
        except Exception as failed:  # noqa: BLE001 — a server that will not start is a report
            ready.set_result(f"{type(failed).__name__}: {failed}")
            return
        ready.set_result(None)
        try:
            await let_go.wait()
        finally:
            # Not shielded: a shield is a cancel scope of its own, and the client's task group
            # must find *its* scope current when it leaves (measured).
            await server.stop()

    holder = asyncio.create_task(hold())
    why = await ready
    if why is not None:
        await holder
        return OpenedBattery(battery, problem=f"battery {battery.id!r} did not start: {why}")

    async def close() -> None:
        let_go.set()
        await holder

    return OpenedBattery(battery, port=server, _close=close)


__all__ = [
    "Battery",
    "BatteryRegistry",
    "BatterySource",
    "BatteryTool",
    "FileBatteries",
    "OpenedBattery",
    "StoreBatteries",
    "batteries_in",
    "battery_from_document",
    "open_battery",
    "shipped_batteries",
    "store_batteries",
]
