"""Phase 1's exit criterion: the harness on a real model and a real MCP server.

`test_bare_harness.py` proves the shape with a scripted model and a hand-written server.
This proves the **seams** — an HTTP wire, a subprocess, a policy that refuses — and it costs money,
so it is deselected by default and opted into with `uv run pytest -m live`.

What is asserted is the harness, never the model's cleverness: a model that wanders is a model
problem, and a test that fails when it wanders is a test that will fail for the wrong reason.
"""

from __future__ import annotations

import io
import json
import os
from typing import Any

import pytest
from examples.real import real_harness

from shadow_hdk.kernel import (
    Completed,
    Composed,
    Ended,
    Invoked,
    Observed,
    Proposed,
    Spawned,
    Started,
)

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not os.environ.get("INTENT_HF_TOKEN"),
        reason="INTENT_HF_TOKEN is not set; the live harness is opt-in because it costs money",
    ),
]


async def _run() -> tuple[list[Any], list[dict[str, Any]]]:
    out = io.StringIO()
    events = await real_harness(out)
    written = [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]
    return events, written


async def test_the_harness_runs_on_a_real_model_and_a_real_server() -> None:
    events, written = await _run()

    # It ran, and it finished.
    assert isinstance(events[0], Started)
    assert isinstance(events[-1], Ended)
    assert events[-1].reason == "completed"

    # A real model chose its own work, and the runtime ran it as a child run.
    assert [e for e in events if isinstance(e, Spawned)], "no turn was carried out"
    assert [e for e in events if isinstance(e, Composed)], "no plan was recorded"

    # A real MCP server answered, with the record its own annotations described.
    invoked = [e for e in events if isinstance(e, Invoked)]
    assert any(e.component == "look_up" for e in invoked), f"the server was never called: {invoked}"
    answers = [
        e.observation.output
        for e in events
        if isinstance(e, Observed) and isinstance(e.observation, Completed)
    ]
    assert any(
        isinstance(output, dict) and output.get("asset") == "LATHE-3" for output in answers
    ), "the lathe record never came back"

    # Everything left through the ports, and only through them.
    stamped = [(line["run_id"], line["seq"]) for line in written if "seq" in line]
    assert stamped == [(e.run_id, e.seq) for e in events]


async def test_the_mode_decided_what_the_agent_could_even_see() -> None:
    """The reference server publishes `wipe`, `append`, `mystery` and `explode` beside `look_up`.
    The `looking` mode's ceiling permits reading only, so the other four are **absent** from the
    catalogue rather than refused at call time — and a real model, given the chance, never had one
    to reach for. That is the open registry and effect-governance meeting on a live wire.
    """
    events, _ = await _run()
    called = {e.component for e in events if isinstance(e, Invoked)}
    assert "look_up" in called
    assert called & {"wipe", "mystery", "explode", "append"} == set()


async def test_a_proposal_left_through_the_sink() -> None:
    events, written = await _run()
    proposed = [e for e in events if isinstance(e, Proposed)]
    if not proposed:
        pytest.skip("the model finished without proposing; that is a model choice, not a defect")
    assert [line for line in written if "payload" in line], "a proposal never reached the sink"
