"""Where proposals go when the host has not decided yet: to the screen, or to a function.

Both are honest sinks — the runtime proposes and something else keeps or discards. `StdoutSink`
keeps nothing, which is the right default for a demo and the wrong one for a product.
"""

from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable
from typing import TextIO

from shadow_hdk.kernel.contracts import dump
from shadow_hdk.kernel.observations import Proposal
from shadow_hdk.kernel.ports import SinkPort


class StdoutSink(SinkPort):
    """One JSON line per proposal."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream if stream is not None else sys.stdout

    async def propose(self, proposal: Proposal) -> None:
        self._stream.write(dump(proposal, Proposal) + "\n")
        self._stream.flush()


class CallbackSink(SinkPort):
    """A function of your own. The shortest path from the runtime to a host's gate."""

    def __init__(self, on_proposal: Callable[[Proposal], Awaitable[None] | None]) -> None:
        self._on = on_proposal

    async def propose(self, proposal: Proposal) -> None:
        result = self._on(proposal)
        if result is not None:
            await result
