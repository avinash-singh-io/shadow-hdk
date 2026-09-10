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


ROUNDS = 3
"""**Best of three, not the average.**

A busy machine makes a run slower and never faster, so the minimum is the cleanest estimate of what
the code actually costs — and it is what stops this test failing for the wrong reason. It has
already done so once: during a run that was spawning MCP subprocesses, one hundred steps measured
**308 ms** against a 300 ms ceiling, while the same code alone measured 52.7, 56.2 and 60.7 ms.
Averaging would have hidden the real number under the contention; a single run reported the
contention as if it were the number. A flaky gate is worse than no gate, because it teaches you to
ignore it.
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
