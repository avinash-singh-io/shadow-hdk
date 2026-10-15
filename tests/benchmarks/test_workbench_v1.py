"""Frozen workbench-v1 budgets: 100,000 tracked files and 100,000 ignored files."""

import runpy
from pathlib import Path

import pytest

pytestmark = [pytest.mark.benchmark, pytest.mark.timeout(600)]


async def test_workbench_v1_budgets() -> None:
    driver = runpy.run_path(str(Path(__file__).parents[2] / "scripts/benchmark-workbench.py"))
    result = await driver["benchmark"](100_000)
    seconds = result["seconds"]
    print(result)
    budgets = {
        "glob": 3,
        "grep": 3,
        "snapshot_cold": 2,
        "snapshot_unchanged": 2,
        "snapshot_one_edit": 2,
        "restore": 5,
    }
    assert {key: value for key, value in seconds.items() if value > budgets[key]} == {}
