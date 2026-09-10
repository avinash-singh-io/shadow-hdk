"""Where proposals go when the host has not decided yet: to the screen, to a function, to a file.

All three are honest sinks — the runtime proposes and something else keeps or discards.
`StdoutSink` keeps nothing, which is the right default for a demo and the wrong one for a product.
`FileSink` keeps everything and does not return until it is on disk.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Awaitable, Callable, Iterator
from pathlib import Path
from typing import TextIO

from pydantic import ValidationError

from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.kernel.observations import Proposal
from shadow_hdk.kernel.ports import SinkPort


class StdoutSink(SinkPort):
    """One JSON line per proposal."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream if stream is not None else sys.stdout

    async def propose(self, proposal: Proposal) -> None:
        self._stream.write(dump(proposal, Proposal) + "\n")
        self._stream.flush()


class FileSink(SinkPort):
    """One JSON line per proposal, on disk before `propose` returns.

    The descriptor is opened at construction — a sink that cannot be written refuses to exist —
    with `O_APPEND`, so every write lands at the end whatever else holds the file, and mode 0600,
    because a record of what an agent proposed is the owner's. Each proposal is one `write` and
    one `fsync`; a write that fails **raises**, and the step that proposed becomes `Failed` (D7),
    because a proposal that was not recorded must not be reported as recorded.
    """

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self._fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)

    async def propose(self, proposal: Proposal) -> None:
        line = (dump(proposal, Proposal) + "\n").encode("utf-8")
        os.write(self._fd, line)
        os.fsync(self._fd)

    def close(self) -> None:
        os.close(self._fd)


def proposals_in(path: str | os.PathLike[str]) -> Iterator[Proposal]:
    """The record, read back. Stops at a torn tail — a line with no newline is what a crash
    mid-write leaves, and the writer never finished it — but a complete line that is not a
    proposal is corruption, and says which line."""
    with Path(path).open("rb") as record:
        for number, raw in enumerate(record, 1):
            if not raw.endswith(b"\n"):
                return
            try:
                yield load(raw.decode("utf-8"), Proposal)
            except (ValidationError, UnicodeDecodeError) as bad:
                raise ValueError(f"{Path(path).name}:{number} is not a proposal") from bad


class CallbackSink(SinkPort):
    """A function of your own. The shortest path from the runtime to a host's gate."""

    def __init__(self, on_proposal: Callable[[Proposal], Awaitable[None] | None]) -> None:
        self._on = on_proposal

    async def propose(self, proposal: Proposal) -> None:
        result = self._on(proposal)
        if result is not None:
            await result
