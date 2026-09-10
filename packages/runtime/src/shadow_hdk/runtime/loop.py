"""The drive — `Started` … `Ended`, and the two ways a run begins.

`run()` is an async generator: it yields events **while** the graph runs, on a task of its own, so a
host watching a long run sees it happen rather than hearing about it afterwards. If an observer is
bound it is fed in parallel (D6).

A run started while a step is executing is a **child** (D2): it finds its parent through the
contextvar, carves its lease from what the parent has left, announces itself on the parent's stream
as `Spawned`, and forwards its own events there verbatim — so one consumer sees the whole tree, and
every event says which run it belongs to.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from shadow_hdk.kernel.composition import Composition
from shadow_hdk.kernel.events import Composed, Ended, EndReason, Event, Started
from shadow_hdk.runtime.bindings import _CURRENT, MISSING, Ports, RunContext, RunOptions
from shadow_hdk.runtime.compile import compile_composition
from shadow_hdk.runtime.emit import Emitter
from shadow_hdk.runtime.errors import RuntimeStop
from shadow_hdk.runtime.registry import Registry
from shadow_hdk.runtime.session import Session
from shadow_hdk.runtime.state import initial_state, no_spend
from shadow_hdk.runtime.step import StepExecutor

RECURSION_HEADROOM = 4
"""LangGraph counts every node, not every step. A composition's own ceiling is its lease."""


def _parent_of(options: RunOptions) -> RunContext | None:
    """`MISSING` means *look for an ambient parent*; `None` means *be a root* (D2)."""
    if options.parent is MISSING:
        return _CURRENT.get()
    parent: RunContext | None = options.parent
    return parent


def _stop_reason(error: BaseException) -> tuple[EndReason, str | None] | None:
    """LangGraph may wrap a node's exception, so the chain is walked rather than the top checked.

    The *words* come back too: a host reading the record should be able to tell "the user closed the
    tab" from a budget ceiling, and both from a port that broke.
    """
    seen: BaseException | None = error
    while seen is not None:
        if isinstance(seen, RuntimeStop):
            return seen.reason, str(seen) or None
        seen = seen.__cause__ or seen.__context__
    return None


async def _drive(
    composition: Composition,
    ports: Ports,
    session: Session,
    emitter: Emitter,
    context: RunContext,
    registry: Registry,
    parent: RunContext | None,
    payload: Any,
    checkpointer: Any,
) -> None:
    token = _CURRENT.set(context)
    try:
        if not isinstance(payload, Command):
            await emitter.emit(
                lambda **k: Started(
                    lease=session.meter.lease, parent_run_id=session.parent_run_id, **k
                )
            )
            if parent is not None:
                await parent.announce_child(session.run_id, session.meter.lease)
            await emitter.emit(lambda **k: Composed(composition=composition, **k))

        executor = StepExecutor(session, emitter, ports, registry)
        config = {
            "configurable": {"thread_id": session.run_id},
            "recursion_limit": session.meter.lease.ceiling.max_steps * RECURSION_HEADROOM,
        }

        reason: EndReason = "completed"
        detail: str | None = None
        parked = False
        try:
            # Compiling is inside the guard: a composition an agent authored badly — a repeated
            # step id, say — is *its* mistake, and D7 says no exception from here escapes `run()`.
            # It ends the run with a reason on the record instead of a traceback at the caller.
            graph = compile_composition(composition, executor, checkpointer)
            result = await graph.ainvoke(payload, config=config)
            parked = isinstance(result, dict) and "__interrupt__" in result
        except BaseException as error:  # noqa: BLE001 — every stop is a reason, never a traceback
            stop = _stop_reason(error)
            reason, detail = stop if stop is not None else ("failed", str(error) or None)
            if reason == "failed" and not isinstance(error, Exception):
                raise

        # A parked run has not ended. `Ended` waits for whoever resumes it.
        if not parked:
            await emitter.emit(
                lambda **k: Ended(
                    reason=reason, steps_taken=session.meter.steps, detail=detail, **k
                )
            )
    finally:
        _CURRENT.reset(token)
        if parent is not None:
            # Always paired with the carve, including when the run ended badly: a reservation held
            # by a run that has stopped is budget lost to nobody.
            parent.settle(
                session.meter.lease.ceiling,
                steps=session.meter.steps,
                cost_cents=session.meter.cost_cents,
                cost_known=session.meter.cost_is_known,
            )
        emitter.close()


