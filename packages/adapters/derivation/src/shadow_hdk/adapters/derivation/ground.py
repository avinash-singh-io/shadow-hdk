"""A ground: a closed expression tree, and the one engine that evaluates it (D26).

**Closed.** The vocabulary is the nodes below and nothing else. `parse` refuses anything outside it
*when the tree is read* — an `eval`, a lambda, a third operand, a float literal — so a ground that
fails halfway through evaluation is not a thing that can happen. That is what *total* buys, and it
is why the language is small: `09` §2's argument against free-form predicates applies to grounds
exactly, because a ground somebody else cannot re-run is a number with a story attached.

**Structural.** Evaluation walks the tree once. No loops, no recursion beyond the tree's own depth,
no user functions. Every node yields a `Value`, a verdict, or an `Indeterminate` that says why.

**Canonical.** `to_tree` gives a ground back as key-sorted JSON, and `fingerprint` hashes that with
the table's canonical form. Two grounds with the same fingerprint are the same claim; the same
ground written with its keys in a different order hashes the same.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal, get_args

from shadow_hdk.adapters.derivation.table import Table
from shadow_hdk.adapters.derivation.values import (
    Comparison,
    Indeterminate,
    Quantity,
    Value,
    add,
    compare,
    div,
    mul,
    percent,
    sub,
)

BinaryOp = Literal["add", "sub", "mul", "div"]
COMPARISONS: frozenset[str] = frozenset(get_args(Comparison))


@dataclass(frozen=True)
class Lit:
    magnitude: Decimal
    unit: str


@dataclass(frozen=True)
class Count:
    col: str | None
    """`None` counts every row; a name counts rows where that column is present."""


@dataclass(frozen=True)
class CountWhere:
    col: str
    eq: str


@dataclass(frozen=True)
class Sum:
    col: str


@dataclass(frozen=True)
class Binary:
    op: BinaryOp
    left: Ground
    right: Ground


@dataclass(frozen=True)
class Percent:
    inner: Ground


@dataclass(frozen=True)
class Cmp:
    left: Ground
    op: Comparison
    right: Ground


Ground = Lit | Count | CountWhere | Sum | Binary | Percent | Cmp

VOCABULARY = frozenset(
    {"lit", "count", "count_where", "sum", "add", "sub", "mul", "div", "percent", "cmp"}
)


# ---------------------------------------------------------------- parse: refuse at the door


def parse(tree: object) -> Ground:
    """A ground from JSON, or a `ValueError` naming what was outside the vocabulary."""
    if not isinstance(tree, dict) or len(tree) == 0:
        raise ValueError(f"unknown_node: a ground is an object with one key, not {tree!r}")
    keys = set(tree)
    if keys == {"lit", "unit"} or keys == {"lit"}:
        raw = tree["lit"]
        if not isinstance(raw, str):
            raise ValueError(
                f"unknown_node: a literal must be a string so it stays exact, not {raw!r}"
            )
        try:
            magnitude = Decimal(raw)
        except InvalidOperation as bad:
            raise ValueError(f"unknown_node: {raw!r} is not a number") from bad
        unit = tree.get("unit", "")
        if not isinstance(unit, str):
            raise ValueError(f"unknown_node: a unit is a string, not {unit!r}")
        return Lit(magnitude, unit)
    if len(keys) != 1:
        raise ValueError(f"unknown_node: a ground has one key, got {sorted(keys)}")
    (key,) = keys
    body = tree[key]
    match key:
        case "count":
            if body == "*":
                return Count(None)
            if isinstance(body, str):
                return Count(body)
        case "count_where":
            if (
                isinstance(body, dict)
                and set(body) == {"col", "eq"}
                and isinstance(body["col"], str)
                and isinstance(body["eq"], str)
            ):
                return CountWhere(body["col"], body["eq"])
        case "sum":
            if isinstance(body, str):
                return Sum(body)
        case "add" | "sub" | "mul" | "div":
            if isinstance(body, list) and len(body) == 2:
                return Binary(key, parse(body[0]), parse(body[1]))  # type: ignore[arg-type]
        case "percent":
            return Percent(parse(body))
        case "cmp":
            if isinstance(body, list) and len(body) == 3 and body[1] in COMPARISONS:
                return Cmp(parse(body[0]), body[1], parse(body[2]))
        case _:
            raise ValueError(f"unknown_node: {key!r} is not in the vocabulary {sorted(VOCABULARY)}")
    raise ValueError(f"unknown_node: {key!r} does not take {body!r}")


# ---------------------------------------------------------------- evaluate: total, structural


def evaluate(ground: Ground, table: Table) -> Value | bool | Indeterminate:
    match ground:
        case Lit(magnitude, unit):
            return Quantity(magnitude, unit)
        case Count(None):
            return Quantity(Decimal(len(table.rows)), table.row_unit)
        case Count(col):
            if col not in table.columns:
                return _missing(col, table)
            return Quantity(Decimal(sum(1 for row in table.rows if col in row)), table.row_unit)
        case CountWhere(col, eq):
            if col not in table.columns:
                return _missing(col, table)
            matched = sum(1 for row in table.rows if str(row.get(col, "")) == eq)
            return Quantity(Decimal(matched), table.row_unit)
        case Sum(col):
            return _sum(col, table)
        case Binary(op, left, right):
            a = evaluate(left, table)
            b = evaluate(right, table)
            if isinstance(a, bool) or isinstance(b, bool):
                return Indeterminate("type_mismatch", f"cannot {op} a comparison verdict")
            return {"add": add, "sub": sub, "mul": mul, "div": div}[op](a, b)
        case Percent(inner):
            x = evaluate(inner, table)
            if isinstance(x, bool):
                return Indeterminate("type_mismatch", "cannot take a percentage of a verdict")
            return percent(x)
        case Cmp(left, op, right):
            a = evaluate(left, table)
            b = evaluate(right, table)
            if isinstance(a, bool) or isinstance(b, bool):
                return Indeterminate("type_mismatch", "cannot compare a verdict")
            return compare(a, op, b)
    raise AssertionError(f"unreachable: {ground!r}")  # pragma: no cover — parse is total


def _missing(col: str, table: Table) -> Indeterminate:
    return Indeterminate(
        "missing_column", f"no column {col!r}; the table has {sorted(table.columns)}"
    )


def _sum(col: str, table: Table) -> Value:
    if col not in table.columns:
        return _missing(col, table)
    if table.columns[col] != "number":
        return Indeterminate(
            "type_mismatch",
            f"column {col!r} is {table.columns[col]}, and only a number column sums",
        )
    total = Decimal(0)
    for index, row in enumerate(table.rows, start=1):
        raw = row.get(col)
        if raw is None:
            continue
        try:
            total += Decimal(str(raw))
        except InvalidOperation:
            return Indeterminate(
                "type_mismatch", f"row {index} of {col!r} holds {raw!r}, which is not a number"
            )
    return Quantity(total, table.units.get(col, ""))


# ---------------------------------------------------------------- canonical


def to_tree(ground: Ground) -> object:
    match ground:
        case Lit(magnitude, unit):
            return {"lit": str(magnitude), "unit": unit} if unit else {"lit": str(magnitude)}
        case Count(None):
            return {"count": "*"}
        case Count(col):
            return {"count": col}
        case CountWhere(col, eq):
            return {"count_where": {"col": col, "eq": eq}}
        case Sum(col):
            return {"sum": col}
        case Binary(op, left, right):
            return {op: [to_tree(left), to_tree(right)]}
        case Percent(inner):
            return {"percent": to_tree(inner)}
        case Cmp(left, op, right):
            return {"cmp": [to_tree(left), op, to_tree(right)]}
    raise AssertionError(f"unreachable: {ground!r}")  # pragma: no cover


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(ground: Ground, table: Table) -> str:
    """The ground's identity: a hash of the canonical tree and the canonical table."""
    payload = canonical_json({"ground": to_tree(ground), "table": table.canonical()})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "VOCABULARY",
    "Binary",
    "Cmp",
    "Count",
    "CountWhere",
    "Ground",
    "Lit",
    "Percent",
    "Sum",
    "canonical_json",
    "evaluate",
    "fingerprint",
    "parse",
    "to_tree",
]
