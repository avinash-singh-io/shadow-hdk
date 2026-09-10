"""The latency budget (D11), measured rather than hoped for.

The runtime's overhead per step is what a host pays for governance, events and bookkeeping — on top
of whatever the component itself does. A no-op component under allow-all isolates exactly that.

**D11's targets** are 100 ms for a hundred sequential steps, 50 ms for a fifty-way fan-out, and 1 ms
of overhead per step. Measured on the development machine, 2026-09-10: **57.0 ms (0.570 ms/step)**
and **27.2 ms** — inside all three. The assertions are set at three times those targets so a shared
runner does not flake, which means they catch a regression of an order of magnitude rather than a
drift of ten per cent. The printed numbers are the real signal; read them.

What the budget protects is the *design* behind D11: governance in-process, no per-step
serialisation, a cached plan, the observer off the critical path. Break one and this goes red.
"""

from __future__ import annotations

import time

from shadow_hdk.kernel import Ceiling, Composition, FanOut, Floor, Invoke, Lease, Sequence
from shadow_hdk.runtime import RunOptions, run
from shadow_hdk.runtime.testing import FixedClock, make_registration
from tests.runtime.conftest import ports_over

REG = make_registration("noop")
STEPS = 100
FAN = 50

D11_SEQUENTIAL_MS = 100.0
D11_FAN_OUT_MS = 50.0
D11_PER_STEP_MS = 1.0

CI_SLACK = 3.0
"""A shared runner is not the development machine. Three times the target, and no more."""


ROUNDS = 9
"""**Best of nine, not the average.**

A busy machine makes a run slower and never faster, so the minimum is the cleanest estimate of what
the code actually costs — and it is what stops this test failing for the wrong reason. It has
already done so twice. First at **308 ms** against a 300 ms ceiling during a run spawning MCP
subprocesses, while the same code alone measured 52.7, 56.2 and 60.7 ms. Then again at **309.9 ms**,
in a suite that by then spawned subprocesses of its own for the sandbox, the recording server and
the held-child tests — 56.9 ms when run alone a minute later.

Three was not enough, because the contention is now **inside the suite** rather than beside it:
tests that spawn processes run before this one, and three samples can all land while the machine is
still settling. Nine costs about half a second and gives the minimum a real chance at a quiet
moment. Averaging would have hidden the true number under the contention; a single run reports the
contention as if it were the number; and raising the slack instead would have bought quiet by making
the gate unable to fail. A flaky gate is worse than no gate, because it teaches you to ignore it.
"""


async def _once(composition: Composition, steps: int) -> tuple[float, int]:
    ports, _ = ports_over([(REG, "ok")], clock=FixedClock())
    options = RunOptions(lease=Lease(Ceiling(steps + 10, 10_000, None), Floor(0)))
    started = time.perf_counter()
    count = 0
    async for _event in run(composition, ports, options=options):
        count += 1
    return (time.perf_counter() - started) * 1000, count


async def _time(composition: Composition, steps: int) -> tuple[float, int]:
    results = [await _once(composition, steps) for _ in range(ROUNDS)]
    return min(elapsed for elapsed, _ in results), results[0][1]


async def test_a_hundred_sequential_steps() -> None:
    plan = Composition((Sequence("seq", tuple(Invoke(f"s{i}", REG.id) for i in range(STEPS))),))
    elapsed, events = await _time(plan, STEPS)
    print(
        f"\n  {STEPS} sequential steps: {elapsed:.1f} ms "
        f"({elapsed / STEPS:.3f} ms/step, best of {ROUNDS}), {events} events"
    )
    assert elapsed < D11_SEQUENTIAL_MS * CI_SLACK
    assert elapsed / STEPS < D11_PER_STEP_MS * CI_SLACK


async def test_a_fifty_way_fan_out() -> None:
    plan = Composition((FanOut("fan", tuple(Invoke(f"c{i}", REG.id) for i in range(FAN))),))
    elapsed, events = await _time(plan, FAN)
    print(f"\n  {FAN}-way fan-out: {elapsed:.1f} ms (best of {ROUNDS}), {events} events")
    assert elapsed < D11_FAN_OUT_MS * CI_SLACK


async def test_the_same_shape_is_not_re_planned() -> None:
    """The plan cache is one of D11's mechanisms, so it is measured rather than asserted."""
    from shadow_hdk.runtime.compile import plan_cache_stats

    plan = Composition((Sequence("seq", tuple(Invoke(f"s{i}", REG.id) for i in range(10))),))
    await _time(plan, 10)
    before = plan_cache_stats()
    await _time(plan, 10)
    after = plan_cache_stats()
    assert after["misses"] == before["misses"], "the same shape was planned twice"


NESTING = 10
"""Ten nested sequences of ten steps — the same hundred steps, arranged so every one of them runs
inside a subgraph."""


async def test_a_hundred_steps_arranged_as_nested_subgraphs() -> None:
    """What Phase 6's subgraphs cost, measured against the flat hundred above.

    A nested composite is now a compiled graph added as a node rather than more edges in one graph.
    That is a real cost — a graph per scope — and D11 says a cost is a number, not a shrug. Ten
    scopes is a plausible depth for a plan-and-execute pattern; a hundred would not be.
    """
    plan = Composition(
        (
            Sequence(
                "outer",
                tuple(
                    Sequence(
                        f"inner{group}",
                        tuple(Invoke(f"s{group}_{i}", REG.id) for i in range(NESTING)),
                    )
                    for group in range(NESTING)
                ),
            ),
        )
    )
    elapsed, events = await _time(plan, STEPS)
    print(
        f"\n  {STEPS} steps in {NESTING} nested subgraphs: {elapsed:.1f} ms "
        f"({elapsed / STEPS:.3f} ms/step, best of {ROUNDS}), {events} events"
    )
    assert elapsed < D11_SEQUENTIAL_MS * CI_SLACK
    assert elapsed / STEPS < D11_PER_STEP_MS * CI_SLACK
