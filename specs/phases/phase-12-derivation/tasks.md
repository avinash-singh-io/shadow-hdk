---
type: Tasks
phase: 12-derivation
---

# Phase 12 — tasks

## Group 0 — the value model
- [x] `Quantity`, `Indeterminate`, pinned context at scale 12 half-even (D26)
- [x] `add` `sub` `mul` `div` `percent` `compare`, all total
- [x] RED property tests: algebraic laws; mismatch, zero, propagation; the worked example
- [x] two of my own tests were wrong on first writing — a dimensioned 1 as the multiplicative
      identity, and a round-trip bound that ignored the second quantization — corrected with reasons
- [x] a survivor pinned D26's owned-context claim: the thread default is also half-even, so a test
      now poisons the thread's rounding and precision and asserts the engine did not notice
- [x] Gate

## Group 1 — table, ground, engine
- [x] `Table` with typed columns
- [x] the closed ground tree and its parser, refusing unknown nodes at parse
- [x] `evaluate`, structural and total
- [x] `fingerprint` over canonical JSON — **one canonicalizer**: a survivor showed the table
      pre-sorting its keys made the JSON sort unable to change anything (Phase 9's shape)
- [x] RED: worked example; missing column; wrong type; unknown node; bit-for-bit across engines
- [x] Gate

## Group 2 — the component
- [x] `DerivationComponents.derive`, effects empty
- [x] proposes the ground beside the number
- [x] RED: through a real run to the sink
- [x] records, board, status, roadmap
- [x] Gate
