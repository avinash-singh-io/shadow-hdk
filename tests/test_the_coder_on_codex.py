"""The coder on Codex: this run's tools through the registry relay, pre-permitted (live).

Skips where Codex is absent, signed out, or out of quota — the last measured as a `turn.failed`
whose text names the limit. Costs one turn on the owner's plan when it runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.kernel import Event, Invoked
from shadow_hdk.providers import NoProvider
from shadow_hdk.serve import a_thread

pytestmark = [pytest.mark.live, pytest.mark.anyio]


async def test_codex_writes_through_this_runs_tools(tmp_path: Path) -> None:
    (tmp_path / "names.txt").write_text("alpha\nbeta\n")
    seen: list[Event] = []
    try:
        async with a_thread(tmp_path, want="codex") as thread:
            async for event in thread.turn(
                'Add "gamma" as a third line to names.txt using the tools you were given, '
                "not your own shell. Then stop."
            ):
                seen.append(event)
            done = thread.record.turns[-1]
    except NoProvider as nothing:
        pytest.skip(str(nothing))
    if done.outcome != "completed" and "limit" in done.text.lower():
        pytest.skip(f"codex is out of quota: {done.text[:80]}")

    called = [e.component for e in seen if isinstance(e, Invoked) and e.component != "turn"]
    assert "write_file" in called, (called, done.text)
    assert (tmp_path / "names.txt").read_text().splitlines()[-1] == "gamma"
