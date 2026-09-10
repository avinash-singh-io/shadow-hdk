"""Quantities that are exact, carry their unit, and can be indeterminate (D26).

A test that checks one value does not check the arithmetic, so the laws are property tests. The
worked example from R8 — *3 of 1842 units, 0.16%* — is here too, because it is the sentence this
phase exists to make checkable, and because 0.16 is a number floats cannot hold.
"""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from shadow_hdk.adapters.derivation import (
    SCALE,
    Indeterminate,
    Quantity,
    add,
    compare,
    div,
    mul,
    percent,
    sub,
)

magnitudes = st.decimals(
    min_value=Decimal("-1000000"), max_value=Decimal("1000000"), places=6, allow_nan=False
)
units = st.sampled_from(["unit", "kg", "s"])


def q(m: Decimal | str | int, unit: str = "unit") -> Quantity:
    return Quantity(Decimal(str(m)), unit)


# ---------------------------------------------------------------- laws


@given(a=magnitudes, b=magnitudes, unit=units)
def test_addition_is_commutative_within_a_unit(a: Decimal, b: Decimal, unit: str) -> None:
    assert add(q(a, unit), q(b, unit)) == add(q(b, unit), q(a, unit))


@given(a=magnitudes, b=magnitudes, unit=units)
def test_multiplication_is_commutative(a: Decimal, b: Decimal, unit: str) -> None:
    assert mul(q(a, unit), q(b, "unit")) == mul(q(b, "unit"), q(a, unit))


@given(a=magnitudes, unit=units)
def test_zero_is_the_additive_identity(a: Decimal, unit: str) -> None:
    assert add(q(a, unit), q(0, unit)) == q(a, unit)


@given(a=magnitudes, unit=units)
def test_one_is_the_multiplicative_identity(a: Decimal, unit: str) -> None:
    # Dimensionless one. A 1 with a unit is not an identity; multiplying by it changes the unit.
    assert mul(q(a, unit), q(1, "")) == q(a, unit)


@given(a=magnitudes, b=magnitudes.filter(lambda d: d != 0))
@settings(max_examples=300)
def test_dividing_then_multiplying_returns_within_the_scale(a: Decimal, b: Decimal) -> None:
    """Division is the one inexact operation, quantized to SCALE places — so a round trip lands
    within one unit of the last place, never further. That bound *is* the precision claim."""
    back = mul(div(q(a), q(b)), q(b))
    assert isinstance(back, Quantity)
    # Two quantizations, each at most half a quantum: the quotient's, scaled by |b|, and the
    # product's own. So the bound is a quantum times (|b| + 1), and that arithmetic *is* the claim.
    assert abs(back.magnitude - a) <= Decimal(10) ** -SCALE * (abs(b) + 1), (a, b, back.magnitude)


@given(a=magnitudes, b=magnitudes)
def test_a_result_never_carries_more_than_the_scale(a: Decimal, b: Decimal) -> None:
    for result in (add(q(a), q(b)), mul(q(a), q(b)), sub(q(a), q(b))):
        assert isinstance(result, Quantity)
        exponent = result.magnitude.as_tuple().exponent
        assert isinstance(exponent, int), "a finite quantity has an integer exponent"
        assert -exponent <= SCALE


# ---------------------------------------------------------------- honesty


def test_a_quantity_carries_its_unit() -> None:
    assert q(3, "unit").unit == "unit"
    assert add(q(1, "kg"), q(2, "kg")) == q(3, "kg")


def test_adding_different_units_is_indeterminate_not_a_number() -> None:
    out = add(q(1, "kg"), q(2, "s"))
    assert isinstance(out, Indeterminate)
    assert out.reason == "unit_mismatch"
    assert "kg" in out.detail and "s" in out.detail


def test_dividing_like_units_is_dimensionless_and_keeps_the_denominator() -> None:
    ratio = div(q(3, "unit"), q(1842, "unit"))
    assert isinstance(ratio, Quantity)
    assert ratio.unit == ""
    assert ratio.of == q(1842, "unit"), "the denominator is part of the claim"


def test_the_worked_example_is_exact() -> None:
    """*3 of 1842 units, 0.16%.* Floats give 0.16286644951140064; fixed-point gives the digits a
    person can re-derive by hand and a second machine will reproduce."""
    out = percent(div(q(3, "unit"), q(1842, "unit")))
    assert isinstance(out, Quantity)
    assert out.unit == "%"
    assert out.magnitude == Decimal("0.162866449511")
    assert str(out.magnitude) == "0.162866449511"


def test_percent_of_a_dimensioned_quantity_is_indeterminate() -> None:
    out = percent(q(3, "kg"))
    assert isinstance(out, Indeterminate)
    assert out.reason == "unit_mismatch"


# ---------------------------------------------------------------- totality


def test_division_by_zero_is_indeterminate() -> None:
    out = div(q(3), q(0))
    assert isinstance(out, Indeterminate)
    assert out.reason == "division_by_zero"


@given(a=magnitudes)
def test_an_indeterminate_propagates_through_every_operation(a: Decimal) -> None:
    nothing = Indeterminate(reason="division_by_zero", detail="earlier")
    for op in (add, sub, mul, div):
        assert op(q(a), nothing) is nothing
        assert op(nothing, q(a)) is nothing
    assert percent(nothing) is nothing


# ---------------------------------------------------------------- comparison


def test_a_comparison_can_answer_true_false_or_indeterminate() -> None:
    limit = q("0.05", "%")
    assert compare(percent(div(q(3), q(1842))), "gt", limit) is True
    assert compare(q("0.01", "%"), "gt", limit) is False
    verdict = compare(div(q(3), q(0)), "gt", limit)
    assert isinstance(verdict, Indeterminate)


def test_comparing_different_units_is_indeterminate() -> None:
    verdict = compare(q(1, "kg"), "lt", q(2, "s"))
    assert isinstance(verdict, Indeterminate)
    assert verdict.reason == "unit_mismatch"


def test_rounding_is_half_even_as_the_decision_says() -> None:
    """D26 says half-even. Nothing above can tell half-even from half-up, because a tie at the
    thirteenth place never arises from six-place inputs — so this constructs one. Five at the
    thirteenth place rounds to the even neighbour, which is zero; half-up would give one quantum."""
    exactly_half = Quantity(Decimal("0.0000000000005"), "")
    assert exactly_half.magnitude == Decimal("0")
    one_and_a_half = Quantity(Decimal("0.0000000000015"), "")
    assert one_and_a_half.magnitude == Decimal("0.000000000002")


def test_the_host_thread_context_does_not_change_the_answer() -> None:
    """D26's actual claim: the engine owns its context, so two machines produce the same digits.

    A mutation quantizing under the thread default survived, because the default happens to be
    half-even too and nothing could tell them apart. This poisons the thread — a host that set
    `getcontext().rounding` to something else, as hosts do — and asserts the engine did not notice.
    """
    import decimal

    saved = decimal.getcontext().copy()
    try:
        decimal.getcontext().rounding = decimal.ROUND_UP
        decimal.getcontext().prec = 6
        tie = Quantity(Decimal("0.0000000000005"), "")
        assert tie.magnitude == Decimal("0"), "the host's rounding leaked into the engine"
        wide = mul(q("123456.789012"), q("1000000", ""))
        assert isinstance(wide, Quantity)
        assert wide.magnitude == Decimal("123456789012"), "the host's precision leaked in"
    finally:
        decimal.setcontext(saved)
