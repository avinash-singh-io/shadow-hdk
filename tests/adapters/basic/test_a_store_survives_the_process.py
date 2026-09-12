"""A `Store` on sqlite: live data outlives the process (D66)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from shadow_hdk.adapters.basic import SqliteStore

from tests.adapters.contract.suites import StoreContract

pytestmark = pytest.mark.anyio


class TestSqliteStoreIsAStore(StoreContract):
    def store(self) -> SqliteStore:
        return SqliteStore(Path(tempfile.mkdtemp()) / "live.sqlite")


async def test_a_second_store_over_the_same_file_sees_the_rows_and_the_version(
    tmp_path: Path,
) -> None:
    where = tmp_path / "live.sqlite"
    first = SqliteStore(where)
    await first.put("modes", "calm", {"id": "calm"})
    second = SqliteStore(where)
    assert await second.get("modes", "calm") == {"id": "calm"}
    assert await second.version("modes") == 1
