"""Our registry, offered to a child — and recording as a consequence of routing.

Nothing here is a recording *feature*. The handler runs the call as a child run, and judgement, the
event stream, lease carving and provenance are what a run already does. The tests are therefore
about **routing**: that the child gets exactly what the parent could use, and that what it did
shows up on the parent's record because it went through the same door.
"""

from __future__ import annotations

import json

from mcp import types

from shadow_hdk.adapters.modes import Mode, ModeGovernance
from shadow_hdk.adapters.recording import RecordingServer
from shadow_hdk.kernel import EffectProfile, Invoked, Observed
from shadow_hdk.runtime import RunContext
from tests.adapters.recording.conftest import EVERYTHING, WORKSPACE, with_a_run

READING = Mode("reading", EffectProfile(reads=EVERYTHING, contained=False, costs=True))
WRITING = Mode(
    "writing",
    EffectProfile(
        reads=EVERYTHING, writes=WORKSPACE, reversible=False, contained=False, costs=True
    ),
)


def mode(one: Mode) -> ModeGovernance:
    return ModeGovernance({one.name: one}, default=one.name)


def text_of(result: types.CallToolResult) -> str:
    """What a child would read. Narrowed once here rather than ignored at every call site."""
    first = result.content[0]
    assert isinstance(first, types.TextContent)
    text: str = first.text
    return text


# ---------------------------------------------------------------- what the child is offered


async def test_the_child_is_offered_exactly_what_the_parent_can_use() -> None:
    """The same computation, not a parallel one: `RunContext.visible()` is the registry filtered by
    the governance port, and it is what the model sees too."""
    listed, _ = await with_a_run(lambda ctx: RecordingServer(ctx).tools())
    assert {tool.name for tool in listed} == {"look", "wipe", "breaks", "driver"}


async def test_a_narrowing_mode_narrows_the_child_with_nothing_in_between() -> None:
    """No wiring, no second policy. `wipe` writes irreversibly, so a reading mode removes it — from
    the child, because it removed it from the run."""
    listed, _ = await with_a_run(lambda ctx: RecordingServer(ctx).tools(), governance=mode(READING))
    names = {tool.name for tool in listed}
    assert "look" in names
    assert "wipe" not in names


async def test_the_schema_the_component_published_reaches_the_child_verbatim() -> None:
    """Verbatim, and asserted on something **distinctive**.

    A first version checked only `type == "object"`, which the fallback for a missing schema also
    produces — so replacing the schema wholesale left the test green. A named property is the thing
    that cannot be produced by accident.
    """
    listed, _ = await with_a_run(lambda ctx: RecordingServer(ctx).tools())
    look = next(tool for tool in listed if tool.name == "look")
    assert look.description == "Look a topic up."
    assert look.input_schema["required"] == ["topic"]
    properties = look.input_schema["properties"]
    assert isinstance(properties, dict)
    assert properties["topic"]["description"] == "what to look up"


async def test_a_call_on_an_exhausted_run_is_refused_before_it_is_attempted() -> None:
    """The guard in front of the routing. A run with nothing left cannot carve a child at all, so
    the honest answer is an error rather than an exception out of `spawn_options`."""

    async def spend_then_call(ctx: RunContext) -> types.CallToolResult:
        server = RecordingServer(ctx)
        for _ in range(4):
            await server.call_tool("look", {"topic": "x"})
        return await server.call_tool("look", {"topic": "x"})

    result, _ = await with_a_run(spend_then_call, steps=4)
    assert result.is_error
    assert "left" in text_of(result)


# ---------------------------------------------------------------- what happens when it calls


async def test_a_call_runs_the_component_and_comes_back() -> None:
    result, _ = await with_a_run(
        lambda ctx: RecordingServer(ctx).call_tool("look", {"topic": "lathe"})
    )
    assert not result.is_error
    assert json.loads(text_of(result))["found"] == {"topic": "lathe"}


async def test_what_the_child_did_is_on_the_parents_record() -> None:
    """The whole point. A host watching the parent sees the child's step, because the child's call
    *was* a step — routed through `run()` as a child of the parent."""
    _result, events = await with_a_run(
        lambda ctx: RecordingServer(ctx).call_tool("look", {"topic": "lathe"})
    )
    invoked = [e for e in events if isinstance(e, Invoked) and e.component == "look"]
    observed = [e for e in events if isinstance(e, Observed) and e.step != "s1"]
    assert invoked, "the child's call never reached the parent's stream"
    assert observed
    assert invoked[0].run_id != events[0].run_id, "it should be a child run, not the parent's"


async def test_a_refused_call_is_an_error_the_child_can_read() -> None:
    result, events = await with_a_run(
        lambda ctx: RecordingServer(ctx).call_tool("wipe", {}), governance=mode(READING)
    )
    assert result.is_error
    assert "reading" in text_of(result)
    assert not [e for e in events if isinstance(e, Invoked) and e.component == "wipe"], (
        "the component ran despite being refused"
    )


async def test_a_component_that_breaks_is_an_error_and_not_a_crash() -> None:
    result, _ = await with_a_run(lambda ctx: RecordingServer(ctx).call_tool("breaks", {}))
    assert result.is_error
    assert "unwell" in text_of(result)


async def test_a_tool_the_child_invented_is_an_error() -> None:
    result, _ = await with_a_run(lambda ctx: RecordingServer(ctx).call_tool("no_such_tool", {}))
    assert result.is_error


async def test_the_parents_lease_bounds_the_child() -> None:
    """A child that calls forever is stopped by the ceiling it was carved from — the same clock
    that bounds everything else, with nothing added for this case."""

    async def call_until_stopped(ctx: RunContext) -> int:
        server = RecordingServer(ctx)
        errors = 0
        for _ in range(40):
            result = await server.call_tool("look", {})
            if result.is_error:
                errors += 1
                if errors > 2:
                    break
        return errors

    errors, _events = await with_a_run(call_until_stopped, steps=6)
    assert errors > 0, "the child was never stopped"
