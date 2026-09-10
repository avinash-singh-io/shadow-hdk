"""A parked run survives the process that parked it.

Everything before this was proven against `InMemorySaver`, which is not durability — it is a dict
that happens to satisfy the interface. `RunOptions.checkpointer` has been a parameter since Phase 0
and nothing had ever handed it a checkpointer we do not ship. These two tests do: one parks inside a
**nested composite** and resumes into it, and one parks with a **file** and resumes after the saver
object is gone.

`langgraph-checkpoint-sqlite` is a dev dependency for exactly this. We ship no checkpointer; the
host brings one, and this is where we find out whether that claim was true.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from shadow_hdk.kernel import (
    Allow,
    Ask,
    Ceiling,
    Completed,
    Composition,
    Ended,
    Event,
    Floor,
    Invoke,
    Lease,
    Observed,
    Sequence,
)
from shadow_hdk.runtime import Ports, RunOptions, resume, run
from shadow_hdk.runtime.testing import Judge, make_registration
from tests.runtime.conftest import ports_over

A = make_registration("a")
B = make_registration("b")

PARKS_INSIDE = Composition(
    (
        Invoke("first", A.id),
        Sequence("inner", (Invoke("deep", B.id),)),
    )
)


def a_lease(steps: int = 20) -> Lease:
    return Lease(Ceiling(steps, 3600, 1000), Floor(0))


def _asks_about(step: str) -> Judge:
    return Judge(lambda _e, context: Ask("may it?") if context.step == step else Allow())


def _ports() -> Ports:
    ports, _ = ports_over([(A, "one"), (B, "two")], judge=_asks_about("deep"))
    return ports


async def _collect(events: Any) -> list[Event]:
    return [e async for e in events]


async def test_a_run_parked_inside_a_subgraph_resumes_into_it() -> None:
    """The interrupt was raised in a nested scope, so the resume has to land back in that scope —
    which is what the subgraph's checkpoint namespace is for."""
    from langgraph.checkpoint.memory import InMemorySaver

    saver = InMemorySaver()
    options = RunOptions(lease=a_lease(), run_id="parked-inside", checkpointer=saver)

    parked = await _collect(run(PARKS_INSIDE, _ports(), options=options))
    assert [e.kind for e in parked if e.kind == "asked"], "the nested Ask never reached the top"
    assert not [e for e in parked if isinstance(e, Ended)], "a parked run must not report Ended"

    after = await _collect(resume(PARKS_INSIDE, Allow(), _ports(), options=options))
    done = [e for e in after if isinstance(e, Observed) and e.step == "deep"]
    assert done, "the resume never reached the step inside the subgraph"
    assert done[0].observation == Completed("two")
    # Resumed, not restarted: the step before the park is not run a second time.
    assert "first" not in [e.step for e in after if e.kind == "invoked"]
    assert [e for e in after if isinstance(e, Ended)][-1].reason == "completed"


async def test_a_run_parked_on_a_file_resumes_after_the_saver_is_gone(tmp_path: Path) -> None:
    """Durability, not memory. The saver that parked the run is closed and dropped; a *new* one
    over the same file finishes it. Nothing of the run is held by the runtime between the two —
    `09` §6: the runtime owns nothing durable, which is why the composition is passed back in.
    """
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    database = tmp_path / "runs.sqlite"

    async with AsyncSqliteSaver.from_conn_string(str(database)) as saver:
        parked = await _collect(
            run(
                PARKS_INSIDE,
                _ports(),
                options=RunOptions(lease=a_lease(), run_id="on-a-file", checkpointer=saver),
            )
        )
    assert [e.kind for e in parked if e.kind == "asked"], "the run did not park"
    assert database.exists() and database.stat().st_size > 0, "nothing was written to the file"

    # A different saver object, over the same file. The first one is closed and unreachable.
    async with AsyncSqliteSaver.from_conn_string(str(database)) as reopened:
        after = await _collect(
            resume(
                PARKS_INSIDE,
                Allow(),
                _ports(),
                options=RunOptions(lease=a_lease(), run_id="on-a-file", checkpointer=reopened),
            )
        )
    done = [e for e in after if isinstance(e, Observed) and e.step == "deep"]
    assert done, "a run parked on disk could not be resumed from it"
    assert done[0].observation == Completed("two")
    # The proof that the file carried the state: the step before the park is not run again, so the
    # work it did came back off disk rather than being redone.
    assert "first" not in [e.step for e in after if e.kind == "invoked"]
    assert [e for e in after if isinstance(e, Ended)][-1].reason == "completed"


async def test_two_runs_sharing_a_checkpointer_resume_into_their_own_park() -> None:
    """The thread is the run id, which is what makes one host checkpointer usable for every run at
    once. Two runs are parked on the same saver, at *different* steps, and then the first is
    resumed: it must wake where it slept, not where the other one did.

    Two identical compositions could not tell: a fresh input overwrites a thread, so a second run
    starting from the beginning proves nothing about isolation. The parks have to differ.
    """
    from langgraph.checkpoint.memory import InMemorySaver

    shared = InMemorySaver()
    ports, _ = ports_over(
        [(A, "one"), (B, "two")],
        judge=Judge(
            lambda _e, context: Ask("may it?") if context.step.endswith("deep") else Allow()
        ),
    )

    async def park(composition: Composition, run_id: str) -> list[Event]:
        return await _collect(
            run(
                composition,
                ports,
                options=RunOptions(lease=a_lease(), run_id=run_id, checkpointer=shared),
            )
        )

    mine = Composition(
        (Invoke("mine_first", A.id), Sequence("mine_inner", (Invoke("mine_deep", B.id),)))
    )
    theirs = Composition(
        (Invoke("their_first", A.id), Sequence("their_inner", (Invoke("their_deep", B.id),)))
    )

    assert [e for e in await park(mine, "run-a") if e.kind == "asked"], "run-a did not park"
    assert [e for e in await park(theirs, "run-b") if e.kind == "asked"], "run-b did not park"

    woken = await _collect(
        resume(
            mine,
            Allow(),
            ports,
            options=RunOptions(lease=a_lease(), run_id="run-a", checkpointer=shared),
        )
    )
    done = [e for e in woken if isinstance(e, Observed)]
    assert [e.step for e in done] == ["mine_deep"], (
        "run-a woke up somewhere other than where it slept"
    )
    assert [e for e in woken if isinstance(e, Ended)][-1].reason == "completed"
