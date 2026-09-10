---
type: History
phase: 12-derivation
---

# Phase 12 — history

Append only. Newest at the bottom.

### [DECISION] 2026-09-10 — D26: a ground is data, and the engine is its only interpreter
Topics: derivation, grounds, fixed-point, decimal, d26
Affects-phases: none
Affects-specs: specs/architecture/decisions.md, specs/architecture/adapters.md

A ground that is a callable, a string of Python, or a spreadsheet formula is executable; none is
re-executable by anyone else, and R8's whole point is that the story behind a number is checkable.
So a ground is a closed expression tree as JSON, and one deterministic engine evaluates it — the
same argument `09` §2 makes against free-form predicates and D23 makes against `when` clauses.

Three consequences, each a decision: no loops or user functions, so every ground terminates;
`Decimal` at scale 12 half-even under a context the engine owns, so two machines produce the same
digits; and a fingerprint over canonical JSON of tree plus typed rows as the ground's identity.

*Rejected:* floats with a tolerance (a tolerance confesses two runs disagree); `Fraction`
(exact, but unbounded denominators make a percentage of a percentage unreadable); a formula string
(a grammar is the thing nobody else re-implements bit-for-bit).

---
