"""What a mode forbids, a child is not even offered — and is refused if it asks anyway.

The coder example's second demonstration, and it needs **no model at all**: the claim is about the
registry a child is handed, which is decided before anybody reasons about anything. Written as a
live test first, which was a mistake — it spent minutes of somebody's subscription to observe a
fact that is settled by governance and a `visible()` call.

Two layers, and both matter:

**It is not offered.** `RecordingServer` builds its tool list from `RunContext.visible()`, which is
governed. Under a mode that permits no shell, `run_shell` and `run_python` are absent from the list
the child receives — so a well-behaved agent never tries, and never burns a turn discovering it
cannot.

**It is refused if called anyway.** A list is a courtesy; the judgement is the control. A child that
remembered a tool name from an earlier turn, or guessed one, gets `refused: mode 'confined' does not
permit this` — naming the **mode**, because the policy judged a set of effects and has never heard
of `run_shell`.

Since BUG-018 this is a real boundary rather than a nominal one: the sandbox stopped claiming
`{workspace}` while being able to reach the whole machine, so a mode permitting workspace writes
genuinely excludes running code.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from examples.coder.workshop import BUILDING, CONFINED, LOOKING, a_lease, workshop
from shadow_hdk.adapters.recording import RecordingServer

from shadow_hdk.kernel import Completed, Composition, EffectProfile, Invoke, Observation
from shadow_hdk.runtime import RunOptions, current_run, run
from shadow_hdk.runtime.testing import InMemoryComponents, make_registration

WATCHING = make_registration(
    "watching",
    effects=EffectProfile(),
    description="Look at the registry a child would be handed, and nothing else.",
)
"""A driver that does nothing, on purpose.

The example's real driver holds a conversation, so it declares writes and reaching out — and a mode
that forbids those refuses **it** before the registry is consulted. That is correct enforcement,
and it made the first version of this file test the driver's profile rather than the registry's
contents. A driver with no effects is permitted by every mode here, which leaves each test's
subject the thing it is named after.
"""


async def offered_and_asked(root: Path, mode: Any) -> dict[str, Any]:
    """What a child would be handed under `mode`, and what happens if it calls the shell anyway."""
    found: dict[str, Any] = {}

    async def drive(_inputs: Any) -> Observation:
        context = current_run()
        assert context is not None
        server = RecordingServer(context, withhold={"watching"})
        found["offered"] = sorted(tool.name for tool in await server.tools())
        found["wrote"] = await server.call("write_file", {"path": "a.txt", "content": "hi"})
        found["ran"] = await server.call("run_shell", {"command": "ls"})
        return Completed(None)

    ports = workshop(root, mode=mode)
    ports = replace(ports, components=(*ports.components, InMemoryComponents([(WATCHING, drive)])))
    plan = Composition((Invoke("watching", "watching"),))
    async for _ in run(plan, ports, options=RunOptions(lease=a_lease())):
        pass
    return found


async def test_a_confined_mode_does_not_offer_the_shell(tmp_path: Path) -> None:
    """A well-behaved agent never tries, because it was never told the tool exists."""
    seen = await offered_and_asked(tmp_path, CONFINED)

    assert "write_file" in seen["offered"]
    assert "run_shell" not in seen["offered"], seen["offered"]
    assert "run_python" not in seen["offered"], seen["offered"]


async def test_it_is_refused_even_if_the_child_asks_anyway(tmp_path: Path) -> None:
    """The list is a courtesy; the judgement is the control."""
    seen = await offered_and_asked(tmp_path, CONFINED)

    assert seen["wrote"].is_error is False, "a confined mode should still permit the workspace"
    assert seen["ran"].is_error is True
    assert "confined" in str(seen["ran"].content), seen["ran"].content


async def test_the_refusal_names_the_mode_and_not_the_tool(tmp_path: Path) -> None:
    """The policy judged a set of effects. It has never heard of `run_shell`, which is why it would
    refuse a tool nobody has written yet on exactly the same grounds."""
    seen = await offered_and_asked(tmp_path, CONFINED)

    said = str(seen["ran"].content)
    assert "run_shell" not in said, f"the refusal is about the effects, not the name: {said}"


async def test_the_building_mode_does_offer_it(tmp_path: Path) -> None:
    """The anti-vacuity half: a registry that offered nothing under every mode would pass the three
    tests above and mean nothing."""
    seen = await offered_and_asked(tmp_path, BUILDING)

    assert "run_shell" in seen["offered"]
    assert seen["ran"].is_error is False


async def test_a_looking_mode_offers_no_writing_at_all(tmp_path: Path) -> None:
    """The third rung, and the one that shows the ordering is real rather than two special cases."""
    seen = await offered_and_asked(tmp_path, LOOKING)

    assert "read_file" in seen["offered"]
    assert "write_file" not in seen["offered"], seen["offered"]
    assert seen["wrote"].is_error is True
