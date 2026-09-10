"""Run a bridge-client call **inside a real run**, because that is the only place it works.

`BridgeClient` looks up `current_run()` on every governable request: it needs the run's governance
port and the run's context. Constructing one by hand would test a fiction, so these helpers put the
call where it really happens — inside a component, inside a step, inside a run.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from shadow_hdk.adapters.basic import AllowAll
from pydantic import JsonValue

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    EffectProfile,
    Floor,
    Invoke,
    Lease,
    Observation,
    ScopeSet,
)
from shadow_hdk.kernel.ports import GovernancePort
from shadow_hdk.runtime import Ports, RunOptions, run
from shadow_hdk.runtime.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    ScriptedModel,
    make_registration,
)

EVERYTHING = ScopeSet(everything=True)
CALLER = make_registration("caller", effects=EffectProfile(reads=EVERYTHING))


async def inside_a_run[T](
    what: Callable[[], Awaitable[T]], *, governance: GovernancePort | None = None
) -> T:
    """Await `what()` inside a run governed by `governance`, and give back what it returned."""
    box: list[Any] = []

    async def call(_inputs: JsonValue) -> Observation:
        try:
            box.append(("ok", await what()))
        except BaseException as raised:  # noqa: BLE001 — the test wants the exception, not a crash
            box.append(("raised", raised))
        return Completed(None)

    ports = Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(CALLER, call)]),),
        governance=governance or AllowAll(),
        sink=ListSink(),
        clock=FixedClock(),
    )
    async for _event in run(
        Composition((Invoke("s1", CALLER.id),)),
        ports,
        options=RunOptions(lease=Lease(Ceiling(10, 600, 1000), Floor(0))),
    ):
        pass
    assert box, "the component never ran"
    outcome, value = box[0]
    if outcome == "raised":
        raise value
    return value  # type: ignore[no-any-return]
