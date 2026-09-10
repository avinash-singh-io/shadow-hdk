"""Wiring: a run, a registry served on a socket, and a provider that can only reach it.

The one structural thing worth understanding. `RecordingServer` holds a **live** `RunContext` — the
parent's lease, the parent's event stream — so it is not a program that can be started; it can only
be connected to. A coding CLI launches its own MCP servers. Those two facts meet in the relay: the
CLI launches `shadow-hdk-registry`, which connects back to the port we are already listening on,
and the server it reaches is this run's own registry.

So the conversation happens **inside a step**. One run, one step, many turns — and every tool the
provider calls becomes a child run on the same graph, with the same lease and the same record.
"""

from __future__ import annotations

import shutil
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.recording import PORT_VARIABLE, RecordingServer, serve_over_socket

from examples.coder.workshop import a_lease, workshop
from shadow_hdk.kernel import (
    Binding,
    Completed,
    Composition,
    EffectProfile,
    Event,
    Invoke,
    Observation,
    ScopeSet,
    ToolSource,
)
from shadow_hdk.providers import detect, environment_for, open_with, search_dirs, shipped
from shadow_hdk.runtime import RunOptions, current_run, run
from shadow_hdk.runtime.testing import InMemoryComponents, make_registration

RELAY = "shadow-hdk-registry"

CONVERSE = make_registration(
    "converse",
    effects=EffectProfile(
        reads=ScopeSet(everything=True),
        writes=ScopeSet.of("workspace"),
        reaches=True,
        reversible=False,
        costs=True,
    ),
    description="Hold a conversation with the provider, for as long as the person wants one.",
)


class NoProvider(RuntimeError):
    """Nothing on this machine can do the reasoning."""


async def ready_provider(want: str | None = None) -> Any:
    """The first provider this machine can actually use, or a refusal that says why not.

    Detection is the whole of it — no credential is read, and nothing is installed (D41). A provider
    that is present but signed out is reported as exactly that, with the command that fixes it.
    """
    library = shipped()
    wanted = [library[want]] if want else list(library.values())
    found = await detect(wanted)
    for it in found:
        if it.status == "ready" and it.provider.injects_tools:
            return it
    lines = [f"  {it.provider.called:12} {it.status:14} {it.provider.install_hint}" for it in found]
    raise NoProvider("no provider on this machine is ready:\n" + "\n".join(lines))


def relay_source(port: int) -> ToolSource:
    """Where the provider's tools are — and under D42 they are ours.

    The relay must be on the path the *child* will search, not merely on ours: it is launched by the
    CLI, in the environment we hand the CLI, and a `PATH` that resolved it here and not there is the
    asymmetry the resolution module exists to prevent.
    """
    found = shutil.which(RELAY)
    return ToolSource(kind="mcp", address=found or RELAY, env=((PORT_VARIABLE, str(port)),))


@asynccontextmanager
async def a_conversation(
    root: Path, *, want: str | None = None, on_event: Callable[[Event], None] | None = None
) -> AsyncIterator[Any]:
    """A resident provider whose only tools are this run's, inside a live run.

    Yields something with `turn(prompt)` on it. Everything the provider does while you hold it lands
    on the run's stream.
    """
    root.mkdir(parents=True, exist_ok=True)
    available = await ready_provider(want)
    held: dict[str, Any] = {}

    async def converse(_inputs: Any) -> Observation:
        context = current_run()
        assert context is not None
        held_back = {CONVERSE.component.interface.name}
        async with (
            RecordingServer(context, withhold=held_back).served() as server,
            serve_over_socket(server) as port,
        ):
            opened = await open_with(
                available.provider,
                binary=available.binary,
                env=environment_for(available.provider, base={}, search=search_dirs()),
                workspace=root,
            )
            session = await opened.open(tools=(relay_source(port),), workspace=str(root))
            held["session"] = session
            held["ready"].set_result(None)
            await held["finished"]
            await session.close()
        return Completed({"turns": held.get("turns", 0)})

    import asyncio

    held["ready"] = asyncio.get_running_loop().create_future()
    held["finished"] = asyncio.get_running_loop().create_future()

    ports = workshop(root)
    # `replace`, not `__class__(**__dict__)`: the latter copies a frozen dataclass by side-stepping
    # its own constructor, so every argument arrives untyped and nothing can see that the component
    # tuple went to `components` rather than to `governance`. It type-checks by accident, which is
    # worse than not type-checking at all.
    ports = replace(
        ports, components=(*ports.components, InMemoryComponents([(CONVERSE, converse)]))
    )
    plan = Composition((Invoke("converse", "converse", (Binding("brief", value=""),)),))

    async def drive() -> None:
        async for event in run(plan, ports, options=RunOptions(lease=a_lease())):
            if on_event is not None:
                on_event(event)

    driving = asyncio.create_task(drive())
    try:
        await held["ready"]
        yield Talker(held)
    finally:
        if not held["finished"].done():
            held["finished"].set_result(None)
        await driving


class Talker:
    """What the caller holds: one method, and a count of what it cost."""

    def __init__(self, held: dict[str, Any]) -> None:
        self._held = held

    async def turn(self, prompt: str) -> Any:
        self._held["turns"] = self._held.get("turns", 0) + 1
        return await self._held["session"].turn(prompt)


__all__ = ["NoProvider", "Talker", "a_conversation", "ready_provider", "relay_source"]
