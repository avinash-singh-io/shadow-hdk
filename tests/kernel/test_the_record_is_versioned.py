"""The record versioned (Phase 30 group 5, D93).

`ThreadRecord.version` says which shape a record was written with: 1 for every record before
the field existed (0.28.0 added five fields with defaults; every old record still loads), 2 for
this kit's writes. A product mapping the record to columns reads the version first; an older
record picked up by this kit is written back in this kit's shape, and says so.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from shadow_hdk.kernel import RECORD_VERSION, ThreadRecord
from shadow_hdk.kernel.contracts import dump, load
from shadow_hdk.runtime.threads import InMemoryThreads, Thread
from shadow_hdk.testing import ScriptedAgent

pytestmark = pytest.mark.anyio


def test_a_record_written_before_the_field_reads_as_version_one() -> None:
    old = {"id": "t", "root": "/w", "created_at": "2026-09-01T00:00:00+00:00", "turns": []}
    record = load(json.dumps(old), ThreadRecord)
    assert record.version == 1
    assert record.pending == () and record.principal == "" and record.spent.steps == 0
    assert json.loads(dump(record, ThreadRecord))["version"] == 1, "read as it was, until written"


async def test_a_new_thread_writes_this_kits_version_and_an_old_one_is_written_back(
    tmp_path: Path,
) -> None:
    from tests.runtime.test_a_conversation_without_a_record import Seen, _lease, _ports

    store = InMemoryThreads()
    thread = await Thread.open(
        agent=cast(Any, ScriptedAgent([])),
        ports=_ports(Seen()),
        store=store,
        root=tmp_path,
        lease=_lease(),
    )
    try:
        assert thread.record.version == RECORD_VERSION == 2
        kept = await store.get(thread.id)
        assert kept is not None and kept.version == 2
    finally:
        await thread.close()

    await store.create(
        ThreadRecord(id="old", root=str(tmp_path), created_at="2026-09-01T00:00:00+00:00")
    )
    older = await store.get("old")
    assert older is not None and older.version == 1
    resumed = await Thread.resume(
        "old", agent=cast(Any, ScriptedAgent([])), ports=_ports(Seen()), store=store, lease=_lease()
    )
    try:
        assert resumed.record.version == 2
        rewritten = await store.get("old")
        assert rewritten is not None and rewritten.version == 2, "written back in this shape"
    finally:
        await resumed.close()
