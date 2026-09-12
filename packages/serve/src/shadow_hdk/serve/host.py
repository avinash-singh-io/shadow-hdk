"""The shipped composition — what the coder and the studio used to carry, as the harness's own.

One environment with a mode (D48; confinement is the operating system's, proven before the
environment exists — D49), the shipped skills, `ask_person`, a mode registry over files and a
store (D64, D66), the person's act rules (D65), the registry offered to the provider over the
authenticated socket for the thread's lifetime (D62), and a provider — whichever CLI is signed in
here, or one handed in. `ServeHost` implements the wire's `ThreadHost`, so the same object stands
behind `shadow-hdk serve` for a host in any language and behind `a_thread` for a Python one.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.agent import (
    SkillComponents,
    SkillRegistry,
    shipped_skills,
    store_skills,
)
from shadow_hdk.adapters.basic import SqliteStore, SqliteThreads, StdoutSink, SystemClock
from shadow_hdk.adapters.modes import (
    ActRules,
    Mode,
    ModeRegistry,
    governance_for,
    modes_in,
    shipped_modes,
    store_modes,
    store_rules,
)
from shadow_hdk.adapters.recording import SocketOffer

from shadow_hdk.adapters.environment import LocalEnvironment
from shadow_hdk.kernel import Ceiling, Floor, Lease, ThreadStore
from shadow_hdk.kernel.ports import AgentPort
from shadow_hdk.providers import environment_for, open_with, ready, search_dirs
from shadow_hdk.runtime import Approvals, Ports
from shadow_hdk.runtime.environment import Mode as EnvironmentMode
from shadow_hdk.runtime.person import person_components
from shadow_hdk.runtime.store import InMemoryStore
from shadow_hdk.runtime.switched import Switched, store_switches
from shadow_hdk.runtime.threads import TURN, InMemoryThreads, Thread
from shadow_hdk.serve.batteries import (
    BatteryRegistry,
    OpenedBattery,
    batteries_in,
    open_battery,
    shipped_batteries,
    store_batteries,
)
from shadow_hdk.serve.config import Settings

MODES = ModeRegistry(shipped_modes())
_POLICY = {spec.id: spec.policy for spec in MODES.listing()}
LOOKING: Mode = _POLICY["read-only"]
CONFINED: Mode = _POLICY["workspace-write"]
OPEN: Mode = _POLICY["full"]
POLICY_FOR: dict[EnvironmentMode, Mode] = {
    "read-only": LOOKING,
    "workspace-write": CONFINED,
    "full": OPEN,
}


def modes_for(store: Any = None, *, files: Path | None = None) -> ModeRegistry:
    """The registry a thread reads modes from: shipped, then a directory of files, then a store
    (D66) — later shadowing earlier by id. Live: a row or a file written now is a mode at the next
    read."""
    sources: list[Any] = []
    if files is not None:
        sources.append(modes_in(files))
    if store is not None:
        sources.append(store_modes(store))
    return ModeRegistry(shipped_modes(), sources=tuple(sources))


def batteries_for(store: Any = None, *, files: Path | None = None) -> BatteryRegistry:
    """The registry batteries are read from (D70): shipped, then a directory of files, then a
    store — later shadowing earlier by id."""
    sources: list[Any] = []
    if files is not None:
        sources.append(batteries_in(files))
    if store is not None:
        sources.append(store_batteries(store))
    return BatteryRegistry(shipped_batteries(), sources=tuple(sources))


async def open_batteries(
    registry: BatteryRegistry, wanted: Sequence[str]
) -> tuple[tuple[OpenedBattery, ...], dict[str, str]]:
    """Start the batteries named — an MCP server each, held open for the process — and say which
    could not be: unknown ids and the reasons the rest gave."""
    opened: list[OpenedBattery] = []
    problems: dict[str, str] = {}
    for battery_id in wanted:
        battery = await registry.find(battery_id)
        if battery is None:
            problems[battery_id] = f"no battery {battery_id!r} is shipped, filed or stored here"
            continue
        started = await open_battery(battery)
        opened.append(started)
        if started.problem is not None:
            problems[battery_id] = started.problem
    return tuple(opened), problems


async def workshop(
    root: Path,
    *,
    mode: EnvironmentMode = "workspace-write",
    rules: Any = None,
    store: Any = None,
    modes: ModeRegistry | None = None,
    batteries: Sequence[Any] = (),
) -> Ports:
    """Everything the agent can reach, and the policy that judges it.

    Raises `CannotEnforce` when this machine has no OS sandbox and a confined mode was asked for —
    the environment refuses to exist rather than quietly widen, and that reaches the person,
    because it is the right thing for them to see.
    """
    environment = await LocalEnvironment.open(
        root, mode=mode, timeout_s=60.0, output_limit=32_000, at="2026-09-11T00:00:00+00:00"
    )
    skill_sources: tuple[Any, ...] = (shipped_skills(),)
    if store is not None:
        skill_sources = (*skill_sources, store_skills(store))  # a row is a skill (D66)
    skills = SkillComponents(
        SkillRegistry(skill_sources), minting=True, at="2026-09-11T00:00:00+00:00"
    )
    # The agent's own question to the person is a component like any other (D65): no effects,
    # so every mode offers it.
    # Batteries (D70) are ports like any other, judged by the same modes: their profiles say what
    # they reach, so a confined mode hides them by itself.
    offered: tuple[Any, ...] = (environment, skills, person_components(), *batteries)
    if store is not None:
        # Which components are on is the store's to say (D66): off at the next refresh.
        offered = tuple(Switched(port, store_switches(store)) for port in offered)
    return Ports(
        model=None,  # the reasoning is the provider's; this runtime supplies no model
        components=offered,
        # Every shipped mode is judged from; the environment's mode is the one selected by default,
        # and `Thread.set_mode` flips between them live (D64). The person's act rules are read
        # after a mode says *ask* (D65).
        governance=governance_for(modes or MODES, default=mode, rules=rules),
        sink=StdoutSink(),
        clock=SystemClock(),
    )


def a_lease() -> Lease:
    """What one thread may spend. A ceiling on steps, wall-clock and money — the money being the
    subscription's, which is why it is small enough to notice."""
    return Lease(Ceiling(max_steps=400, max_wall_seconds=3600, max_cost_cents=500), Floor(0))


