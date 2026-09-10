---
type: Plan
phase: 12-derivation
---

# Phase 12 — plan

```
# Sequential: Group 0 → 1 → 2. Each is one of the three claims.
```

## Group 0 — the value model, exact and honest

- `Quantity(magnitude: Decimal, unit: str)` under a pinned context, scale 12, half-even (D26)
- `Indeterminate(reason, detail)` — the typed nothing; `Value = Quantity | Indeterminate`
- `add`, `sub`, `mul`, `div`, `percent`, `compare` — every one total
- RED as **property tests**: commutativity and identity for add and mul; `div` then `mul` returns
  within scale; unit mismatch on add is indeterminate; div by zero is indeterminate; indeterminate
  propagates through every op; `percent` of a dimensionless ratio carries `%`; the worked example
  3 of 1842 is exactly `0.162866449511%`

**Commit:** `feat(adapters): quantities that are exact, carry their unit, and can be indeterminate`

## Group 1 — the table, the ground, and the engine

- `Table(columns, rows)` with typed columns: `number`, `text`, `bool`
- The ground: a closed JSON tree — `col`, `lit`, `count`, `count_where`, `sum`, `add`, `sub`,
  `mul`, `div`, `percent`, `cmp`
- `evaluate(ground, table) -> Value | Verdict`, structural, no loops
- `fingerprint(ground, table)` over canonical JSON
- RED: the worked example end to end; a missing column is indeterminate naming the column; a text
  column summed is indeterminate; an unknown node is refused at parse, not at evaluation; two fresh
  engines agree bit-for-bit; the fingerprint changes when the table changes and when the ground does

**Commit:** `feat(adapters): a ground anyone can re-execute bit-for-bit`

## Group 2 — the engine as a component

- `DerivationComponents`: one component, `derive`, effects empty (pure; no containment needed)
- It **proposes** `Proposal(kind="derivation", payload={value, unit, ground, fingerprint})` and
  returns the same as its observation
- RED: through a real run, the proposal reaches the sink with the ground beside the number
- records, board, status, roadmap

**Commit:** `feat(adapters): the derivation engine as a component that proposes its ground`
