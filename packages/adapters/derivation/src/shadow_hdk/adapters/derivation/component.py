"""The derivation engine as a component (`09` §5: *a derivation engine is a component*).

Reached the way anything else is — a step in a composition, judged by governance, observed on the
record. What it hands back is not a number but a **claim**: the value, its unit, the denominator it
was made over, the ground that produced it, and the fingerprint that is that ground's identity. The
same claim goes to the sink as a proposal, because a number nobody can re-derive is not a fact the
record should hold, and `08` §C6 says a claim without a ground that resolves is refused.

*No containment needed.* A pure function over data reads, writes and reaches nothing, so its effect
profile is the narrowest there is and a mode that allows nothing else still lets it run.

A malformed ground or table is the author's error (D7): a `Failed` the model can read, and **no
proposal** — a claim that could not be parsed is not a claim.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import JsonValue

from shadow_hdk.adapters.derivation.ground import evaluate, fingerprint, parse, to_tree
from shadow_hdk.adapters.derivation.table import Table
from shadow_hdk.adapters.derivation.values import Indeterminate, Quantity
from shadow_hdk.kernel.components import (
    Component,
    Interface,
    Provenance,
    Registration,
    RegistrationId,
)
from shadow_hdk.kernel.effects import EffectProfile
from shadow_hdk.kernel.observations import Completed, Failed, Observation, Proposal
from shadow_hdk.kernel.ports import ComponentPort

DERIVE = "derive"


class DerivationComponents(ComponentPort):
    def __init__(self, *, registered_by: str = "host", at: str = "") -> None:
        self._registered_by = registered_by
        self._at = at

    async def registrations(self) -> Sequence[Registration]:
        return [
            Registration(
                id=DERIVE,
                component=Component(
                    interface=Interface(
                        name=DERIVE,
                        description=(
                            "Evaluate a ground over a typed table and return the claim it "
                            "produces: the value, its unit, the ground, and its fingerprint. "
                            "Anyone can re-run the ground and get the same digits."
                        ),
                        input_schema={
                            "type": "object",
                            "properties": {
                                "table": {
                                    "type": "object",
                                    "description": "columns, units, row_unit, rows",
                                },
                                "ground": {"type": "object", "description": "the expression tree"},
                            },
                            "required": ["table", "ground"],
                        },
                        output_schema={"type": "object"},
                    ),
                    # Pure. Reads nothing, writes nothing, reaches nowhere, costs nothing.
                    effects=EffectProfile(),
                    provenance=Provenance(
                        registered_by=self._registered_by, adapter="derivation", at=self._at
                    ),
                    labels=frozenset({"derivation"}),
                ),
            )
        ]

    async def invoke(self, registration: RegistrationId, inputs: JsonValue) -> Observation:
        if registration != DERIVE:
            return Failed(f"no component registered as {registration!r}")
        arguments = inputs if isinstance(inputs, dict) else {}
        try:
            table = _table_from(arguments.get("table"))
            ground = parse(arguments.get("ground"))
        except (ValueError, TypeError, KeyError) as bad:
            return Failed(f"the derivation could not be read: {bad}")
        claim = _claim(evaluate(ground, table), ground, table)

        from shadow_hdk.runtime import current_run

        context = current_run()
        if context is not None:
            await context.propose(
                Proposal(
                    kind="derivation",
                    payload=claim,
                    provenance=Provenance(
                        registered_by=context.run_id, adapter="derivation", at=context.now()
                    ),
                )
            )
        return Completed(claim)


def _table_from(raw: Any) -> Table:
    if not isinstance(raw, dict):
        raise ValueError("a table is an object with columns, units, row_unit and rows")
    columns = raw.get("columns")
    if not isinstance(columns, dict):
        raise ValueError("a table needs 'columns': a mapping of name to type")
    rows = raw.get("rows", [])
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("a table's 'rows' is a list of objects")
    units = raw.get("units", {})
    if not isinstance(units, dict):
        raise ValueError("a table's 'units' is a mapping of column to unit")
    return Table(
        columns=dict(columns),
        units=dict(units),
        row_unit=str(raw.get("row_unit", "row")),
        rows=[dict(row) for row in rows],
    )


def _claim(
    result: Quantity | bool | Indeterminate, ground: Any, table: Table
) -> dict[str, JsonValue]:
    """The value and everything needed to re-derive it. Strings for magnitudes, so no float ever
    enters the record on the way out either."""
    base: dict[str, JsonValue] = {
        "ground": to_tree(ground),  # type: ignore[dict-item]
        "fingerprint": fingerprint(ground, table),
    }
    if isinstance(result, Indeterminate):
        return {
            **base,
            "value": None,
            "unit": None,
            "of": None,
            "indeterminate": {"reason": result.reason, "detail": result.detail},
        }
    if isinstance(result, bool):
        return {**base, "value": result, "unit": "", "of": None, "indeterminate": None}
    return {
        **base,
        "value": str(result.magnitude),
        "unit": result.unit,
        "of": (
            {"value": str(result.of.magnitude), "unit": result.of.unit}
            if result.of is not None
            else None
        ),
        "indeterminate": None,
    }


__all__ = ["DERIVE", "DerivationComponents"]
