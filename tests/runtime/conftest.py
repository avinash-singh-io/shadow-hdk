"""One builder, so every runtime test says what it is testing rather than how it is wired."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from pydantic import JsonValue

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    Floor,
    Lease,
    Observation,
    Registration,
)
from shadow_hdk.runtime.bindings import Ports
from shadow_hdk.runtime.effects import InMemoryEffectJournal
from shadow_hdk.runtime.emit import Emitter
from shadow_hdk.runtime.registry import Registry
from shadow_hdk.runtime.session import Session
from shadow_hdk.runtime.step import StepExecutor
from shadow_hdk.runtime.testing import (
    AllowAuthorizer,
    FixedAuthority,
    FixedClock,
    InMemoryComponents,
    Judge,
    ListObserver,
    ListSink,
    ScriptedModel,
)

Behaviour = Any
"""A literal to return as `Completed`, or an async callable taking inputs."""


def _handler(behaviour: Behaviour) -> Callable[[JsonValue], Awaitable[Observation]]:
    if callable(behaviour):
        handler: Callable[[JsonValue], Awaitable[Observation]] = behaviour
        return handler

    async def constant(_inputs: JsonValue) -> Observation:
        return Completed(behaviour)

    return constant


def ports_over(
    entries: Sequence[tuple[Registration, Behaviour]],
    *,
    judge: Judge | None = None,
    clock: FixedClock | None = None,
    observer: ListObserver | None = None,
    model: ScriptedModel | None = None,
    sink: ListSink | None = None,
) -> tuple[Ports, InMemoryComponents]:
    components = InMemoryComponents([(reg, _handler(b)) for reg, b in entries])
    clock = clock or FixedClock()
    return (
        Ports(
            model=model or ScriptedModel(),
            components=(components,),
            governance=judge or Judge.allow_all(),
            sink=sink or ListSink(),
            clock=clock,
            observer=observer,
            authority=FixedAuthority(),
            authorizer=AllowAuthorizer(),
            effect_journal=InMemoryEffectJournal(),
        ),
        components,
    )


def executor_over(
    entries: Sequence[tuple[Registration, Behaviour]],
    *,
    judge: Judge | None = None,
    context: dict[str, JsonValue] | None = None,
    principal: str | None = None,
    lease: Lease | None = None,
    clock: FixedClock | None = None,
) -> tuple[StepExecutor, InMemoryComponents, Emitter]:
    clock = clock or FixedClock()
    ports, components = ports_over(entries, judge=judge, clock=clock)
    session = Session(
        run_id="run-under-test",
        lease=lease or Lease(Ceiling(100, 3600, 10_000), Floor(0)),
        clock=clock,
        context=context,
        principal=principal,
    )
    emitter = Emitter(session.run_id, clock, None)
    registry = Registry(ports.components)
    return StepExecutor(session, emitter, ports, registry), components, emitter


async def drive(
    composition: Composition,
    entries: Sequence[tuple[Registration, Behaviour]],
    *,
    judge: Judge | None = None,
    lease: Lease | None = None,
    interruptible: bool = False,
    context: dict[str, JsonValue] | None = None,
) -> Any:
    """Compile and run one composition, returning its events.

    A thin stand-in for `run()`, which lands in Group 3. The point here is the *shape* of the
    graph, so this driver stays deliberately dumb. With `interruptible=True` it returns
    `(events_so_far, resume)` so a parked run can be let through.
    """
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command

    from shadow_hdk.runtime.compile import compile_composition
    from shadow_hdk.runtime.state import initial_state

    clock = FixedClock()
    ports, _ = ports_over(entries, judge=judge, clock=clock)
    session = Session(
        run_id="run-under-test",
        lease=lease or Lease(Ceiling(100, 3600, 10_000), Floor(0)),
        clock=clock,
        context=context,
    )
    emitter = Emitter(session.run_id, clock, None)
    executor = StepExecutor(session, emitter, ports, Registry(ports.components))
    graph = compile_composition(composition, executor, InMemorySaver())
    config = {"configurable": {"thread_id": session.run_id}, "recursion_limit": 100}

    async def collect(payload: Any) -> list[Any]:
        await graph.ainvoke(payload, config=config)
        events: list[Any] = []
        while not emitter._stream.empty():  # noqa: SLF001 — a test driver, not the API
            events.append(emitter._stream.get_nowait())  # noqa: SLF001
        return events

    first = await collect(initial_state())
    if not interruptible:
        return first

    async def resume(answer: Any) -> list[Any]:
        return await collect(Command(resume=answer))

    return first, resume
