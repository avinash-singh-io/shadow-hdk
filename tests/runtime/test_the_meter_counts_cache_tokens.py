"""The meter counts what the cache did across a thread's turns, and the record carries it (D141).

`Spent.cache_read_tokens` / `cache_write_tokens` sum every call's report; a call that reported no
tokens at all makes the counts a floor (`unmetered`), as it does for input and output. A record or
a checkpoint written before these fields existed restores with zeros — the count is a floor there
too, and nothing older than the field is refused.
"""

from __future__ import annotations

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
