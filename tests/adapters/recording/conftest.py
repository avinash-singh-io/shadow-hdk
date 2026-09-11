"""Drive a RecordingServer inside a real run, and keep the parent's events.

The point of the server is that a child's call lands on the **parent's** record, so a helper that
threw the parent's events away would test everything except the thing that matters.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from shadow_hdk.adapters.basic import AllowAll
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Event,
    Floor,
    Invoke,
    Lease,
    Observation,
    Registration,
    ScopeSet,
)
from shadow_hdk.kernel.ports import GovernancePort
from shadow_hdk.runtime import Ports, RunContext, RunOptions, current_run, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)

EVERYTHING = ScopeSet(everything=True)
WORKSPACE = ScopeSet.of("workspace")

LOOK = make_registration(
    "look",
    effects=EffectProfile(reads=WORKSPACE),
    description="Look a topic up.",
    input_schema={
        "type": "object",
        "properties": {"topic": {"type": "string", "description": "what to look up"}},
        "required": ["topic"],
    },
)
WIPE = make_registration("wipe", effects=EffectProfile(writes=WORKSPACE, reversible=False))
BREAKS = make_registration("breaks", effects=EffectProfile(reads=WORKSPACE))
DRIVER = make_registration("driver", effects=EffectProfile(reads=EVERYTHING))


async def _look(inputs: JsonValue) -> Observation:
    return Completed({"found": inputs})


async def _wipe(_inputs: JsonValue) -> Observation:
    return Completed({"wiped": True})


async def _breaks(_inputs: JsonValue) -> Observation:
    raise RuntimeError("the component is unwell")


def tools() -> InMemoryComponents:
    return InMemoryComponents([(LOOK, _look), (WIPE, _wipe), (BREAKS, _breaks)])


async def with_a_run[T](
    what: Callable[[RunContext], Awaitable[T]],
    *,
    governance: GovernancePort | None = None,
    extra: Sequence[Registration] = (),
    steps: int = 20,
    questions: Any = None,
    wall_seconds: int = 600,
) -> tuple[T, list[Event]]:
    """Run `what` inside a step, giving back its answer **and the parent's event stream**."""
    box: list[Any] = []

    async def call(_inputs: JsonValue) -> Observation:
        context = current_run()
        assert context is not None
        try:
            box.append(("ok", await what(context)))
        except BaseException as raised:  # noqa: BLE001 — the test wants it, not a crash
            box.append(("raised", raised))
        return Completed(None)

    ports = Ports(
        model=ScriptedModel(),
        components=(tools(), InMemoryComponents([(DRIVER, call)])),
        governance=governance or AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    events = [
        e
        async for e in run(
            Composition((Invoke("s1", DRIVER.id),)),
            ports,
            options=RunOptions(
                lease=Lease(Ceiling(steps, wall_seconds, 10_000), Floor(0)), questions=questions
            ),
        )
    ]
    assert box, "the driver never ran"
    outcome, value = box[0]
    if outcome == "raised":
        raise value
    return value, events
