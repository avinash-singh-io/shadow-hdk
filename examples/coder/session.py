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

from shadow_hdk.adapters.recording import (
    PORT_VARIABLE,
    TOKEN_VARIABLE,
    RecordingServer,
    serve_over_socket,
)

from examples.coder.workshop import a_lease, workshop
from shadow_hdk.kernel import (
    Binding,
    Completed,
    Composition,
    EffectProfile,
    Ended,
    Event,
    Invoke,
    Observation,
    Refused,
    ScopeSet,
    ToolSource,
)
from shadow_hdk.providers import detect, environment_for, open_with, search_dirs, shipped
from shadow_hdk.runtime import Questions, RunOptions, current_run, run
from shadow_hdk.runtime.environment import Mode as EnvironmentMode
from shadow_hdk.runtime.testing import InMemoryComponents, make_registration

RELAY = "shadow-hdk-registry"

CONVERSE = make_registration(
    "converse",
    # What holding the conversation *itself* writes: the provider's own state — a session
    # transcript under its home, never the root, because its file tools are withheld and every
    # write to the root goes through this run's environment and is judged there. Declaring
    # `workspace` here made `read-only` refuse the conversation before it began (measured
    # 2026-09-12: *the run ended before the conversation started*), when what read-only means is
    # that the *tools* may not write.
    effects=EffectProfile(
        reads=ScopeSet(everything=True),
        writes=ScopeSet.of("provider-state"),
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


def relay_source(port: int, token: str) -> ToolSource:
    """Where the provider's tools are — and under D42 they are ours; under D52, only with the token.

    The relay must be on the path the *child* will search, not merely on ours: it is launched by the
    CLI, in the environment we hand the CLI, and a `PATH` that resolved it here and not there is the
    asymmetry the resolution module exists to prevent.
    """
    found = shutil.which(RELAY)
    return ToolSource(
        kind="mcp",
        address=found or RELAY,
        env=((PORT_VARIABLE, str(port)), (TOKEN_VARIABLE, token)),
    )


@asynccontextmanager
async def a_conversation(
    root: Path,
    *,
    want: str | None = None,
    mode: EnvironmentMode = "workspace-write",
    on_event: Callable[[Event], None] | None = None,
    questions: Questions | None = None,
) -> AsyncIterator[Any]:
    """A resident provider whose only tools are this run's, inside a live run.

    `questions` is where the policy's questions about the provider's tool calls go while the
    provider waits on them (D58) — the person at the terminal, in this example. Without one, a
    call the policy asks about is refused: nobody was there to ask.

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
        holder = RecordingServer(context, withhold=held_back)
        async with (
            holder.served() as server,
            serve_over_socket(server, refused=holder.refuse) as (port, token),
        ):
            opened = await open_with(
                available.provider,
                binary=available.binary,
                env=environment_for(available.provider, base={}, search=search_dirs()),
                workspace=root,
            )
            session = await opened.open(tools=(relay_source(port, token),), workspace=str(root))
            held["session"] = session
            held["provider"] = f"{available.provider.called} {available.version or ''}".strip()
            held["ready"].set_result(None)
            await held["finished"]
            await session.close()
        return Completed({"turns": held.get("turns", 0)})

    import asyncio

    held["ready"] = asyncio.get_running_loop().create_future()
    held["finished"] = asyncio.get_running_loop().create_future()

    ports = await workshop(root, mode=mode)
    # `replace`, not `__class__(**__dict__)`: the latter copies a frozen dataclass by side-stepping
    # its own constructor, so every argument arrives untyped and nothing can see that the component
    # tuple went to `components` rather than to `governance`. It type-checks by accident, which is
    # worse than not type-checking at all.
    ports = replace(
        ports, components=(*ports.components, InMemoryComponents([(CONVERSE, converse)]))
    )
    plan = Composition((Invoke("converse", "converse", (Binding("brief", value=""),)),))

    async def drive() -> None:
        """Run the conversation, and **never leave the caller waiting on a signal that is not
        coming.**

        The step holding the conversation is judged like any other, and a mode that refuses it ends
        the run before `converse` executes — so `ready` is never set and `a_conversation` waits for
        ever. Measured: a confined mode that forbade `reaches` produced a ten-minute hang with no
        output, which is a worse failure than the refusal it was hiding.

        Whatever ends the run, the caller is told.
        """
        reason = "the run ended before the conversation started"
        try:
            options = RunOptions(lease=a_lease(), questions=questions)
            async for event in run(plan, ports, options=options):
                if isinstance(event, Refused) and event.step == "converse":
                    reason = f"the conversation was refused: {event.reason}"
                if isinstance(event, Ended) and event.reason != "completed":
                    reason = f"the run ended {event.reason}: {event.detail or ''}".strip()
                if on_event is not None:
                    on_event(event)
        finally:
            if not held["ready"].done():
                held["ready"].set_exception(NoProvider(reason))

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

    @property
    def provider(self) -> str:
        """Which provider is doing the reasoning, as detected — for a host that shows it."""
        return str(self._held.get("provider", ""))


__all__ = ["NoProvider", "Talker", "a_conversation", "ready_provider", "relay_source"]