class ServeHost:
    """The wire's `ThreadHost`, composed from the shipped adapters.

    One per process: one store (sqlite when `settings.store` names a file, memory otherwise), one
    thread store beside it, one `Approvals` handle, one rule registry, one mode registry. A
    provider is resolved at `open` — `settings.want` or the first CLI signed in here — unless one
    was handed in (`agent=`), which is what a test does.
    """

    def __init__(self, settings: Settings, *, agent: AgentPort | None = None) -> None:
        self.settings = settings
        self.approvals = Approvals()
        self.store: Any = SqliteStore(settings.store) if settings.store else InMemoryStore()
        self.threads: ThreadStore = (
            SqliteThreads(settings.store.with_suffix(".threads.sqlite"))
            if settings.store
            else InMemoryThreads()
        )
        self.rules = ActRules(sources=(store_rules(self.store),))
        self.modes = modes_for(self.store, files=settings.modes_dir)
        self.batteries = batteries_for(self.store, files=settings.batteries_dir)
        self.batteries_opened: tuple[OpenedBattery, ...] = ()
        self.battery_problems: dict[str, str] = {}
        self._batteries_started = False
        self._agent = agent
        self.provider = ""

    async def _battery_ports(self) -> tuple[Any, ...]:
        """The batteries switched on, opened once for the process — their servers outlive any one
        thread, like the store does."""
        if not self._batteries_started:
            self.batteries_opened, self.battery_problems = await open_batteries(
                self.batteries, self.settings.batteries
            )
            self._batteries_started = True
        return tuple(b.port for b in self.batteries_opened if b.port is not None)

    async def battery_listing(self) -> list[dict[str, Any]]:
        """Every battery the registry knows: on, off (not wanted), or unavailable and why."""
        await self._battery_ports()
        running = {b.battery.id for b in self.batteries_opened if b.port is not None}
        listed: list[dict[str, Any]] = []
        for battery in await self.batteries.all():
            problem = self.battery_problems.get(battery.id)
            status = (
                "on"
                if battery.id in running
                else "unavailable"
                if problem
                else "off"
                if battery.id not in self.settings.batteries
                else "unavailable"
            )
            listed.append(
                {
                    "id": battery.id,
                    "name": battery.name,
                    "kind": battery.kind,
                    "source": battery.source,
                    "tools": sorted(battery.tools),
                    "licence": battery.licence,
                    "status": status,
                    "problem": problem,
                }
            )
        for battery_id, problem in self.battery_problems.items():
            if not any(row["id"] == battery_id for row in listed):
                listed.append(
                    {
                        "id": battery_id,
                        "name": battery_id,
                        "kind": "",
                        "source": "",
                        "tools": [],
                        "licence": "",
                        "status": "unavailable",
                        "problem": problem,
                    }
                )
        return listed

    async def aclose(self) -> None:
        """Stop what the process holds open: the batteries' servers."""
        for opened in self.batteries_opened:
            await opened.close()
        self.batteries_opened = ()
        self._batteries_started = False

    async def _provider(self, want: str | None, root: Path) -> tuple[AgentPort, str]:
        if self._agent is not None:
            return self._agent, self.provider or "handed in"
        available = await ready(want or self.settings.want)
        assert available.binary is not None, "a ready provider has a binary"
        opened = await open_with(
            available.provider,
            binary=available.binary,
            env=environment_for(available.provider, base={}, search=search_dirs()),
            workspace=root,
        )
        return opened, f"{available.provider.called} {available.version or ''}".strip()

    async def open(
        self,
        *,
        root: str,
        mode: str,
        want: str | None,
        name: str,
        observer: Any = None,
        thread_id: str | None = None,
    ) -> Thread:
        where = Path(root or self.settings.root).resolve()
        where.mkdir(parents=True, exist_ok=True)
        environment_mode: EnvironmentMode = mode or self.settings.mode  # type: ignore[assignment]
        agent, called = await self._provider(want, where)
        ports = await workshop(
            where,
            mode=environment_mode,
            rules=self.rules,
            store=self.store,
            modes=self.modes,
            batteries=await self._battery_ports(),
        )
        thread = await Thread.open(
            agent=agent,
            ports=replace(ports, observer=observer) if observer is not None else ports,
            store=self.threads,
            root=where,
            lease=a_lease(),
            registry=SocketOffer(name=name or self.settings.registry_name, withhold={TURN}),
            approvals=self.approvals,
            rules=self.rules,
            modes=self.modes,
            mode=environment_mode,
            provider=called,
            thread_id=thread_id,
        )
        self.provider = called
        return thread

    async def resume(self, thread_id: str, *, observer: Any = None) -> Thread:
        record = await self.threads.get(thread_id)
        if record is None:
            raise KeyError(f"no thread {thread_id!r} in the store")
        where = Path(record.root)
        environment_mode: EnvironmentMode = record.mode or self.settings.mode  # type: ignore[assignment]
        agent, _called = await self._provider(None, where)
        ports = await workshop(
            where,
            mode=environment_mode,
            rules=self.rules,
            store=self.store,
            modes=self.modes,
            batteries=await self._battery_ports(),
        )
        return await Thread.resume(
            thread_id,
            agent=agent,
            ports=replace(ports, observer=observer) if observer is not None else ports,
            store=self.threads,
            lease=a_lease(),
            registry=SocketOffer(name=self.settings.registry_name, withhold={TURN}),
            approvals=self.approvals,
            rules=self.rules,
            modes=self.modes,
        )

    async def list(self) -> Any:
        return await self.threads.list()


