"""Open a thread on this machine's provider — nothing here that is not the harness's (D62).

    async with a_thread(root, mode="workspace-write") as thread:
        async for event in thread.turn("hello"):
            ...

The provider is whichever CLI is signed in here (`providers.ready`), opened through its file
(`open_with`); the registry is served to it over the authenticated socket for the thread's
lifetime (`SocketOffer`); the environment and the policy are the workshop's; the thread keeps its
record in memory. A product would hand in its own store, policy and approvals — this example
composes the harness's parts and adds none of its own.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any

from shadow_hdk.adapters.recording import SocketOffer

from examples.coder.workshop import a_lease, modes_for, workshop
from shadow_hdk.kernel import ThreadStore
from shadow_hdk.providers import environment_for, open_with, ready, search_dirs
from shadow_hdk.runtime import Approvals
from shadow_hdk.runtime.environment import Mode as EnvironmentMode
from shadow_hdk.runtime.threads import TURN, InMemoryThreads, Thread


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
) -> AsyncIterator[Thread]:
    """A thread on the provider signed in here, its tools this run's, inside the workshop.

    `approvals` is where the policy's approval requests about the provider's tool calls go while
    the provider waits on them (D58). Without one, a call the policy asks about is refused: nobody
    was there to ask. `observer` hears the record and, through `on_activity`, what is happening
    beside it (D63).
    """
    root.mkdir(parents=True, exist_ok=True)
    available = await ready(want)
    assert available.binary is not None, "a ready provider has a binary"
    opened = await open_with(
        available.provider,
        binary=available.binary,
        env=environment_for(available.provider, base={}, search=search_dirs()),
        workspace=root,
    )
    modes = modes_for(store, files=root / ".harness" / "modes")  # live: rows and files (D66)
    thread = await Thread.open(
        agent=opened,
        ports=replace(
            await workshop(root, mode=mode, rules=rules, store=store, modes=modes),
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
        provider=f"{available.provider.called} {available.version or ''}".strip(),
    )
    try:
        yield thread
    finally:
        await thread.close()


__all__ = ["a_thread"]