async def _carried(options: RunOptions, run_id: str) -> dict[str, float]:
    """What earlier legs of this run already spent, read from the checkpoint (D33).

    The runtime owns nothing durable (`09` §6), so the only place a parked run's spend can have
    survived is the checkpoint the host holds. A checkpointer that answers neither shape, or a
    thread with nothing in it, means *nothing spent yet* — a first leg, which is the truth.
    """
    checkpointer = options.checkpointer
    if checkpointer is None:
        return no_spend()
    config = {"configurable": {"thread_id": run_id}}
    try:
        if hasattr(checkpointer, "aget_tuple"):
            found = await checkpointer.aget_tuple(config)
        else:
            found = await asyncio.to_thread(checkpointer.get_tuple, config)
    except Exception:  # noqa: BLE001 — an unreadable checkpoint is a first leg, not a crash
        return no_spend()
    values = getattr(found, "checkpoint", {}).get("channel_values", {}) if found else {}
    spent = values.get("spent")
    carried = {**no_spend(), **spent} if isinstance(spent, dict) else no_spend()
    # The state's mark was written when the last node returned; a step that parked emitted its
    # `Asked` or `Observed(Pending)` *after* that, and said where to continue in the interrupt it
    # raised. A fan-out can park more than once, so the furthest one wins.
    carried["seq"] = max(carried["seq"], _resume_seq(found))
    return carried


def _resume_seq(found: Any) -> int:
    furthest = 0
    for write in getattr(found, "pending_writes", None) or ():
        if len(write) < 3 or write[1] != "__interrupt__":
            continue
        for interrupt in write[2] if isinstance(write[2], list | tuple) else (write[2],):
            value = getattr(interrupt, "value", None)
            if isinstance(value, dict) and isinstance(value.get("resume_seq"), int):
                furthest = max(furthest, value["resume_seq"])
    return furthest


async def _stream(
    composition: Composition, ports: Ports, options: RunOptions, payload: Any
) -> AsyncIterator[Event]:
    parent = _parent_of(options)
    run_id = options.run_id or ports.clock.new_id()
    # One place carves, whoever asked: a child is never promised more than its parent still holds.
    lease = parent.reserve(options.lease.ceiling) if parent is not None else options.lease
    session = Session(
        run_id=run_id,
        lease=lease,
        clock=ports.clock,
        context=dict(options.context),
        principal=options.principal,
        parent_run_id=parent.run_id if parent is not None else None,
        cancellation=options.cancellation,
    )
    # Only the **root** feeds the observer. A child forwards its events to its parent, which
    # forwards them on, so the observer is reached exactly once however deep the tree; a child that
    # also called it would report an event once per level it sits under.
    emitter = Emitter(run_id, ports.clock, ports.observer if parent is None else None)
    if isinstance(payload, Command):
        # A resume continues a run; it does not start one (D33). The meter and the record's
        # numbering pick up where the parked leg left them.
        carried = await _carried(options, run_id)
        session.meter.restore(carried)
        emitter.restore(int(carried["seq"]))
    registry = Registry(ports.components, trust=ports.trust)
    context = RunContext(session, emitter, ports, registry)
    driving = asyncio.create_task(
        _drive(
            composition,
            ports,
            session,
            emitter,
            context,
            registry,
            parent,
            payload,
            options.checkpointer or InMemorySaver(),
        )
    )
    try:
        async for event in emitter.stream():
            if parent is not None:
                await parent.forward(event)
            yield event
    finally:
        await driving
        await emitter.drained()


def run(composition: Composition, ports: Ports, *, options: RunOptions) -> AsyncIterator[Event]:
    """Execute a composition. Yields every event as it happens, and feeds the observer if bound.

    A component's failure is never raised — it is a `Failed` observation. A *port's* failure ends
    the run with `Ended(reason="failed")` rather than a traceback (D7).
    """
    return _stream(composition, ports, options, initial_state())


def resume(
    composition: Composition, answer: Any, ports: Ports, *, options: RunOptions
) -> AsyncIterator[Event]:
    """Continue a run parked on an `Ask` or an `Await`.

    **The composition is passed back in.** The runtime owns nothing durable (`09` §6), so it cannot
    remember the shape of a run it parked — the checkpointer holds the state, and whoever resumes
    holds the plan. `options.run_id` and `options.checkpointer` are both required: without the first
    there is no thread to resume, and without the second there is nothing to resume from.
    """
    if options.run_id is None:
        raise ValueError("resume needs options.run_id — the run to continue")
    if options.checkpointer is None:
        raise ValueError("resume needs options.checkpointer — the one the run was parked with")
    return _stream(composition, ports, options, Command(resume=answer))


__all__ = ["resume", "run"]
