"""What crosses a boundary is JSON, and what a step cost is an event (D19, D20).

**D19.** A checkpoint *is* a wire. It crosses a process, it crosses a version, and it crosses into a
store the host chose and we know nothing about. So `RunState` carries JSON and the runtime loads
observations back at its own edge — rather than asking every host to name
`shadow_hdk.kernel.observations` in its serializer's allowlist, which would make our module
names part of somebody else's deployment.

**D20.** Phase 1 asked that tokens reach the observer. They did not: `_usage_of` dug them out of a
`Completed` observation's output dict by convention, so anyone wanting to know what a run cost had
to parse somebody else's payload. `Spent` says it.
"""

from __future__ import annotations

import json

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
    Observed,
    Spent,
)
from shadow_hdk.runtime import RunOptions, run
from shadow_hdk.runtime.testing import ListObserver, make_registration
from tests.runtime.conftest import ports_over

FREE = make_registration("free", effects=EffectProfile())
COSTLY = make_registration("costly", effects=EffectProfile(costs=True))


async def _costs(_inputs: JsonValue) -> Observation:
    """What a model adapter reports — the convention stays; the record stops depending on it."""
    return Completed(
        {"text": "hello", "usage": {"input_tokens": 11, "output_tokens": 3, "cost_cents": 2}}
    )


def a_lease(steps: int = 20) -> Lease:
    return Lease(Ceiling(steps, 3600, 10_000), Floor(0))


# ---------------------------------------------------------------- D19


def test_what_a_step_writes_into_the_graph_state_is_json() -> None:
    """The decision, at the one place it lives. `json.dumps` is the whole assertion: it raises on
    anything that is not a plain type, which is exactly what a checkpointer will do."""
    from shadow_hdk.runtime.compile import _step_node

    written: dict[str, object] = {}

    class _Executor:
        async def invoke(self, _step: object, _state: object) -> Observation:
            return Completed({"found": "a lathe"})

    import anyio

    node = _step_node(Invoke("s1", FREE.id), _Executor())  # type: ignore[arg-type]
    written = anyio.run(node, {"handles": {}, "observations": {}, "iterations": {}})  # type: ignore[arg-type]
    json.dumps(written)  # raises if anything in here is one of our classes
    assert written["observations"] == {"s1": {"output": {"found": "a lathe"}, "kind": "completed"}}


async def test_a_whole_run_leaves_a_checkpoint_of_plain_types() -> None:
    """End to end: what the host's checkpointer is actually handed."""
    from langgraph.checkpoint.memory import InMemorySaver

    saver = InMemorySaver()
    ports, _ = ports_over([(FREE, "ok")])
    async for _ in run(
        Composition((Invoke("s1", FREE.id),)),
        ports,
        options=RunOptions(lease=a_lease(), run_id="crossing", checkpointer=saver),
    ):
        pass

    tuples = [t async for t in saver.alist({"configurable": {"thread_id": "crossing"}})]
    assert tuples, "the run left no checkpoint"
    for checkpoint in tuples:
        json.dumps(checkpoint.checkpoint["channel_values"].get("observations", {}))


async def test_an_observation_still_arrives_as_an_observation_on_the_stream() -> None:
    """The types stay ours. Only what *crosses* is plain — a host reading the event stream still
    gets a `Completed`, not a dict it has to interpret."""
    ports, _ = ports_over([(FREE, "ok")])
    events = [
        e
        async for e in run(
            Composition((Invoke("s1", FREE.id),)), ports, options=RunOptions(lease=a_lease())
        )
    ]
    observed = [e for e in events if isinstance(e, Observed)]
    assert observed and observed[-1].observation == Completed("ok")


# ---------------------------------------------------------------- D20


async def test_spent_reaches_the_observer_with_what_the_step_cost() -> None:
    watching = ListObserver()
    ports, _ = ports_over([(COSTLY, _costs)], observer=watching)
    async for _ in run(
        Composition((Invoke("s1", COSTLY.id),)), ports, options=RunOptions(lease=a_lease())
    ):
        pass
    spent = [e for e in watching.events if isinstance(e, Spent)]
    assert len(spent) == 1, "the observer was told nothing about what the step cost"
    assert spent[0].step == "s1"
    assert spent[0].usage.input_tokens == 11
    assert spent[0].usage.output_tokens == 3
    assert spent[0].usage.cost_cents == 2


async def test_a_step_that_cost_nothing_says_nothing() -> None:
    """A kind that appears when there is nothing to say is a kind readers learn to skip."""
    watching = ListObserver()
    ports, _ = ports_over([(FREE, "ok")], observer=watching)
    async for _ in run(
        Composition((Invoke("s1", FREE.id),)), ports, options=RunOptions(lease=a_lease())
    ):
        pass
    assert not [e for e in watching.events if isinstance(e, Spent)]
