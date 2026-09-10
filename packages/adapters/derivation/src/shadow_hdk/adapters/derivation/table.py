"""Typed data a ground is evaluated over.

A table declares what each column *is* — `number`, `text` or `bool` — and what unit a number
column carries, and what one row counts as. Evaluation checks those declarations rather than
guessing from the values, so a text column summed is a type mismatch that names the column, not a
crash halfway down the rows.

Cells are strings on the way in, always. A number cell is parsed as a `Decimal` at evaluation, so
a float never enters, and a cell that cannot be parsed names its row in the indeterminate.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

ColumnType = Literal["number", "text", "bool"]
COLUMN_TYPES: frozenset[str] = frozenset({"number", "text", "bool"})


@dataclass(frozen=True)
class Table:
    columns: Mapping[str, ColumnType]
    """Column name → declared type."""
    units: Mapping[str, str] = field(default_factory=dict)
    """Number column name → unit. A number column with no entry is dimensionless."""
    row_unit: str = "row"
    """What one row counts as — *unit*, *sample*, *lot* — so a count carries a unit too."""
    rows: Sequence[Mapping[str, str | bool]] = ()

    def __post_init__(self) -> None:
        bad = {name: kind for name, kind in self.columns.items() if kind not in COLUMN_TYPES}
        if bad:
            raise ValueError(
                f"unknown column type(s) {bad}; a column is one of {sorted(COLUMN_TYPES)}"
            )
        stray = set(self.units) - set(self.columns)
        if stray:
            raise ValueError(f"units for columns that do not exist: {sorted(stray)}")

    def canonical(self) -> dict[str, object]:
        """The table as plain data. **Not** sorted here: key order is `canonical_json`'s job, and
        one canonicalizer is one place for a mutation to bite. A second sort in this method
        survived every test, because it made the JSON step's sort unable to change anything."""
        return {
            "columns": dict(self.columns),
            "units": dict(self.units),
            "row_unit": self.row_unit,
            "rows": [dict(row) for row in self.rows],
        }


__all__ = ["COLUMN_TYPES", "ColumnType", "Table"]
