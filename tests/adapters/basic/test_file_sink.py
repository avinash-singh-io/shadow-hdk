"""A sink that does not return until the line is on disk.

Durability cannot be tested without a crash, so each test says what it proves: the line is visible
to another descriptor before `propose` returns (it left the process), `fsync` was asked of the
file's own descriptor (it was told to leave the page cache), a torn tail — what a crash mid-write
leaves — does not poison the next read, and a write that fails raises rather than pretending.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest
from pydantic import JsonValue

from shadow_hdk.adapters.basic import AllowAll, FileSink, proposals_in
from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    Floor,
    Invoke,
    Lease,
    Observation,
    Proposal,
)
from shadow_hdk.kernel.contracts import load
from shadow_hdk.runtime import Ports, RunOptions, current_run, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ScriptedModel,
    make_registration,
)

LOOK = make_registration("look")


def a_proposal(n: int) -> Proposal:
    return Proposal(
        kind="finding", payload={"n": n, "text": "lathe " * n}, provenance=LOOK.component.provenance
    )


async def test_the_line_is_visible_to_another_descriptor_before_propose_returns(
    tmp_path: Path,
) -> None:
    sink = FileSink(tmp_path / "proposals.jsonl")
    await sink.propose(a_proposal(1))
    raw = (tmp_path / "proposals.jsonl").read_bytes()
    assert raw.endswith(b"\n") and raw.count(b"\n") == 1
    assert load(raw.decode("utf-8"), Proposal) == a_proposal(1)


def _watching_fsync(monkeypatch: pytest.MonkeyPatch, synced: list[int]) -> None:
    real = os.fsync

    def spy(fd: int) -> None:
        synced.append(os.fstat(fd).st_ino)
        real(fd)

    monkeypatch.setattr(os, "fsync", spy)


async def test_fsync_is_asked_of_this_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The one thing about durability that can be observed without a crash. `fsync` flushes the
    *file*, whichever descriptor names it, so the inode is what this proves — a sink that opened
    a second descriptor to sync would leak one per proposal and still be durable.

    Watched from **after** construction, because the sink also syncs the directory once when it
    creates the name (BUG-014), and that is a different claim tested below. Watching from before
    would fold the two together and make either of them able to satisfy this one.
    """
    path = tmp_path / "proposals.jsonl"
    sink = FileSink(path)
    synced: list[int] = []
    _watching_fsync(monkeypatch, synced)

    await sink.propose(a_proposal(1))

    assert synced == [os.stat(path).st_ino], "fsync was not asked of this file, once, per proposal"


async def test_the_directory_is_synced_once_when_the_name_is_created(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`fsync` on the file makes its **contents** durable; the directory entry is a separate write.

    Without this a crash straight after `O_CREAT` could leave a machine with fsynced bytes and no
    name to find them under. Once, at construction — a name is created once, and syncing a directory
    per proposal would be a cost paid on every record for a guarantee already held.
    """
    synced: list[int] = []
    _watching_fsync(monkeypatch, synced)
    path = tmp_path / "proposals.jsonl"

    sink = FileSink(path)
    await sink.propose(a_proposal(1))
    sink.close()

    assert synced[0] == os.stat(tmp_path).st_ino, "the directory holding the name was not synced"
    assert synced.count(os.stat(tmp_path).st_ino) == 1, "the directory was synced more than once"


async def test_a_torn_tail_does_not_poison_the_next_read(tmp_path: Path) -> None:
    path = tmp_path / "proposals.jsonl"
    sink = FileSink(path)
    await sink.propose(a_proposal(1))
    await sink.propose(a_proposal(2))
    with path.open("ab") as torn:
        torn.write(b'{"kind": "finding", "payl')  # the process died here
    assert list(proposals_in(path)) == [a_proposal(1), a_proposal(2)]
    with path.open("ab") as rest:
        rest.write(b'oad": {"n": 3, "text": "lathe lathe lathe "}, "provenance": ')
        rest.write(
            b'{"registered_by": "tests", "adapter": "tests", "at": "2026-01-01T00:00:00+00:00"}}\n'
        )
    assert [p.payload for p in proposals_in(path)][-1] == {"n": 3, "text": "lathe lathe lathe "}


def test_a_whole_line_that_is_not_a_proposal_is_an_error_that_names_the_line(
    tmp_path: Path,
) -> None:
    """A torn tail is what a crash leaves and is expected; a complete wrong line is corruption."""
    path = tmp_path / "proposals.jsonl"
    path.write_bytes(b'{"kind": "finding"}\nnot json at all\n')
    with pytest.raises(ValueError, match=r"proposals\.jsonl:1"):
        list(proposals_in(path))


async def test_a_write_that_fails_raises_and_through_a_run_the_run_fails(tmp_path: Path) -> None:
    """The descriptor is closed under the sink, which from here is what a full disk is: an
    `OSError` from `write`. A proposal that was not recorded must not be reported as recorded.

    **This test used to assert the *step* failed, and cited D7 while doing the opposite of what D7
    says** (TD-006). The sink is a **port**: *a component raising is data; a port raising is a
    failure*. A step-level `Failed` is something an agent routes around — so a host whose sink could
    not write watched the run carry on producing work nothing was keeping. Ending the run is the
    harsher answer and the correct one, because a sink that cannot write is a gate that is shut.
    """
    sink = FileSink(tmp_path / "proposals.jsonl")
    sink.close()
    with pytest.raises(OSError):
        await sink.propose(a_proposal(1))

    async def proposes(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        await context.propose(a_proposal(2))
        return Completed("recorded")

    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(LOOK, proposes)]),),
        governance=AllowAll(),
        sink=sink,
        clock=FixedClock(),
    )
    events = [
        e
        async for e in run(
            Composition((Invoke("s1", LOOK.id),)),
            ports,
            options=RunOptions(lease=Lease(Ceiling(5, 600, 10), Floor(0))),
        )
    ]
    ended = [e for e in events if e.kind == "ended"][-1]
    assert ended.reason == "failed", "a sink that cannot write let the run carry on"
    assert "sink" in str(ended.detail), f"the run ended without naming the port: {ended.detail}"
    assert [e.kind for e in events].count("proposed") == 0, (
        "a proposal the sink never took was announced anyway"
    )
    assert "OSError" in str(ended.detail)
    assert (tmp_path / "proposals.jsonl").read_bytes() == b""


async def test_the_sink_appends_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "proposals.jsonl"
    await FileSink(path).propose(a_proposal(1))
    await FileSink(path).propose(a_proposal(2))
    assert list(proposals_in(path)) == [a_proposal(1), a_proposal(2)]


def test_the_record_is_private_to_its_owner(tmp_path: Path) -> None:
    path = tmp_path / "proposals.jsonl"
    FileSink(path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_a_sink_that_cannot_be_written_refuses_to_exist(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        FileSink(tmp_path / "no-such-dir" / "proposals.jsonl")