@asynccontextmanager
async def a_thread(
    root: Path,
    *,
    want: str | None = None,
    mode: EnvironmentMode = "workspace-write",
    approvals: Approvals | None = None,
    threads: ThreadStore | None = None,
    name: str = "tools",
    observer: Any = None,
    rules: Any = None,
    store: Any = None,
    agent: AgentPort | None = None,
    batteries: Sequence[str] = (),
    batteries_dir: Path | None = None,
) -> AsyncIterator[Thread]:
    """A thread on the provider signed in here, its tools this run's, inside the workshop — the
    Python-side door onto the same composition `serve` puts behind the wire.

    `approvals` is where the policy's approval requests about the provider's tool calls go while
    the provider waits on them (D58). Without one, a call the policy asks about is refused: nobody
    was there to ask. `observer` hears the record and, through `on_activity`, what is happening
    beside it (D63). `batteries` names what to switch on (D70) — opened for the thread's life,
    read from the shipped files, `batteries_dir` and the store; `agent` hands a provider in.
    """
    root.mkdir(parents=True, exist_ok=True)
    if agent is not None:
        opened, called = agent, "handed in"
    else:
        available = await ready(want)
        assert available.binary is not None, "a ready provider has a binary"
        opened = await open_with(
            available.provider,
            binary=available.binary,
            env=environment_for(available.provider, base={}, search=search_dirs()),
            workspace=root,
        )
        called = f"{available.provider.called} {available.version or ''}".strip()
    modes = modes_for(store, files=root / ".harness" / "modes")  # live: rows and files (D66)
    started, problems = await open_batteries(
        batteries_for(store, files=batteries_dir or root / ".harness" / "batteries"), batteries
    )
    for battery_id, problem in problems.items():
        print(f"battery {battery_id!r}: {problem}", file=sys.stderr)
    try:
        thread = await Thread.open(
            agent=opened,
            ports=replace(
                await workshop(
                    root,
                    mode=mode,
                    rules=rules,
                    store=store,
                    modes=modes,
                    batteries=tuple(b.port for b in started if b.port is not None),
                ),
                observer=observer,
            ),
            store=threads or InMemoryThreads(),
            root=root,
            lease=a_lease(),
            registry=SocketOffer(name=name, withhold={TURN}),
            approvals=approvals,
            rules=rules,
            modes=modes,
            mode=mode,
            provider=called,
        )
        try:
            yield thread
        finally:
            await thread.close()
    finally:
        for battery in started:
            await battery.close()


__all__ = [
    "CONFINED",
    "batteries_for",
    "open_batteries",
    "LOOKING",
    "MODES",
    "OPEN",
    "POLICY_FOR",
    "ServeHost",
    "a_lease",
    "a_thread",
    "modes_for",
    "workshop",
]
