"""The coder example, against a real provider and a real subscription.

Marked `live` and **deselected by default**, because it spends somebody's money and needs software
this repository does not ship. It skips rather than fails where no provider is ready, which is the
same rule every other live test here follows.

Run it deliberately:

    uv run pytest -m live tests/test_the_coder_example.py -q

What it asserts is the claim the example exists to make, and nothing softer: the provider reasoned,
**our** components acted, and both actions are on the run's own record. A version of this that only
checked the agent's prose would pass against an agent that did the work with its own tools.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from examples.coder.thread import a_thread

from shadow_hdk.kernel import Event, Invoked, Observed
from shadow_hdk.providers import NoProvider, ready

pytestmark = [
    pytest.mark.live,
    # The suite's default deadline is 60s and exists so a hung subprocess cannot wedge CI. A live
    # turn is a conversation with a model: it thinks, calls a tool, reads the answer, and after a
    # refusal it tries something else before giving up. Minutes, not seconds, and the deadline is
    # still a deadline.
    pytest.mark.timeout(600),
]


async def test_it_writes_a_file_and_runs_it_through_our_tools(tmp_path: Path) -> None:
    seen: list[Event] = []
    try:
        async with a_thread(tmp_path) as thread:
            async for event in thread.turn(
                "Write hello.py that prints exactly: hi\n"
                "Then run it and tell me what it printed. Use only the tools you have."
            ):
                seen.append(event)
            done = thread.record.turns[-1]
    except NoProvider as nothing:
        pytest.skip(str(nothing))

    used = [e.component for e in seen if isinstance(e, Invoked) and e.component != "turn"]
    assert "write_file" in used, f"it did not go through our workspace: {used}"
    assert any(t in used for t in ("run_shell", "run_python")), (
        f"it did not use our sandbox: {used}"
    )

    assert (tmp_path / "hello.py").exists(), "our workspace component never wrote the file"

    ran = [
        e
        for e in seen
        if isinstance(e, Observed) and e.step.endswith(("run_shell__2", "run_python__2"))
    ]
    assert ran, "the sandbox's answer never reached the parent's stream"

    assert done.outcome == "completed", done.text
    assert "hi" in done.text


async def test_the_provider_is_told_what_this_machine_can_do_before_anything_starts() -> None:
    """Detection is not a formality: a run opened against a signed-out provider spends a turn to
    discover what a probe would have said for nothing."""
    try:
        available = await ready()
    except NoProvider as nothing:
        pytest.skip(str(nothing))

    assert available.status == "ready"
    assert available.binary is not None
    assert available.provider.injects_tools, "a provider we cannot hand tools to cannot be governed"
