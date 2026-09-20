"""The meter counts what the cache did across a thread's turns, and the record carries it (D141).

`Spent.cache_read_tokens` / `cache_write_tokens` sum every call's report; a call that reported no
tokens at all makes the counts a floor (`unmetered`), as it does for input and output. A record or
a checkpoint written before these fields existed restores with zeros — the count is a floor there
too, and nothing older than the field is refused.
"""

from __future__ import annotations

from pathlib import Path

from shadow_hdk.kernel import Spent, Usage
from shadow_hdk.kernel.leases import Ceiling, Floor, Lease
from shadow_hdk.runtime.conversation import spent_of
from shadow_hdk.runtime.session import LeaseMeter
from shadow_hdk.runtime.testing import FixedClock


def a_meter() -> LeaseMeter:
    return LeaseMeter(Lease(Ceiling(100, 100, 1000), Floor(0)), FixedClock())


def test_cache_tokens_are_counted_across_calls() -> None:
    meter = a_meter()
    meter.count_tokens(Usage(input_tokens=10, output_tokens=4, cache_read_tokens=8))
    meter.count_tokens(
        Usage(input_tokens=5, output_tokens=1, cache_read_tokens=3, cache_write_tokens=7)
    )

    spent = spent_of(meter)

    assert spent.input_tokens == 15 and spent.output_tokens == 5
    assert spent.cache_read_tokens == 11
    assert spent.cache_write_tokens == 7
    assert spent.unmetered is False


def test_a_call_with_no_cache_report_counts_nothing_and_claims_nothing() -> None:
    meter = a_meter()
    meter.count_tokens(Usage(input_tokens=10, output_tokens=4))

    spent = spent_of(meter)

    assert spent.cache_read_tokens == 0 and spent.cache_write_tokens == 0
    assert spent.unmetered is False, "input and output were reported; only the cache was silent"


def test_the_checkpoint_carries_and_restores_them() -> None:
    meter = a_meter()
    meter.count_tokens(Usage(input_tokens=1, output_tokens=1, cache_read_tokens=9))
    carried = meter.spent()
    assert carried["cache_read_tokens"] == 9 and carried["cache_write_tokens"] == 0

    later = a_meter()
    later.restore(carried)
    later.count_tokens(Usage(input_tokens=1, output_tokens=1, cache_write_tokens=2))

    assert spent_of(later).cache_read_tokens == 9
    assert spent_of(later).cache_write_tokens == 2


def test_a_checkpoint_from_before_the_fields_restores_with_zeros() -> None:
    later = a_meter()
    later.restore({"steps": 3, "cost_cents": 0, "input_tokens": 40, "output_tokens": 2})

    spent = spent_of(later)

    assert spent.input_tokens == 40 and spent.cache_read_tokens == 0


def test_spent_defaults_the_new_counters() -> None:
    """A `Spent` built from an older record — no cache keys — is still a `Spent`."""
    assert Spent(steps=1).cache_read_tokens == 0 and Spent(steps=1).cache_write_tokens == 0


async def test_a_thread_turns_cache_tokens_reach_spent(tmp_path: Path) -> None:
    """The join (BUG-063): the conversation writes the turn's `Usage` into the step's output and
    the meter reads it back through `step._usage_of`, which dropped the two cache counters — so
    every piece was tested and `Spent.cache_read_tokens` was still `0` for every thread turn.
    Measured by the product on 0.34.0. `Turn.usage` → `Spent`, end to end."""
    from typing import Any, cast

    from shadow_hdk.kernel import Turn
    from shadow_hdk.kernel.ports import AgentSession
    from shadow_hdk.runtime import Approvals, Ports
    from shadow_hdk.runtime.testing import InMemoryComponents, ListSink
    from shadow_hdk.runtime.threads import InMemoryThreads, Thread
    from tests.wire.test_a_thread_crosses_the_wire import AllowAll

    class Reporting:
        async def open(self, **_: Any) -> AgentSession:
            class _Session:
                async def turn(self, prompt: str) -> Turn:
                    return Turn(
                        text="ok",
                        usage=Usage(
                            input_tokens=10,
                            output_tokens=30,
                            cache_read_tokens=531,
                            cache_write_tokens=2458,
                        ),
                    )

                async def close(self) -> None:
                    pass

            return cast(AgentSession, _Session())

    thread = await Thread.open(
        agent=cast(Any, Reporting()),
        ports=Ports(
            model=None,
            components=(InMemoryComponents([]),),
            governance=AllowAll(),
            sink=ListSink(),
            clock=FixedClock(),
        ),
        store=InMemoryThreads(),
        root=tmp_path,
        lease=Lease(Ceiling(20, 600, None), Floor(0)),
        approvals=Approvals(),
        mode="full",
    )
    try:
        [e async for e in thread.turn("one")]
        [e async for e in thread.turn("two")]
        spent = thread.record.spent
        assert spent.input_tokens == 20 and spent.output_tokens == 60
        assert spent.cache_read_tokens == 1062, spent
        assert spent.cache_write_tokens == 4916, spent
        assert spent.unmetered is False
    finally:
        await thread.close()


def test_the_steps_usage_is_read_back_whole() -> None:
    """The two-line reproduction the product sent, kept as the unit under the join."""
    import json

    from shadow_hdk.kernel.contracts import dump
    from shadow_hdk.kernel.observations import Completed
    from shadow_hdk.runtime.step import _usage_of

    usage = Usage(input_tokens=10, output_tokens=30, cache_read_tokens=531, cache_write_tokens=2458)
    out = {"text": "x", "stop_reason": "end_turn", "usage": json.loads(dump(usage, Usage))}
    assert _usage_of(Completed(out)) == usage
