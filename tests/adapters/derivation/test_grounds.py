"""A ground anyone can re-execute bit-for-bit (D26).

A ground is a closed tree as JSON, and one engine is its only interpreter. So the properties here
are the ones that make that true rather than merely said: an unknown node is refused when the tree
is **parsed**, not discovered when it is evaluated; a missing column or a wrong type is a typed
indeterminate that names the column; two fresh engines agree to the digit; and the fingerprint —
the ground's identity — moves when the ground moves and when the table moves, and not otherwise.

The worked example is R8's sentence, end to end: *3 of 1842 units, 0.16% against a 0.05% limit.*
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from shadow_hdk.adapters.derivation import (
    Indeterminate,
    Quantity,
    Table,
    evaluate,
    fingerprint,
    parse,
)

LOT = Table(
    columns={"status": "text", "weight": "number"},
    units={"weight": "kg"},
    row_unit="unit",
    rows=[{"status": "ok", "weight": "1.5"}] * 1839
    + [{"status": "defective", "weight": "1.4"}] * 3,
)

DEFECT_RATE = {
    "percent": {
        "div": [
            {"count_where": {"col": "status", "eq": "defective"}},
            {"count": "*"},
        ]
    }
}

AGAINST_THE_LIMIT = {"cmp": [DEFECT_RATE, "gt", {"lit": "0.05", "unit": "%"}]}


# ---------------------------------------------------------------- the worked example


def test_the_worked_example_end_to_end() -> None:
    rate = evaluate(parse(DEFECT_RATE), LOT)
    assert isinstance(rate, Quantity)
    assert rate.unit == "%"
    assert rate.magnitude == Decimal("0.162866449511")
    assert rate.of == Quantity(Decimal(1842), "unit"), "the denominator is part of the claim"
    assert evaluate(parse(AGAINST_THE_LIMIT), LOT) is True


def test_a_comparison_over_nothing_answers_indeterminate() -> None:
    empty = Table(columns={"status": "text"}, units={}, row_unit="unit", rows=[])
    verdict = evaluate(parse(AGAINST_THE_LIMIT), empty)
    assert isinstance(verdict, Indeterminate)
    assert verdict.reason == "division_by_zero"


# ---------------------------------------------------------------- typed data


def test_sum_carries_the_column_unit() -> None:
    total = evaluate(parse({"sum": "weight"}), LOT)
    assert isinstance(total, Quantity)
    assert total.unit == "kg"
    assert total.magnitude == Decimal("1839") * Decimal("1.5") + Decimal("3") * Decimal("1.4")


def test_a_missing_column_is_indeterminate_and_names_the_column() -> None:
    out = evaluate(parse({"sum": "mass"}), LOT)
    assert isinstance(out, Indeterminate)
    assert out.reason == "missing_column"
    assert "mass" in out.detail


def test_summing_a_text_column_is_a_type_mismatch_not_a_crash() -> None:
    out = evaluate(parse({"sum": "status"}), LOT)
    assert isinstance(out, Indeterminate)
    assert out.reason == "type_mismatch"
    assert "status" in out.detail


def test_a_cell_that_is_not_a_number_is_a_type_mismatch_naming_the_row() -> None:
    dirty = Table(
        columns={"weight": "number"},
        units={"weight": "kg"},
        row_unit="unit",
        rows=[{"weight": "1.5"}, {"weight": "heavy"}],
    )
    out = evaluate(parse({"sum": "weight"}), dirty)
    assert isinstance(out, Indeterminate)
    assert out.reason == "type_mismatch"
    assert "heavy" in out.detail or "row 2" in out.detail


def test_count_where_on_a_missing_column_is_indeterminate() -> None:
    out = evaluate(parse({"count_where": {"col": "colour", "eq": "red"}}), LOT)
    assert isinstance(out, Indeterminate)
    assert out.reason == "missing_column"


# ---------------------------------------------------------------- the tree is closed


@pytest.mark.parametrize(
    "tree",
    [
        {"eval": "1+1"},
        {"python": "sum(x)"},
        {"add": [{"lit": "1"}, {"lit": "2"}, {"lit": "3"}]},
        {"cmp": [{"lit": "1"}, "roughly", {"lit": "1"}]},
        {"lit": 1.5},
        {},
        "just a string",
    ],
    ids=["eval", "python", "arity", "unknown-op", "float-literal", "empty", "not-a-node"],
)
def test_anything_outside_the_vocabulary_is_refused_at_parse(tree: object) -> None:
    """Refused when read, not when run. A ground that fails halfway through evaluation is a ground
    somebody has already trusted; a ground that cannot be parsed never got that far."""
    with pytest.raises(ValueError):
        parse(tree)


def test_a_float_literal_is_refused_because_it_cannot_be_exact() -> None:
    with pytest.raises(ValueError, match="string"):
        parse({"lit": 0.16})


# ---------------------------------------------------------------- bit-for-bit


def test_two_fresh_evaluations_agree_to_the_digit() -> None:
    first = evaluate(parse(DEFECT_RATE), LOT)
    second = evaluate(parse(json.loads(json.dumps(DEFECT_RATE))), LOT)
    assert isinstance(first, Quantity) and isinstance(second, Quantity)
    assert str(first.magnitude) == str(second.magnitude)
    assert first == second


def test_the_fingerprint_is_the_grounds_identity() -> None:
    same = fingerprint(parse(DEFECT_RATE), LOT)
    assert same == fingerprint(parse(json.loads(json.dumps(DEFECT_RATE))), LOT)
    assert len(same) == 64, "a sha256 hex digest"


def test_the_fingerprint_moves_when_the_table_moves() -> None:
    moved = Table(
        columns=LOT.columns, units=LOT.units, row_unit=LOT.row_unit, rows=[*LOT.rows[:-1]]
    )
    assert fingerprint(parse(DEFECT_RATE), LOT) != fingerprint(parse(DEFECT_RATE), moved)


def test_the_fingerprint_moves_when_the_ground_moves() -> None:
    other = {"percent": {"div": [{"count_where": {"col": "status", "eq": "ok"}}, {"count": "*"}]}}
    assert fingerprint(parse(DEFECT_RATE), LOT) != fingerprint(parse(other), LOT)


def test_the_fingerprint_does_not_move_when_only_key_order_does() -> None:
    """Canonical, or it is not an identity. `{"cmp": [...]}` written with its keys in a different
    order is the same ground and must hash the same."""
    reordered = {
        "cmp": [
            {"percent": {"div": [{"count": "*"}, {"count": "*"}]}},
            "gt",
            {"unit": "%", "lit": "0.05"},
        ]
    }
    ordered = {
        "cmp": [
            {"percent": {"div": [{"count": "*"}, {"count": "*"}]}},
            "gt",
            {"lit": "0.05", "unit": "%"},
        ]
    }
    assert fingerprint(parse(reordered), LOT) == fingerprint(parse(ordered), LOT)


# ---------------------------------------------------------------- the declarations are load-bearing


def test_a_text_column_of_numeric_looking_cells_still_does_not_sum() -> None:
    """The declared type decides, not the cells. An identifier column holding "001", "002" would
    otherwise sum to a meaningless number — silently, because every cell parses."""
    ids = Table(
        columns={"id": "text"}, units={}, row_unit="unit", rows=[{"id": "001"}, {"id": "002"}]
    )
    out = evaluate(parse({"sum": "id"}), ids)
    assert isinstance(out, Indeterminate)
    assert out.reason == "type_mismatch"
    assert "text" in out.detail


def test_a_ground_round_trips_through_its_canonical_tree() -> None:
    """`to_tree(parse(x))` is `x`, keys sorted — including a literal's unit, which a fingerprint
    test alone could not pin because both sides would drop it the same way."""
    from shadow_hdk.adapters.derivation import to_tree

    assert to_tree(parse(AGAINST_THE_LIMIT)) == AGAINST_THE_LIMIT


def test_an_unknown_column_type_is_refused_when_the_table_is_built() -> None:
    with pytest.raises(ValueError, match="float"):
        Table(columns={"x": "float"}, units={}, row_unit="unit", rows=[])  # type: ignore[dict-item]


def test_counting_a_column_counts_rows_that_have_it() -> None:
    sparse = Table(
        columns={"weight": "number"},
        units={"weight": "kg"},
        row_unit="unit",
        rows=[{"weight": "1"}, {}, {"weight": "2"}],
    )
    out = evaluate(parse({"count": "weight"}), sparse)
    assert out == Quantity(Decimal(2), "unit")


def test_the_fingerprint_does_not_move_when_a_row_is_written_in_another_key_order() -> None:
    """The table half of canonical. `to_tree` rebuilds a ground structurally, so the ground half
    is canonical by construction — which is exactly why a `sort_keys=False` mutation survived:
    nothing reached the JSON sort with keys out of order. A row dict can, and this one does."""
    one = Table(
        columns={"a": "text", "b": "text"}, units={}, row_unit="unit", rows=[{"a": "1", "b": "2"}]
    )
    other = Table(
        columns={"b": "text", "a": "text"}, units={}, row_unit="unit", rows=[{"b": "2", "a": "1"}]
    )
    assert fingerprint(parse({"count": "*"}), one) == fingerprint(parse({"count": "*"}), other)
