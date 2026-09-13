"""What a crash leaves behind is readable, and a write that did not finish raises (BUG-014).

`FileSink`'s promise is in its own docstring: *one JSON line per proposal, on disk before `propose`
returns*, and *a write that fails raises, and the step that proposed becomes `Failed` (D7), because
a proposal that was not recorded must not be reported as recorded*. Two things broke it.

**A short write was silent.** `os.write` returns how many bytes it took, and nothing read it. A
partial write is ordinary — a signal, a full disk, a pipe — and it left half a record on disk while
`propose` returned as though all of it were there.

**A torn tail plus a restart destroyed the record.** A crash mid-write leaves a line with no
newline; `proposals_in` stops there, which is correct and was tested. But the next process opened
the same file `O_APPEND` and wrote **straight onto the end of it**, gluing its first proposal to the
half-written one. Measured: three lines on disk, `p.jsonl:2 is not a proposal`, and the two good
proposals after the glue unreachable — a crash that cost nothing on its own became total loss the
moment the process came back.

**That last one retires an equivalent-mutant claim from Phase 14.** It reasoned that *a torn line
can only be the last*, which holds within one process's lifetime and fails across a restart — and a
restart is the only time a torn line exists. The other claim from that pass, that `fsync` is
per-inode, still holds and is cited rather than re-derived.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.adapters.basic.sinks import FileSink, proposals_in
from shadow_hdk.kernel.components import Provenance
from shadow_hdk.kernel.observations import Proposal

WHERE = Provenance(registered_by="tests", adapter="test", at="2026-01-01T00:00:00+00:00")


def a_proposal(n: int) -> Proposal:
    return Proposal(kind="claim", payload={"n": n}, provenance=WHERE)


def torn(path: Path) -> None:
    """What a crash mid-write leaves: bytes with no newline after them."""
    with path.open("ab") as record:
        record.write(b'{"kind":"claim","payl')


# ------------------------------------------------------------------ a write that did not finish


async def test_a_short_write_raises_rather_than_returning(tmp_path: Path, monkeypatch: Any) -> None:
    """The promise is that `propose` does not return until the record is on disk. A write that took
    half the bytes has not done that, and a caller told otherwise reports a proposal it does not
    have."""
    path = tmp_path / "p.jsonl"
    sink = FileSink(path)
    real = os.write

    def half(fd: int, data: bytes) -> int:
        return real(fd, data[: len(data) // 2])

    monkeypatch.setattr(os, "write", half)
    try:
        with pytest.raises(OSError, match="wrote"):
            await sink.propose(a_proposal(1))
    finally:
        monkeypatch.undo()
        sink.close()


async def test_a_write_that_takes_two_goes_is_not_a_failure(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """A partial write is **ordinary** — a signal arrives, a pipe fills — and the answer is to
    write the rest, not to fail. Only a write that stops making progress is a failure."""
    path = tmp_path / "p.jsonl"
    sink = FileSink(path)
    real, calls = os.write, []

    def in_pieces(fd: int, data: bytes) -> int:
        calls.append(len(data))
        return real(fd, data[: max(1, len(data) // 2)])

    monkeypatch.setattr(os, "write", in_pieces)
    try:
        await sink.propose(a_proposal(1))
    finally:
        monkeypatch.undo()
        sink.close()

    assert len(calls) > 1, "the arrangement failed: the write completed in one go"
    assert [p.payload for p in proposals_in(path)] == [{"n": 1}]


# ------------------------------------------------------------------ a crash, then a restart


async def test_a_restart_does_not_glue_itself_to_a_torn_record(tmp_path: Path) -> None:
    """The bug, at the size it was measured: two good proposals lost to one that never finished."""
    path = tmp_path / "p.jsonl"
    first = FileSink(path)
    await first.propose(a_proposal(1))
    first.close()
    torn(path)

    second = FileSink(path)
    await second.propose(a_proposal(2))
    await second.propose(a_proposal(3))
    second.close()

    assert [p.payload for p in proposals_in(path)] == [{"n": 1}, {"n": 2}, {"n": 3}]


def test_the_unfinished_record_is_discarded_rather_than_kept(tmp_path: Path) -> None:
    """Discarded, and that is not data loss: `propose` had not returned, so nobody was ever told
    the proposal was recorded. Keeping it would mean keeping half a record that no reader can use
    and every reader must step over."""
    path = tmp_path / "p.jsonl"
    path.write_bytes(b'{"kind":"claim","payl')

    FileSink(path).close()

    assert path.read_bytes() == b""


async def test_a_record_with_no_torn_tail_is_left_exactly_as_it_was(tmp_path: Path) -> None:
    """The repair must not touch a healthy file. A sink that rewrote its own history on every open
    would be a worse problem than the one it fixes."""
    path = tmp_path / "p.jsonl"
    first = FileSink(path)
    await first.propose(a_proposal(1))
    first.close()
    before = path.read_bytes()

    FileSink(path).close()

    assert path.read_bytes() == before


def test_an_empty_record_is_not_disturbed(tmp_path: Path) -> None:
    """A file that does not exist yet ends with no newline too, and must not be read as torn."""
    path = tmp_path / "p.jsonl"

    FileSink(path).close()

    assert path.exists()
    assert path.read_bytes() == b""


# ------------------------------------------------------------------ the loop, and the door


async def test_the_event_loop_is_not_blocked_while_the_disk_works(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """`fsync` is a syscall that waits on hardware, and it ran on the event loop inside an `async
    def`. One slow disk stalled every other run in the process.

    Asserted as a claim about the mechanism rather than a stopwatch: the sync happens off the loop
    thread, so a run that shares the loop keeps running.
    """
    path = tmp_path / "p.jsonl"
    sink = FileSink(path)
    import threading

    loop_thread = threading.current_thread().ident
    synced_on: list[int | None] = []
    real = os.fsync

    def note(fd: int) -> None:
        synced_on.append(threading.current_thread().ident)
        real(fd)

    monkeypatch.setattr(os, "fsync", note)
    try:
        await sink.propose(a_proposal(1))
    finally:
        monkeypatch.undo()
        sink.close()

    assert synced_on and synced_on[0] != loop_thread, "fsync ran on the event loop"


def test_the_sink_closes_itself(tmp_path: Path) -> None:
    """A descriptor opened at construction is a descriptor somebody has to close, and `close()`
    alone means a raise anywhere in between leaks one."""
    path = tmp_path / "p.jsonl"

    with FileSink(path) as sink:
        assert sink.path == path

    with pytest.raises(OSError):
        os.fstat(sink._fd)  # noqa: SLF001 — the claim is about the descriptor, not the object


async def test_closing_twice_is_not_an_error(tmp_path: Path) -> None:
    """`__exit__` runs, and a host that also calls `close()` in its own teardown should not meet a
    `Bad file descriptor` for being careful."""
    sink = FileSink(tmp_path / "p.jsonl")
    sink.close()

    sink.close()
