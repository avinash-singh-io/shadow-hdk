"""A lease caps tokens, so a thread can be budgeted before it reaches the window (ENH-052).

Steps, seconds and cents were capped and tokens were not, so a product that budgets in tokens could
not cap a run at all and a long thread walked into the model's context window with nothing to stop
it — learning where the limit was from a provider error.

The meter already counts tokens and already knows when a provider's numbers are unreliable, and that
second part decides the design: a ceiling enforced on numbers nobody gave would stop runs for
arithmetic that was never done.
"""

import pytest

from shadow_hdk.kernel import Ceiling, Floor, Lease, Usage
from shadow_hdk.runtime.session import LeaseMeter
from shadow_hdk.runtime.testing import FixedClock

pytestmark = pytest.mark.anyio


def a_meter(*, max_tokens: int | None) -> LeaseMeter:
    return LeaseMeter(Lease(Ceiling(100, 600, None, max_tokens=max_tokens), Floor(0)), FixedClock())


def spend(
    meter: LeaseMeter, *, input_tokens: int | None = 0, output_tokens: int | None = 0
) -> None:
    meter.count_tokens(Usage(input_tokens=input_tokens, output_tokens=output_tokens))


def test_a_run_under_its_token_ceiling_continues() -> None:
    meter = a_meter(max_tokens=1000)
    spend(meter, input_tokens=400, output_tokens=100)
    assert meter.check() is None


def test_a_run_over_its_token_ceiling_stops_the_way_one_out_of_money_does() -> None:
    """The same vocabulary, because to a product it is the same event: the budget is gone."""
    meter = a_meter(max_tokens=1000)
    spend(meter, input_tokens=900, output_tokens=200)
    assert meter.check() == "lease_exhausted"


def test_no_ceiling_means_no_cap() -> None:
    meter = a_meter(max_tokens=None)
    spend(meter, input_tokens=10**9)
    assert meter.check() is None


def test_a_ceiling_is_not_enforced_against_numbers_the_provider_never_gave() -> None:
    """Unknown is unknown. A provider that reports nothing must not exhaust a run by omission —
    the meter already tracks that its numbers are unreliable, and this is what that is for."""
    meter = a_meter(max_tokens=10)
    spend(meter, input_tokens=None, output_tokens=None)
    spend(meter, input_tokens=5000)
    assert meter.check() is None, "a run must not be stopped for arithmetic nobody did"


def test_what_is_left_is_reported() -> None:
    meter = a_meter(max_tokens=1000)
    spend(meter, input_tokens=300, output_tokens=200)
    assert meter.remaining().ceiling.max_tokens == 500


def test_what_is_left_is_never_negative() -> None:
    meter = a_meter(max_tokens=100)
    spend(meter, input_tokens=500)
    assert meter.remaining().ceiling.max_tokens == 0


def test_unknown_tokens_are_reported_as_unknown_not_as_plenty() -> None:
    """Reporting the full ceiling would tell a product it has budget it cannot account for."""
    meter = a_meter(max_tokens=1000)
    spend(meter, input_tokens=None, output_tokens=None)
    assert meter.remaining().ceiling.max_tokens is None


def test_a_child_cannot_be_carved_more_than_the_parent_holds() -> None:
    """A carve that handed out more than it had would make the parent's ceiling advisory."""
    meter = a_meter(max_tokens=1000)
    spend(meter, input_tokens=800)
    carved = meter.carve(Ceiling(10, 10, None, max_tokens=900))
    assert carved.ceiling.max_tokens == 200, carved.ceiling


def test_tokens_a_cache_moved_count_toward_the_budget() -> None:
    """D141's tokens are tokens. A budget that ignored them would let a thread with a warm cache
    run well past what its product was charged for, which is the opposite of a budget.
    """
    meter = a_meter(max_tokens=1000)
    meter.count_tokens(
        Usage(input_tokens=100, output_tokens=100, cache_read_tokens=700, cache_write_tokens=200)
    )
    assert meter.check() == "lease_exhausted"
    assert meter.tokens_spent() == 1100, meter.tokens_spent()
