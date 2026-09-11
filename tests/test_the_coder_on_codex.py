"""The coder on Codex: this run's tools through the registry relay, pre-permitted (live).

Skips where Codex is absent, signed out, or out of quota — the last measured as a `turn.failed`
whose text names the limit. Costs one turn on the owner's plan when it runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from examples.coder.session import NoProvider, a_conversation

from shadow_hdk.kernel import Event, Invoked

pytestmark = [pytest.mark.live, pytest.mark.anyio]


async def test_codex_writes_through_this_runs_tools(tmp_path: Path) -> None:
    (tmp_path / "names.txt").write_text("alpha\nbeta\n")
    seen: list[Event] = []
    try:
        async with a_conversation(tmp_path, want="codex", on_event=seen.append) as talk:
            done = await talk.turn(
                'Add "gamma" as a third line to names.txt using the tools you were given, '
                "not your own shell. Then stop."
            )
    except NoProvider as nothing:
        pytest.skip(str(nothing))
    if done.failed and "limit" in done.text.lower():
        pytest.skip(f"codex is out of quota: {done.text[:80]}")

    called = [e.component for e in seen if isinstance(e, Invoked) and e.step != "converse"]
    assert "write_file" in called, (called, done.text)
    assert (tmp_path / "names.txt").read_text().splitlines()[-1] == "gamma"
