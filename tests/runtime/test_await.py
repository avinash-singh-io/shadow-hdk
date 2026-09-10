"""An `Await` that is told to wait, waits.

`specs/architecture/runtime.md` has said since Phase 0 that `Await` compiles to *one node whose
observation may be `Pending`; the parked form is `interrupt()`*. It did not. The compiler treated it
exactly like `Invoke`, so a component returning `Pending` had its observation recorded and the run
carried straight on to `Ended` — and `Pending` appeared in the suite only inside a round-trip
contract test, serialised and deserialised and never once making a run wait.

The distinction this restores is the one the grammar is for: `Invoke` is *do it now*, `Await` is
*this may take a while*. A `Pending` from an `Invoke` is still just an observation.
"""

from __future__ import annotations

from pydantic import JsonValue

from shadow_hdk.kernel import (
    Await,
    Ceiling,
    Completed,
    Composition,
    Ended,
    Event,
    Floor,
    Invoke,
    Lease,
    Observation,
    Observed,
    Pending,
)
from shadow_hdk.runtime import Ports, RunOptions, resume, run
from shadow_hdk.runtime.testing import make_registration
from tests.runtime.conftest import ports_over

SLOW = make_registration("slow")


async def _pends(_inputs: JsonValue) -> Observation:
    return Pending("job-17")


def a_lease(steps: int = 20) -> Lease:
    return Lease(Ceiling(steps, 3600, 1000), Floor(0))


def _ports() -> Ports:
    ports, _ = ports_over([(SLOW, _pends)])
    return ports


WAITING = Composition((Await("w1", SLOW.id),))


async def test_an_await_told_to_wait_parks_the_run() -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    options = RunOptions(lease=a_lease(), run_id="waiting", checkpointer=InMemorySaver())
    events = [e async for e in run(WAITING, _ports(), options=options)]
    assert not [e for e in events if isinstance(e, Ended)], "a parked run must not report Ended"
    waiting = [e for e in events if isinstance(e, Observed) and e.step == "w1"]
    assert [e.observation for e in waiting] == [Pending("job-17")]


async def test_a_resume_delivers_the_answer_as_the_steps_observation() -> None:
    from langgraph.checkpoint.memory import InMemorySaver

    options = RunOptions(lease=a_lease(), run_id="waiting", checkpointer=InMemorySaver())
    parked = [e async for e in run(WAITING, _ports(), options=options)]
    assert not [e for e in parked if isinstance(e, Ended)]

    after: list[Event] = [
        e async for e in resume(WAITING, {"result": "the job finished"}, _ports(), options=options)
    ]
    observed = [e for e in after if isinstance(e, Observed) and e.step == "w1"]
    assert observed, "the resume never observed the awaited step"
    # Exactly one, and it is the answer. LangGraph re-runs the node on resume, so recording above
    # `interrupt()` rather than on the raising path would put the wait in the record twice — which
    # is the mistake `_ask` made once already, and the reason the contract is raise-to-park.
    assert [e.observation for e in observed] == [Completed({"result": "the job finished"})]
    assert [e for e in after if isinstance(e, Ended)][-1].reason == "completed"


async def test_an_invoke_that_returns_pending_does_not_park() -> None:
    """`Invoke` is *do it now*. A component that answers "later" there has answered — oddly, but it
    has answered, and the composition did not say it was willing to wait."""
    events = [
        e
        async for e in run(
            Composition((Invoke("s1", SLOW.id),)), _ports(), options=RunOptions(lease=a_lease())
        )
    ]
    ended = [e for e in events if isinstance(e, Ended)]
    assert ended and ended[-1].reason == "completed", "an Invoke parked when it should not have"
    observed = [e for e in events if isinstance(e, Observed) and e.step == "s1"]
    assert observed[-1].observation == Pending("job-17")
