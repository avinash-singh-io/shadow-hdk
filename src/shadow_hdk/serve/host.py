"""The shipped composition — what the coder and the studio used to carry, as the harness's own.

One environment with a mode (D48; confinement is the operating system's, proven before the
environment exists — D49), the shipped skills, `ask_person`, a mode registry over files and a
store (D64, D66), the person's act rules (D65), the registry offered to the provider over the
authenticated socket for the thread's lifetime (D62), and a provider — whichever CLI is signed in
here, or one handed in. `ServeHost` implements the wire's `ThreadHost`, so the same object stands
behind `shadow-hdk serve` for a host in any language and behind `a_thread` for a Python one.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import uuid
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from shadow_hdk.adapters.agent import (
    ModelAgent,
    SkillComponents,
    SkillRegistry,
    shipped_skills,
    single,
    store_skills,
)
from shadow_hdk.adapters.basic import StdoutSink, SystemClock
from shadow_hdk.adapters.environment import LocalEnvironment
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
from shadow_hdk.kernel import (
    Ceiling,
    EnvironmentRequirements,
    ExecutionRequirements,
    ExecutionSelection,
    Lease,
    ProviderCapabilities,
    ThreadStore,
    Workspace,
    select_execution,
)
from shadow_hdk.kernel.contracts import adapter_for, dump
from shadow_hdk.kernel.ports import (
    AgentPort,
    AuthorityPort,
    AuthorizerPort,
    ComponentPort,
    EffectJournalPort,
    ModelPort,
)
from shadow_hdk.providers import (
    Available,
    detect,
    environment_for,
    open_with,
    ready,
    search_dirs,
    shipped,
)
from shadow_hdk.runtime import Approvals, InMemoryEffectJournal, Ports
from shadow_hdk.runtime.environment import MODES as ENVIRONMENT_MODES
from shadow_hdk.runtime.environment import Mode as EnvironmentMode
from shadow_hdk.runtime.environment import mode_named
from shadow_hdk.runtime.person import person_components
from shadow_hdk.runtime.switched import Switched, store_switches
from shadow_hdk.runtime.threads import TURN, InMemoryThreads, Thread
from shadow_hdk.serve.authority import HostAuthority, HostAuthorizer
from shadow_hdk.serve.batteries import (
    BatteryRegistry,
    OpenedBattery,
    batteries_in,
    open_battery,
    shipped_batteries,
    store_batteries,
)
from shadow_hdk.serve.config import Budget, Settings
from shadow_hdk.serve.keeping import KeepingSink
from shadow_hdk.serve.stores import Stores, stores_for

WANTED = "wanted"
"""The store collection that says which batteries are on (D83): rows `{id, on}`."""

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


def skills_for(store: Any = None) -> SkillRegistry:
    """The registry a thread chooses skills from: shipped, then a store (D66) — a row written now
    is a skill at the next read — and what its agents mint (D56), for as long as it lives."""
    sources: tuple[Any, ...] = (shipped_skills(),)
    if store is not None:
        sources = (*sources, store_skills(store))
    return SkillRegistry(sources)


async def workshop(
    root: Path,
    *,
    mode: EnvironmentMode = "workspace-write",
    rules: Any = None,
    store: Any = None,
    modes: ModeRegistry | None = None,
    batteries: Sequence[Any] = (),
    skills: SkillRegistry | None = None,
    workspace: Workspace | None = None,
    environment: LocalEnvironment | None = None,
    requirements: EnvironmentRequirements | None = None,
    authority: AuthorityPort | None = None,
    authorizer: AuthorizerPort | None = None,
    effect_journal: EffectJournalPort | None = None,
    principal: str | None = None,
    attributes: dict[str, Any] | None = None,
    provider_revision: str = "",
) -> Ports:
    """Everything the agent can reach, and the policy that judges it.

    `workspace` names the roots (D76) — one or many; `root` alone is the one-root workspace.

    `skills` is the registry the agent chooses from and mints into; a host that hands one in
    shares it across its threads, so a skill minted in one is offered in the next and listed on
    the wire (`skills/list`). Without one, a thread gets its own — shipped, then the store.

    Raises `CannotEnforce` when this machine has no OS sandbox and a confined mode was asked for —
    the environment refuses to exist rather than quietly widen, and that reaches the person,
    because it is the right thing for them to see.
    """
    environment = environment or await LocalEnvironment.open(
        root,
        mode=mode,
        timeout_s=60.0,
        output_limit=32_000,
        at="2026-09-11T00:00:00+00:00",
        workspace=workspace,
        requirements=requirements,
    )
    chosen_from = SkillComponents(
        skills if skills is not None else skills_for(store),
        minting=True,
        at="2026-09-11T00:00:00+00:00",
    )
    # The agent's own question to the person is a component like any other (D65): no effects,
    # so every mode offers it.
    # Batteries (D70) are ports like any other, judged by the same modes: their profiles say what
    # they reach, so a confined mode hides them by itself.
    offered: tuple[Any, ...] = (environment, chosen_from, person_components(), *batteries)
    if store is not None:
        # Which components are on is the store's to say (D66): off at the next refresh.
        offered = tuple(Switched(port, store_switches(store)) for port in offered)
    chosen_modes = modes or MODES
    chosen_rules = rules if rules is not None else ActRules()
    clock = SystemClock()
    return Ports(
        model=None,  # the reasoning is the provider's; this runtime supplies no model
        components=offered,
        # Every shipped mode is judged from; the environment's mode is the one selected by default,
        # and `Thread.set_mode` flips between them live (D64). The person's act rules are read
        # after a mode says *ask* (D65).
        governance=governance_for(chosen_modes, default=mode, rules=chosen_rules),
        sink=StdoutSink(),
        clock=clock,
        authority=authority
        or HostAuthority(
            workspace=workspace or Workspace.of(root),
            modes=chosen_modes,
            rules=chosen_rules,
            components=cast(tuple[ComponentPort, ...], offered),
            provider_revision=provider_revision,
            principal=principal,
            attributes=attributes,
            mode=mode,
        ),
        authorizer=authorizer or HostAuthorizer(clock),
        effect_journal=effect_journal or InMemoryEffectJournal(),
    )


def a_lease(budget: Budget | None = None) -> Lease:
    """What one thread may spend — `[budget]` in the file, a `Lease` underneath: a ceiling on
    steps, wall-clock and money, the money being the subscription's, which is why the default is
    small enough to notice."""
    return (budget or Budget()).lease()


class ServeHost:
    """The wire's `ThreadHost`, composed from the shipped adapters.

    One per process: one record — the store the registries read, the thread store, and the
    checkpointer a parked run sleeps in and effect journal, all four from `settings.store`'s url
    (D79, D101; memory when
    it names nothing) — one `Approvals` handle, one rule registry, one mode registry. A provider
    is resolved at `open` — `settings.want` or the first CLI signed in here — unless one was
    handed in (`agent=`), which is what a test does.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        agent: AgentPort | None = None,
        model: ModelPort | None = None,
        governance: Any = None,
        sink: Any = None,
        store: Any = None,
        threads: ThreadStore | None = None,
        checkpointer: Any = None,
        run_store: Any = None,
        effect_journal: EffectJournalPort | None = None,
        authority: AuthorityPort | None = None,
        authorizer: AuthorizerPort | None = None,
        provider_capabilities: ProviderCapabilities | None = None,
        requirements: ExecutionRequirements | None = None,
    ) -> None:
        """`governance` and `sink` handed in replace the shipped ones for every thread this host
        opens — one step deeper (D71) without composing the rest again. `store`, `threads` and
        `checkpointer` handed in are a product's own tables (D79): each replaces the one the url
        would have made, and a host that hands all four never reads the url. `run_store` (D93)
        is a product's own `RunStore` — the checkpointer is then the library's saver over it."""
        if agent is not None and model is not None:
            raise ValueError("hand either agent= or model=, not both")
        self.settings = settings
        self._governance = governance
        self._sink = sink
        self.approvals = Approvals()
        self.stores: Stores = stores_for(
            settings.store,
            store=store,
            threads=threads,
            checkpointer=checkpointer,
            run_store=run_store,
            effect_journal=effect_journal,
        )
        self.store: Any = self.stores.store
        self.threads: ThreadStore = self.stores.threads
        self.holder = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        """This process's name on every thread it holds (D81): host, pid, a nonce — so a second
        process on the same store is refused by a name a person can find."""
        self.rules = ActRules(sources=(store_rules(self.store),))
        self.modes = modes_for(self.store, files=settings.modes_dir)
        self.skills = skills_for(self.store)
        self.sink: Any = KeepingSink(self.store, sink if sink is not None else StdoutSink())
        """Where a run's proposals go: a minted skill is kept as a store row (ENH-011), and every
        proposal reaches the sink handed in — or stdout, the shipped default."""
        self.batteries = batteries_for(self.store, files=settings.batteries_dir)
        self.batteries_opened: tuple[OpenedBattery, ...] = ()
        self.battery_problems: dict[str, str] = {}
        self._batteries_seeded = False
        self._agent = agent or (
            ModelAgent(model=model, pattern=single) if model is not None else None
        )
        self._handed_capabilities = provider_capabilities or ProviderCapabilities()
        self.requirements = requirements or ExecutionRequirements()
        self._authority = authority
        self._authorizer = authorizer
        self._selections: dict[str, ExecutionSelection] = {}
        self.provider = "handed model" if model is not None else ""

    async def wanted(self) -> tuple[str, ...]:
        """Which batteries are wanted **now** (D83): the store's `wanted` rows (`{id, on}`),
        seeded once from `[tools] batteries` — a row already there is left as it is, so the
        store rules from the first open on, the way a mode or a rule row does (D66)."""
        if not self._batteries_seeded:
            for battery_id in self.settings.batteries:
                if await self.store.get(WANTED, battery_id) is None:
                    await self.store.put(WANTED, battery_id, {"id": battery_id, "on": True})
            self._batteries_seeded = True
        return tuple(
            str(row.get("id", key))
            for key, row in await self.store.list(WANTED)
            if isinstance(row, dict) and row.get("on") is True
        )

    async def _battery_ports(self) -> tuple[Any, ...]:
        """The batteries wanted now, opened — each held for the process once it is, its server
        outliving any one thread like the store does — and the ones no longer wanted closed
        (D83). Read at every thread's open: a row written now is a battery at the next thread —
        and a battery switched off is gone from every thread at once, its server being the
        process's, not a thread's."""
        wanted = await self.wanted()
        keep = tuple(b for b in self.batteries_opened if b.battery.id in wanted)
        for gone in (b for b in self.batteries_opened if b.battery.id not in wanted):
            await gone.close()
            self.battery_problems.pop(gone.battery.id, None)
        have = {b.battery.id for b in keep}
        opened, problems = await open_batteries(
            self.batteries, [b for b in wanted if b not in have]
        )
        self.batteries_opened = (*keep, *opened)
        self.battery_problems = {
            **{k: v for k, v in self.battery_problems.items() if k in wanted},
            **problems,
        }
        return tuple(b.port for b in self.batteries_opened if b.port is not None)

    async def battery_listing(self) -> list[dict[str, Any]]:
        """Every battery the registry knows: on, off (not wanted), or unavailable and why."""
        await self._battery_ports()
        wanted = await self.wanted()
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
                if battery.id not in wanted
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

    async def checkpointer(self) -> Any:
        """Where a parked run sleeps (D80): the one handed in, or the one the store's url names —
        opened on first ask, because its connection is an async one."""
        return await self.stores.checkpointer()

    async def aclose(self) -> None:
        """Stop what the process holds open: the batteries' servers, the record's connections."""
        for opened in self.batteries_opened:
            await opened.close()
        self.batteries_opened = ()
        await self.stores.aclose()

    async def _provider_candidate(
        self, want: str | None
    ) -> tuple[AgentPort | None, Available | None, ProviderCapabilities, str]:
        """Resolve and probe, but do not open the provider's execution process yet."""
        if self._agent is not None:
            return (
                self._agent,
                None,
                self._handed_capabilities,
                self.provider or "handed in",
            )
        available = await ready(want or self.settings.want)
        called = f"{available.provider.called} {available.version or ''}".strip()
        return None, available, available.capabilities, called

    async def _open_candidate(
        self,
        handed: AgentPort | None,
        available: Available | None,
        root: Path,
    ) -> AgentPort:
        if handed is not None:
            return handed
        assert available is not None and available.binary is not None
        opened: AgentPort = await open_with(
            available.provider,
            binary=available.binary,
            env=environment_for(available.provider, base={}, search=search_dirs()),
            workspace=root,
        )
        return opened

    def _requirements(self, given: Any = None) -> ExecutionRequirements:
        if given is None:
            return self.requirements
        if isinstance(given, ExecutionRequirements):
            return given
        return cast(
            ExecutionRequirements,
            adapter_for(ExecutionRequirements).validate_python(given),
        )

    def capabilities_for(self, thread_id: str) -> ExecutionSelection:
        try:
            return self._selections[thread_id]
        except KeyError:
            raise KeyError(f"no capability selection for thread {thread_id!r}") from None

    async def check_capabilities(
        self,
        *,
        mode: str = "",
        want: str | None = None,
        requirements: Any = None,
        root: str = "",
    ) -> ExecutionSelection:
        """Probe and prove a pair without opening the provider agent or a thread."""
        execution = self._requirements(requirements)
        _handed, _available, provider, _called = await self._provider_candidate(want)
        policy_mode = mode or self.settings.mode
        environment_mode = await self._environment_for(policy_mode)
        workspace = Workspace.of(Path(root or self.settings.root))
        for each in workspace.roots:
            Path(each.path).mkdir(parents=True, exist_ok=True)
        environment = await LocalEnvironment.open(
            Path(workspace.primary.path),
            mode=environment_mode,
            workspace=workspace,
            requirements=execution.environment,
        )
        try:
            return select_execution(provider, environment.capabilities, execution)
        finally:
            await environment.close()

    async def provider_listing(self) -> list[dict[str, Any]]:
        """The shipped provider records with this machine's detection and capability evidence."""
        providers = list(shipped().values())
        available = await detect(providers)
        return [
            {
                "id": item.provider.id,
                "name": item.provider.called,
                "kind": item.provider.kind,
                "status": item.status,
                "binary": str(item.binary) if item.binary is not None else None,
                "version": item.version,
                "message": item.message,
                "install_hint": item.install_hint,
                "capabilities": json.loads(dump(item.capabilities, ProviderCapabilities)),
            }
            for item in available
        ]

    async def open(
        self,
        *,
        root: str,
        mode: str,
        want: str | None,
        name: str,
        observer: Any = None,
        thread_id: str | None = None,
        roots: Any = None,
        principal: str = "",
        attributes: Any = None,
        budget: Any = None,
        requirements: Any = None,
    ) -> Thread:
        # One root or many (D76): `roots` as the wire carries them — `[{name, path}, …]` — or
        # `root`, or the settings' default. Every root is made if it is not there.
        workspace = (
            Workspace.from_json(roots) if roots else Workspace.of(Path(root or self.settings.root))
        )
        for each in workspace.roots:
            Path(each.path).mkdir(parents=True, exist_ok=True)
        where = Path(workspace.primary.path).resolve()
        policy_mode = mode or self.settings.mode
        environment_mode = await self._environment_for(policy_mode)
        execution = self._requirements(requirements)
        handed, available, provider_capabilities, called = await self._provider_candidate(want)
        environment = await LocalEnvironment.open(
            where,
            mode=environment_mode,
            timeout_s=60.0,
            output_limit=32_000,
            at="2026-09-11T00:00:00+00:00",
            workspace=workspace,
            requirements=execution.environment,
        )
        try:
            selection = select_execution(provider_capabilities, environment.capabilities, execution)
            agent = await self._open_candidate(handed, available, where)
        except BaseException:
            await environment.close()
            raise
        ports = await workshop(
            where,
            mode=environment_mode,
            rules=self.rules,
            store=self.store,
            modes=self.modes,
            batteries=await self._battery_ports(),
            skills=self.skills,
            workspace=workspace,
            environment=environment,
            authority=self._authority,
            authorizer=self._authorizer,
            effect_journal=self.stores.effects,
            principal=principal or None,
            attributes=attributes if isinstance(attributes, dict) else None,
            provider_revision=called,
        )
        thread = await Thread.open(
            agent=agent,
            ports=self._handed(ports, observer),
            store=self.threads,
            root=where,
            lease=a_lease(self.settings.budget),
            registry=SocketOffer(name=name or self.settings.registry_name, withhold={TURN}),
            approvals=self.approvals,
            checkpointer=await self.checkpointer(),
            rules=self.rules,
            modes=self.modes,
            mode=policy_mode,
            provider=called,
            thread_id=thread_id,
            workspace=workspace,
            holder=self.holder,
            principal=principal,
            attributes=attributes if isinstance(attributes, dict) else None,
            budget=self._budget_of(budget),
            idle_seconds=self.settings.idle_seconds,
            requirements=execution,
        )
        self._selections[thread.id] = selection
        thread.execution = selection
        self.provider = called
        return thread

    def _budget_of(self, given: Any) -> Ceiling | None:
        """A thread's own budget (D84), in the file's words — `{steps, seconds, cents}`, each
        over the file's default when named — as the kernel's ceiling; `None` when nothing was
        asked for. A value that is not a whole number is refused by name."""
        if given is None:
            return None
        if not isinstance(given, dict):
            raise ValueError("budget must be an object of steps, seconds and cents")
        for key in ("steps", "seconds", "cents"):
            if key in given and given[key] is not None and not isinstance(given[key], int):
                raise ValueError(f"budget {key} must be a whole number")
        base = self.settings.budget
        return (
            Budget(
                steps=int(given.get("steps", base.steps)),
                seconds=int(given.get("seconds", base.seconds)),
                cents=given.get("cents", base.cents),
            )
            .lease()
            .ceiling
        )

    async def _environment_for(self, policy_mode: str) -> EnvironmentMode:
        """The sandbox mode a mode needs (D76), from its spec in the registry read now (D66).
        An unknown mode is refused by name, with the known ones; a mode whose spec names no
        environment is refused too — silence never widens to `full`."""
        spec = await self.modes.find(policy_mode)
        if spec is None:
            known = [m.id for m in await self.modes.all()]
            raise KeyError(f"no mode {policy_mode!r}; the modes here are {known}")
        environment = mode_named(spec.environment)
        if environment is None:
            raise ValueError(
                f"mode {policy_mode!r} names no environment mode; "
                f"give it one of {list(ENVIRONMENT_MODES)}"
            )
        return environment

    async def resume(self, thread_id: str, *, observer: Any = None) -> Thread:
        record = await self.threads.get(thread_id)
        if record is None:
            raise KeyError(f"no thread {thread_id!r} in the store")
        workspace = Workspace(record.roots) if record.roots else Workspace.of(record.root)
        where = Path(workspace.primary.path)
        # The policy's mode is the record's; the environment's is the one it was proven in last
        # (D76), or the one the record's mode names where a record predates that field.
        environment_mode = mode_named(record.environment) or await self._environment_for(
            record.mode or self.settings.mode
        )
        execution = record.requirements
        handed, available, provider_capabilities, _called = await self._provider_candidate(None)
        environment = await LocalEnvironment.open(
            where,
            mode=environment_mode,
            timeout_s=60.0,
            output_limit=32_000,
            at="2026-09-11T00:00:00+00:00",
            workspace=workspace,
            requirements=execution.environment,
        )
        try:
            selection = select_execution(provider_capabilities, environment.capabilities, execution)
            agent = await self._open_candidate(handed, available, where)
        except BaseException:
            await environment.close()
            raise
        ports = await workshop(
            where,
            mode=environment_mode,
            rules=self.rules,
            store=self.store,
            modes=self.modes,
            batteries=await self._battery_ports(),
            skills=self.skills,
            workspace=workspace,
            environment=environment,
            authority=self._authority,
            authorizer=self._authorizer,
            effect_journal=self.stores.effects,
            principal=record.principal or None,
            attributes=record.attributes,
            provider_revision=record.provider,
        )
        thread = await Thread.resume(
            thread_id,
            agent=agent,
            ports=self._handed(ports, observer),
            store=self.threads,
            lease=a_lease(self.settings.budget),
            registry=SocketOffer(name=self.settings.registry_name, withhold={TURN}),
            approvals=self.approvals,
            checkpointer=await self.checkpointer(),
            rules=self.rules,
            modes=self.modes,
            holder=self.holder,
            idle_seconds=self.settings.idle_seconds,
        )
        self._selections[thread.id] = selection
        thread.execution = selection
        return thread

    def _handed(self, ports: Ports, observer: Any) -> Ports:
        """The shipped ports, with whatever this host was handed in their place."""
        handed: dict[str, Any] = {}
        if observer is not None:
            handed["observer"] = observer
        if self._governance is not None:
            handed["governance"] = self._governance
        handed["sink"] = self.sink
        return replace(ports, **handed)

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
    model: ModelPort | None = None,
    batteries: Sequence[str] = (),
    batteries_dir: Path | None = None,
    provider_capabilities: ProviderCapabilities | None = None,
    requirements: ExecutionRequirements | None = None,
) -> AsyncIterator[Thread]:
    """A thread on the provider signed in here, its tools this run's, inside the workshop — the
    Python-side door onto the same composition `serve` puts behind the wire.

    `approvals` is where the policy's approval requests about the provider's tool calls go while
    the provider waits on them (D58). Without one, a call the policy asks about is refused: nobody
    was there to ask. `observer` hears the record and, through `on_activity`, what is happening
    beside it (D63). `batteries` names what to switch on (D70) — opened for the thread's life,
    read from the shipped files, `batteries_dir` and the store; `agent` hands a provider in.
    """
    if agent is not None and model is not None:
        raise ValueError("hand either agent= or model=, not both")
    root.mkdir(parents=True, exist_ok=True)
    execution = requirements or ExecutionRequirements()
    available: Available | None = None
    if agent is not None or model is not None:
        opened = agent or ModelAgent(model=cast(ModelPort, model), pattern=single)
        called = "handed in" if agent is not None else "handed model"
        capabilities = provider_capabilities or ProviderCapabilities()
    else:
        available = await ready(want)
        assert available.binary is not None, "a ready provider has a binary"
        called = f"{available.provider.called} {available.version or ''}".strip()
        capabilities = available.capabilities
        opened = None
    modes = modes_for(store, files=root / ".harness" / "modes")  # live: rows and files (D66)
    started: tuple[OpenedBattery, ...] = ()
    try:
        environment = await LocalEnvironment.open(
            root,
            mode=mode,
            requirements=execution.environment,
        )
        try:
            selection = select_execution(capabilities, environment.capabilities, execution)
            if opened is None:
                assert available is not None and available.binary is not None
                opened = await open_with(
                    available.provider,
                    binary=available.binary,
                    env=environment_for(available.provider, base={}, search=search_dirs()),
                    workspace=root,
                )
        except BaseException:
            await environment.close()
            raise
        started, problems = await open_batteries(
            batteries_for(store, files=batteries_dir or root / ".harness" / "batteries"),
            batteries,
        )
        for battery_id, problem in problems.items():
            print(f"battery {battery_id!r}: {problem}", file=sys.stderr)
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
                    environment=environment,
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
            requirements=execution,
        )
        thread.execution = selection
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
    "skills_for",
    "workshop",
]
