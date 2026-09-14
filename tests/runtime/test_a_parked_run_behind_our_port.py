"""A parked run behind a port of ours (Phase 30 group 5, D93).

The `Store` and the `ThreadStore` are the kernel's ports; where a parked run slept was the
runtime library's contract, `BaseCheckpointSaver`, typed `Any` through the kit — a product not on
SQLite or Postgres had to bring a LangGraph saver. `RunStore` is the port: bytes by run id and
key, four methods; `saver_over(run_store)` is LangGraph's checkpointer over it, so the runtime
parks and resumes exactly as it does on the shipped savers, and the state lives in the store —
two savers over one store finish each other's runs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from shadow_hdk.kernel import (
    Ceiling,
    Completed,
    Composition,
    Ended,
    Floor,
    Invoke,
    Lease,
    Observed,
    RunStore,
)
from shadow_hdk.kernel.ports import Allow, Ask, Context, Judgement
from shadow_hdk.runtime import Ports, RunOptions, resume, run
from shadow_hdk.runtime.checkpoints import InMemoryRunStore, saver_over
from shadow_hdk.testing import (
    FixedClock,
    InMemoryComponents,
    ListSink,
    RunStoreContract,
    ScriptedModel,
    make_registration,
)

pytestmark = pytest.mark.anyio

WORK = make_registration("work")
THREE = Composition(tuple(Invoke(f"s{i}", WORK.id) for i in range(1, 4)))


class AsksAtSecond:
    async def judge(self, _effects: Any, context: Context) -> Judgement:
        return Ask("may it?") if context.step == "s2" else Allow()


class Ran:
    def __init__(self) -> None:
        self.count = 0

    async def __call__(self, _inputs: Any) -> Any:
        self.count += 1
        return Completed(self.count)


def _ports(ran: Ran) -> Ports:
    return Ports(
        model=ScriptedModel(),
        components=(InMemoryComponents([(WORK, ran)]),),
        governance=AsksAtSecond(),
        sink=ListSink(),
        clock=FixedClock(),
    )


def test_the_port_is_the_kernels() -> None:
    assert isinstance(InMemoryRunStore(), RunStore)


class TestInMemoryRunStoreHoldsTheContract(RunStoreContract):
    def run_store(self) -> InMemoryRunStore:
        return InMemoryRunStore()


async def test_a_run_parked_through_one_saver_finishes_through_another_over_the_same_store() -> (
    None
):
    store = InMemoryRunStore()
    ran = Ran()
    options = RunOptions(lease=Lease(Ceiling(10, 60, None), Floor(0)), run_id="behind-our-port")
    parked = [
        e
        async for e in run(
            THREE,
            _ports(ran),
            options=RunOptions(**{**options.__dict__, "checkpointer": saver_over(store)}),
        )
    ]
    assert [e for e in parked if e.kind == "approval_requested"], "the run did not park"
    assert not [e for e in parked if isinstance(e, Ended)]
    assert ran.count == 1
    assert await store.list("behind-our-port"), "the state is in the store, not the saver"

    finished = [
        e
        async for e in resume(
            THREE,
            Allow(),
            _ports(ran),
            options=RunOptions(**{**options.__dict__, "checkpointer": saver_over(store)}),
        )
    ]
    done = [e for e in finished if isinstance(e, Observed) and e.step == "s3"]
    assert done and done[0].observation == Completed(3), finished
    assert "s1" not in [e.step for e in finished if e.kind == "invoked"], "redone, not resumed"
    assert [e for e in finished if isinstance(e, Ended)][-1].reason == "completed"
    assert ran.count == 3


async def test_two_runs_on_one_store_do_not_cross() -> None:
    store = InMemoryRunStore()
    ran = Ran()
    for run_id in ("one", "two"):
        [
            e
            async for e in run(
                THREE,
                _ports(ran),
                options=RunOptions(
                    lease=Lease(Ceiling(10, 60, None), Floor(0)),
                    run_id=run_id,
                    checkpointer=saver_over(store),
                ),
            )
        ]
    finished = [
        e
        async for e in resume(
            THREE,
            Allow(),
            _ports(ran),
            options=RunOptions(
                lease=Lease(Ceiling(10, 60, None), Floor(0)),
                run_id="one",
                checkpointer=saver_over(store),
            ),
        )
    ]
    assert [e for e in finished if isinstance(e, Ended)][-1].reason == "completed"
    assert await store.list("two"), "the other run is still asleep"
    await store.delete("one")
    assert await store.list("one") == ()


async def test_a_host_hands_its_run_store_in_and_a_thread_parks_on_it(tmp_path: Path) -> None:
    from shadow_hdk.serve import ServeHost, Settings

    store = InMemoryRunStore()
    host = ServeHost(Settings(root=tmp_path), run_store=store)
    try:
        saver = await host.checkpointer()
        assert type(saver).__name__ == "SaverOverRunStore"
    finally:
        await host.aclose()
