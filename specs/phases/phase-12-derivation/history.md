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

### [ARCH_CHANGE] 2026-09-10 — the engine, in three groups
Topics: derivation, grounds, fixed-point, component, r8
Affects-phases: none
Affects-specs: specs/architecture/adapters.md

`adapters/derivation`: a value model at scale 12 half-even under an owned context; a closed ten-node
ground tree with a parser that refuses at the door; a structural, total evaluator; a fingerprint over
one canonical form; and `DerivationComponents.derive`, whose observation and whose proposal are the
same claim — value, unit, denominator, ground, fingerprint. R8's worked example runs end to end,
answers true against its limit, and answers indeterminate over an empty table.

### [DISCOVERY] 2026-09-10 — three survivors, three different lessons
Topics: mutation-check, tests, design
Affects-phases: none
Affects-specs: none

**Owned context.** Quantizing under the host thread's context survived because the default happens
to be half-even too. A claim about independence from the environment is only tested by varying the
environment, so the test now poisons the thread and asserts nothing changed.

**One canonicalizer.** The table pre-sorted its own keys and the ground is rebuilt structurally, so
`sort_keys` in the JSON step could never change an outcome — Phase 9's shape, two layers doing one
job so neither can be tested. Now one layer, pinned by a row written in another key order.

**Two tests were wrong before any mutation ran.** A dimensioned 1 is not a multiplicative identity,
and a divide-then-multiply round trip has two quantizations, not one. The bound *is* the precision
claim, so the arithmetic is in the test.

### [NOTE] 2026-09-10 — three edits failed on targets that had moved
Topics: process
Affects-phases: none
Affects-specs: none

Two commits failed on a missing message file (`/tmp` not persisting; a write placed after a
conditional exit), and one test edit silently did nothing because ruff had rewrapped its target
and the write sat after the failing assert. The message is now written unconditionally at the top
of the committing call, and edits to a test replace whole functions by their `def` boundaries.

---
