"""Quantities that are exact, carry their unit, and can be indeterminate (D26).

**Fixed-point, never float.** Floats cannot hold 0.16, and their rounding depends on the host.
Every magnitude here is a `Decimal` quantized to `SCALE` fractional digits, half-even, under a
context this module owns — never the thread's default — so two machines produce the same digits.

**A bare number is not a claim.** A `Quantity` carries its unit, and a ratio carries the parts it
was made from, so *3 of 1842* stays *3 of 1842* rather than collapsing to 0.0016 with the story
lost. That is also what lets `percent` be exact: it re-derives from the parts instead of scaling a
number that has already been rounded.

**Total.** No operation raises on its inputs. Division by zero and a unit mismatch each return an
`Indeterminate` that says why, and an indeterminate propagates through anything built on it — the
same object, so a reader can find where it started.

That was a claim this module made and did not keep (BUG-013). `_fix` quantizes to `SCALE` places
under a 34-digit context, and a magnitude that does not fit — `1e22`, `Infinity`, the product of two
values that each fit — raises `InvalidOperation`. It raised through `evaluate`, through `invoke`,
and out of the component altogether, which is exactly what D7 says a component may not do.
`evaluate` catches it now and answers `out_of_range`, so the sentence above is true.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation
from typing import Literal

SCALE = 12
"""Fractional digits every stored magnitude is quantized to. Twelve because the worked examples
are parts-per-hundred over counts in the thousands, and twelve places is six orders past anything
a person reads. A deployment that needs more says so on its engine, not per ground."""

CONTEXT = Context(prec=34, rounding=ROUND_HALF_EVEN)
"""Ours, not the thread's. `decimal.getcontext()` is whatever the host last set it to."""

QUANTUM = Decimal(10) ** -SCALE

Reason = Literal[
    "division_by_zero",
    "unit_mismatch",
    "missing_column",
    "type_mismatch",
    "empty",
    "unknown_node",
    "out_of_range",
]


@dataclass(frozen=True)
class Indeterminate:
    """The typed nothing. A comparison built on it answers neither true nor false."""

    reason: Reason
    detail: str

    def __str__(self) -> str:
        return f"indeterminate ({self.reason}): {self.detail}"


def _fix(magnitude: Decimal) -> Decimal:
    return CONTEXT.quantize(magnitude, QUANTUM)


def canonical(magnitude: Decimal | str) -> str:
    """One spelling per quantity (BUG-013).

    `"1"`, `"1.0"` and `"1.00"` are one number and produced three different fingerprints, because
    identity was built by `str()`-ing whatever `Decimal` happened to be parsed. A fingerprint that
    changes with spelling cannot answer *have I derived this before*.

    Through the **same quantizer the arithmetic uses**, so the identity of a derivation is stated at
    the scale the derivation is actually carried out at — twelve places. A difference this engine
    can represent is a difference it keeps; one it cannot represent was never going to survive the
    calculation either.

    A magnitude that does not fit is spelled as it was given. It cannot be derived from, and
    `evaluate` says so — but a fingerprint is an identity, not a judgement, and two unusable inputs
    that differ should still be told apart.
    """
    try:
        return str(_fix(Decimal(magnitude)))
    except (InvalidOperation, ValueError, ArithmeticError):
        return str(magnitude)


@dataclass(frozen=True)
class Quantity:
    """A magnitude with a unit. `of` and `numerator` are set on a ratio, so the parts survive."""

    magnitude: Decimal
    unit: str
    of: Quantity | None = None
    numerator: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "magnitude", _fix(Decimal(self.magnitude)))

    def __str__(self) -> str:
        return f"{self.magnitude}{self.unit}" if self.unit else str(self.magnitude)


Value = Quantity | Indeterminate


def _product_unit(a: str, b: str) -> str:
    """Dimensionless is the identity, and factors are sorted so the product commutes."""
    factors = sorted(part for part in (*a.split("·"), *b.split("·")) if part)
    return "·".join(factors)


def add(a: Value, b: Value) -> Value:
    if isinstance(a, Indeterminate):
        return a
    if isinstance(b, Indeterminate):
        return b
    if a.unit != b.unit:
        return Indeterminate(
            "unit_mismatch",
            f"cannot add {a.unit or 'a plain number'} to {b.unit or 'a plain number'}",
        )
    return Quantity(CONTEXT.add(a.magnitude, b.magnitude), a.unit)


def sub(a: Value, b: Value) -> Value:
    if isinstance(a, Indeterminate):
        return a
    if isinstance(b, Indeterminate):
        return b
    if a.unit != b.unit:
        return Indeterminate(
            "unit_mismatch",
            f"cannot subtract {b.unit or 'a plain number'} from {a.unit or 'a plain number'}",
        )
    return Quantity(CONTEXT.subtract(a.magnitude, b.magnitude), a.unit)


def mul(a: Value, b: Value) -> Value:
    if isinstance(a, Indeterminate):
        return a
    if isinstance(b, Indeterminate):
        return b
    return Quantity(CONTEXT.multiply(a.magnitude, b.magnitude), _product_unit(a.unit, b.unit))


def div(a: Value, b: Value) -> Value:
    """Like units divide to a dimensionless ratio that remembers its parts."""
    if isinstance(a, Indeterminate):
        return a
    if isinstance(b, Indeterminate):
        return b
    if b.magnitude == 0:
        return Indeterminate("division_by_zero", f"{a} divided by zero {b.unit}".rstrip())
    if a.unit == b.unit:
        unit = ""
    elif not b.unit:
        unit = a.unit
    else:
        unit = f"{a.unit or '1'}/{b.unit}"
    return Quantity(CONTEXT.divide(a.magnitude, b.magnitude), unit, of=b, numerator=a.magnitude)


def percent(x: Value) -> Value:
    """A dimensionless ratio as parts per hundred — re-derived from the parts, so it is exact."""
    if isinstance(x, Indeterminate):
        return x
    if x.unit:
        return Indeterminate(
            "unit_mismatch", f"only a plain ratio can be a percentage, not {x.unit}"
        )
    if x.of is not None and x.numerator is not None:
        magnitude = CONTEXT.divide(CONTEXT.multiply(x.numerator, Decimal(100)), x.of.magnitude)
    else:
        magnitude = CONTEXT.multiply(x.magnitude, Decimal(100))
    return Quantity(magnitude, "%", of=x.of, numerator=x.numerator)


Comparison = Literal["lt", "le", "gt", "ge", "eq", "ne"]


def compare(a: Value, op: Comparison, b: Value) -> bool | Indeterminate:
    """True, false, or — when either side is nothing, or the units differ — indeterminate."""
    if isinstance(a, Indeterminate):
        return a
    if isinstance(b, Indeterminate):
        return b
    if a.unit != b.unit:
        return Indeterminate(
            "unit_mismatch",
            f"cannot compare {a.unit or 'a plain number'} with {b.unit or 'a plain number'}",
        )
    x, y = a.magnitude, b.magnitude
    match op:
        case "lt":
            return x < y
        case "le":
            return x <= y
        case "gt":
            return x > y
        case "ge":
            return x >= y
        case "eq":
            return x == y
        case "ne":
            return x != y


__all__ = [
    "CONTEXT",
    "QUANTUM",
    "SCALE",
    "Comparison",
    "Indeterminate",
    "Quantity",
    "Reason",
    "Value",
    "add",
    "compare",
    "div",
    "mul",
    "percent",
    "sub",
]
