"""Generic optional resource teardown, with no knowledge of a component's vocabulary."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from shadow_hdk.kernel.ports import RunResourcePort


async def release_resources(ports: Iterable[object], scope: str) -> str | None:
    resources = {id(port): port for port in ports if isinstance(port, RunResourcePort)}
    failures: list[str] = []
    for port in reversed(list(resources.values())):
        try:
            await port.release_run(scope)
        except (Exception, asyncio.CancelledError) as error:
            failures.append(f"{type(error).__name__}: {error}")
    return "; ".join(failures) or None


async def settle_resources[T](task: asyncio.Task[T]) -> tuple[T, bool]:
    """An owner's cancellation must wait for teardown, then reach its caller."""
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    return task.result(), cancelled
