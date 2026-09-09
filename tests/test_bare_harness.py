"""The bare-harness test — the definition of done for "generic" (09 §1, §11; 10 §5 R0).

A composition runs against an MCP server, an Ollama model and a sub-agent, governed by allow-all,
with every event written to stdout, using zero lines of any product's code. Until the runtime
exists this is an expected failure; ``xfail_strict`` means the day it passes, the marker must
come off — the test cannot quietly become decoration.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.xfail(raises=ImportError, reason="R0: the runtime does not exist yet")
def test_the_bare_harness_runs_with_zero_product_code() -> None:
    # The plain async entry point, 09 §3 — resolved at run time so the test can exist before it.
    run = importlib.import_module("shadow_hdk.runtime").run

    raise AssertionError(f"write the run with {run}: MCP + Ollama + sub-agent, allow-all, stdout")
