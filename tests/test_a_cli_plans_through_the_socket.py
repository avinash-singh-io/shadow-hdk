"""Phase 36 G3, measured: a resident CLI proposes a plan through the registry socket and it is
admitted like the loop's (D110). One live turn on whichever CLI is signed in here — it costs the
owner's subscription, so it is opt-in with `uv run pytest -m live`, and it skips rather than
fails where no provider is ready.

What is asserted is the runtime, never the model's cleverness: that `compose` was offered, that
the record carries a `plan_admitted` (or, if the model planned wider than the limit, a
`plan_refused` naming the axis), and that the turn ended. A model that does not plan is a model
problem and skips the plan assertions with a reason rather than failing for the wrong one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shadow_hdk.kernel import Event, Invoked, PlanLimits
from shadow_hdk.kernel.events import PlanAdmitted, PlanRefused
from shadow_hdk.providers import NoProvider
from shadow_hdk.runtime.planning import COMPOSE
from shadow_hdk.serve import a_thread

pytestmark = [pytest.mark.live, pytest.mark.timeout(600)]


async def test_the_cli_is_offered_compose_and_its_plan_is_admitted(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("alpha\n")
    (tmp_path / "b.txt").write_text("beta\n")
    seen: list[Event] = []
    try:
        async with a_thread(tmp_path, mode="read-only") as thread:
            offered = [o.registration.id for o in await thread.tools()]
            assert COMPOSE in offered, f"compose is not offered to the CLI: {offered}"
            async for event in thread.turn(
                "Use the `compose` tool exactly once to read a.txt and b.txt in parallel with "
                "the read_file tool — a fan_out of two invoke steps — then tell me both contents. "
                "Use only the tools you have."
            ):
                seen.append(event)
            done = thread.record.turns[-1]
    except NoProvider as nothing:
        pytest.skip(str(nothing))

    used = [e.component for e in seen if isinstance(e, Invoked)]
    if COMPOSE not in used:
        pytest.skip(f"the model did not plan this time; it used {used}")
    admitted = [e for e in seen if isinstance(e, PlanAdmitted)]
    refused = [e for e in seen if isinstance(e, PlanRefused)]
    assert admitted or refused, "a plan through the socket left no admission on the record"
    if admitted:
        assert admitted[-1].limits == PlanLimits() or admitted[-1].limits is not None
        assert "read_file" in used, "the admitted plan's steps ran through our tools"
    assert done.outcome in ("completed", "parked"), done.text
