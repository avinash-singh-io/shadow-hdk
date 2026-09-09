"""The bare-harness test — the definition of done for "generic" (09 §1, §11; 10 §5 R0).

A composition runs against an MCP server, an Ollama model and a sub-agent, governed by allow-all,
with every event written to stdout, using zero lines of any product's code. Until the runtime
exists this is an expected failure; ``xfail_strict`` means the day it passes, the marker must
come off — the test cannot quietly become decoration.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.xfail(
    raises=NotImplementedError,
    reason="R0 in progress: run() exists (Group 3); the demo needs the agent component (Group 4)",
)
def test_the_bare_harness_runs_with_zero_product_code() -> None:
    # The plain async entry point, 09 §3 — resolved at run time so the test can exist before it.
    run = importlib.import_module("shadow_hdk.runtime").run

    assert callable(run), "the entry point exists; what is missing is the demo it drives"
    raise NotImplementedError("Group 4/5: an agent component, a sub-agent, allow-all, stdout")
