"""Where proposals go when the host has not decided yet: to the screen, to a function, to a file.

All three are honest sinks — the runtime proposes and something else keeps or discards.
`StdoutSink` keeps nothing, which is the right default for a demo and the wrong one for a product.
`FileSink` keeps everything and does not return until it is on disk.
"""

from __future__ import annotations

import asyncio
import contextlib
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
        _discard_a_torn_tail(self.path)
        self._fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        self._closed = False
        _make_the_name_durable(self.path)

    async def propose(self, proposal: Proposal) -> None:
        line = (dump(proposal, Proposal) + "\n").encode("utf-8")
        # **Off the loop thread** (BUG-014). `write` and `fsync` wait on hardware, and they ran
        # inside an `async def` on the event loop, so one slow disk stalled every other run in the
        # process — including the ones not writing anything.
        await asyncio.to_thread(self._record, line)

    def _record(self, line: bytes) -> None:
        _write_all(self._fd, line)
        os.fsync(self._fd)

    def close(self) -> None:
        """Idempotent, because `__exit__` runs and a careful host closes in its own teardown too."""
        if not self._closed:
            self._closed = True
            os.close(self._fd)

    def __enter__(self) -> FileSink:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _write_all(fd: int, data: bytes) -> None:
    """Every byte, or raise (BUG-014).

    `os.write` returns how many bytes it took and nothing read it, so half a record could reach the
    disk while `propose` returned as though all of it had — against this class's own promise that a
    proposal not recorded is never reported as recorded.

    A partial write is **ordinary**: a signal arrives mid-call, a pipe fills. So the rest is
    written rather than treated as a failure. What is a failure is a write that stops making
    progress, and that raises with how far it got, because *the disk is full* and *the disk is slow*
    want different answers from whoever reads it.
    """
    written = 0
    while written < len(data):
        just = os.write(fd, data[written:])
        if just <= 0:
            raise OSError(
                f"wrote {written} of {len(data)} bytes to the record and then stopped; "
                "the proposal is not recorded"
            )
        written += just


def _discard_a_torn_tail(path: Path) -> None:
    """Cut back to the last complete line before anything is appended (BUG-014).

    A crash mid-write leaves bytes with no newline. `proposals_in` stops there, which is right and
    was already tested — but the **next process** opened the same file `O_APPEND` and wrote straight
    onto the end of it, gluing its first proposal to the half-written one. Measured: two good
    proposals became unreachable behind `p.jsonl:2 is not a proposal`. A crash that cost nothing on
    its own became total loss the moment the process came back.

    **Discarding is not data loss.** `propose` does not return until the record is on disk, so an
    unfinished record is one whose caller was never told it was recorded. Keeping it would preserve
    half a line that no reader can use and every reader must step over.

    This also retires an equivalent-mutant claim from Phase 14 — *a torn line can only be the last*
    — which holds within one process's lifetime and fails across a restart, and a restart is the
    only time a torn line exists. Phase 14's other claim, that `fsync` is per-inode, still holds.

    **The healthy-file early return is a fast path, not a rule, and removing it is an equivalent
    mutant** — named here so the next pass does not spend a test deriving it again. A file ending
    in a newline has its last newline at `len - 1`, so `keep` is the file's own length and the
    truncate is a no-op. The return saves a syscall on every open and says the intent out loud.
    """
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open("rb") as record:
        content = record.read()
    if content.endswith(b"\n"):
        return
    keep = content.rfind(b"\n") + 1  # 0 when there is no complete line at all
    os.truncate(path, keep)


def _make_the_name_durable(path: Path) -> None:
    """`fsync` on the file makes its **contents** durable; the directory entry is a separate write.

    A crash right after `O_CREAT` could otherwise leave a machine with fsynced bytes and no file to
    find them under. Once at construction, because a name is created once — and best-effort,
    because some filesystems refuse to open a directory for this and a sink that cannot exist on
    them is a worse answer than one whose first record is a little less durable.
    """
    with contextlib.suppress(OSError):
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


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
