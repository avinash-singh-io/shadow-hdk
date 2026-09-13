"""What a step is charged is what **that step** spent (BUG-011).

`Spend` is cumulative because a session is, and its own docstring says why money must accumulate as
`Decimal` before it is rounded: *converting per call would round 0.004 USD to zero and a thousand
such calls would still be zero*. But `_usage` handed the meter the running **total** on every turn,
and `step.py` adds what it is handed — so the second turn re-charged the first, the third re-charged
both, and the class's own argument was defeated by the one place it was read.

Two claims, and they are the same claim from opposite ends: the meter is told the **delta**, and no
fraction of a cent is lost on the way.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pydantic import JsonValue

from shadow_hdk.adapters.acp.client import Spend
from shadow_hdk.kernel import Completed
from tests.adapters.acp.conftest import inside_a_run
from tests.adapters.acp.test_agent import child

TURN_IN, TURN_OUT = 1200, 200
"""What `spikes/acp/agent.py` reports for one turn."""


@dataclass
class Money:
    amount: float | str
    currency: str = "USD"


def charged(observation: object) -> dict[str, JsonValue]:
    assert isinstance(observation, Completed)
    assert isinstance(observation.output, dict)
    usage = observation.output["usage"]
    assert isinstance(usage, dict)
    return usage


# ------------------------------------------------------------------ through the bridge


async def test_a_second_turn_is_charged_what_it_spent_not_what_the_session_holds() -> None:
    """The bug, at the size the audit reported it: two identical turns, charged 1× and then 2×."""
    async with child() as agent:
        first = charged(await agent.invoke("child", {"brief": "just answer"}))
        second = charged(await agent.invoke("child", {"brief": "just answer"}))

    assert first["input_tokens"] == TURN_IN
    assert second["input_tokens"] == TURN_IN, "the second turn was charged the session's total"
    assert second["output_tokens"] == TURN_OUT


async def test_three_turns_charge_the_session_total_between_them() -> None:
    """The property behind the previous test: the meter's sum is the session's spend, not more.

    Asserting a single turn's number can be satisfied by a purse that leaks in the other direction,
    so what is asserted here is that the parts add to the whole.
    """
    async with child() as agent:
        turns = [charged(await agent.invoke("child", {"brief": "just answer"})) for _ in range(3)]
        session_total = agent.client.spend.input_tokens

    charged_in = [turn["input_tokens"] for turn in turns]
    assert all(isinstance(amount, int) for amount in charged_in)
    assert sum(amount for amount in charged_in if isinstance(amount, int)) == session_total
    assert session_total == 3 * TURN_IN


async def test_the_session_purse_still_holds_the_whole_session() -> None:
    """Charging the delta must not cost us the running total — a host asking what this child has
    cost so far is asking about the session, and that answer still exists."""
    async with child() as agent:
        await agent.invoke("child", {"brief": "just answer"})
        await agent.invoke("child", {"brief": "just answer"})
        spend = agent.client.spend

    assert (spend.input_tokens, spend.output_tokens) == (2 * TURN_IN, 2 * TURN_OUT)


async def test_a_turn_that_reported_no_usage_is_unknown_and_not_free() -> None:
    """`None` is *nobody told us*; `0` is *told, and it was nothing*. A provider that reports
    nothing must not read as a free turn, or a meter's total is quietly wrong.

    The spike asks permission *before* it reaches its no-usage branch, so this has to run inside a
    real run under a governance that says yes — invoked bare, the child is denied and ends
    `cancelled`, which reports usage like any other turn and proves nothing.
    """

    async def two_turns() -> dict[str, JsonValue]:
        async with child() as agent:
            await agent.invoke("child", {"brief": "just answer"})
            return charged(await agent.invoke("child", {"brief": "no-usage please"}))

    silent = await inside_a_run(two_turns)

    assert silent["input_tokens"] is None, "a turn nobody priced was charged the last turn's tokens"
    assert silent["output_tokens"] is None
    assert silent["cost_cents"] == 1, (
        "tokens and money are answered separately: nobody reported tokens for this turn, while the "
        "mid-turn cost update did arrive — and two charges of $0.004 are the turn the total first "
        "crosses a whole cent"
    )


# ------------------------------------------------------------------ the purse itself


def test_two_hundred_sub_cent_charges_are_eighty_cents() -> None:
    """`Spend`'s own docstring, made a test: *two hundred of them are eighty cents, and that is
    what the meter is told*. It was not — every one of them was charged as nothing."""
    purse, charged_cents = Spend("USD"), 0
    for _ in range(200):
        purse.add_cost(Money("0.004"))
        charged_cents += purse.take().cents or 0

    assert purse.amount == Decimal("0.800")
    assert charged_cents == 80


def test_the_cent_is_charged_on_the_turn_the_total_crosses_it() -> None:
    """Where the fraction goes while it is not yet a cent: nowhere, and it is not lost.

    Four charges of $0.004 are 1.6 cents. Charging each in isolation truncates four times to zero;
    charging the *difference of the rounded totals* charges 0, 1, 0, 1 — never more than half a
    cent adrift from the truth, and never adrift for long.
    """
    purse, per_turn = Spend("USD"), []
    for _ in range(4):
        purse.add_cost(Money("0.004"))
        per_turn.append(purse.take().cents)

    assert per_turn == [0, 1, 0, 1]


def test_a_charge_that_never_arrived_is_unknown() -> None:
    """A turn with no cost reported at all is not a turn that cost nothing."""
    assert Spend("USD").take().cents is None


def test_a_currency_we_cannot_read_is_unknown_not_zero() -> None:
    """Unchanged by the delta, and worth holding: an exchange rate is policy about a tenant's
    contract, so a foreign charge is reported, never invented."""
    purse = Spend("USD")
    purse.add_cost(Money("1.00", "EUR"))
    taken = purse.take()

    assert taken.cents is None
    assert taken.foreign == {"EUR": Decimal("1.00")}


def test_taking_twice_charges_once() -> None:
    """The delta is *since the last take*, so a second read of the same turn charges nothing —
    which is what makes it safe for the one caller to be the only caller."""
    purse = Spend("USD")
    purse.add_tokens(_Usage(100, 10))
    first, second = purse.take(), purse.take()

    assert (first.input_tokens, second.input_tokens) == (100, None)


@dataclass
class _Usage:
    input_tokens: int
    output_tokens: int
    total_tokens: int = 0


def test_a_turn_with_no_charge_of_its_own_is_unknown_even_after_an_earlier_one() -> None:
    """Found by a mutation that survived: dropping the *arrived this turn* guard passed every test,
    because none of them had a purse with money in it and a quiet turn after.

    Once a session has been charged, `cents` is no longer `None` — so a delta computed without
    asking whether anything arrived reports a confident `0` for a turn nobody priced.
    """
    purse = Spend("USD")
    purse.add_cost(Money("1.00"))
    purse.take()

    assert purse.take().cents is None, "a turn nobody priced was charged a known zero"


def test_a_charge_that_arrived_and_was_nothing_is_a_known_zero() -> None:
    """The other side of the same line, and the reason it is `cost_seen` rather than `amount == 0`:
    a provider that priced the turn at nothing has *told* us, and a meter that files that under
    unknown stops claiming a total it could have supported."""
    purse = Spend("USD")
    purse.add_cost(Money("0.00"))

    assert purse.take().cents == 0


def test_a_currency_already_reported_is_not_reported_again() -> None:
    """Also a survivor: the foreign delta's filter was never exercised, because no test charged a
    foreign currency and then took twice. Without it a currency charged once is repeated as a
    `0` entry on every later turn, and a host doing its own conversion pays for each of them."""
    purse = Spend("USD")
    purse.add_cost(Money("1.00", "EUR"))
    first = purse.take()
    second = purse.take()

    assert first.foreign == {"EUR": Decimal("1.00")}
    assert second.foreign == {}, "a currency charged once was reported on a turn it did not arrive"
