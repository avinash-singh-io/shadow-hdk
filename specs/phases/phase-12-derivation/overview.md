---
type: Phase
phase: 12
name: derivation
epic: 0006-derivation
status: not-started
topics: [derivation, grounds, fixed-point, decimal, units, indeterminate, total, d26, r8]
deps: [phase-11-contained-sandboxes]
---

# Phase 12 — Derivation

## Goal

`09` §5, verbatim: **a derivation — a component that evaluates a total, non-looping expression over
typed data and returns a value whose ground can be re-executed bit-for-bit; no containment needed.**

R8 says what that is for: *hold numbers as claims with units and denominators*, and *a comparison
that can answer indeterminate*. The worked example is *"3 of 1842 units, 0.16% against a 0.05%
limit"* — a claim whose ground the verification harness recomputes from the file. And `08` §C6:
*a Claim without a Ground that resolves is refused.*

Three claims, each testable on its own:

| | claim |
|---|---|
| exact | 0.16% is exact, and a percentage of a percentage does not drift — **fixed-point**, never float |
| honest | a value carries its **unit and its denominator**, because a bare number is not a claim |
| total | every expression has a defined result; division by zero, a missing column, a unit mismatch each yield a typed **indeterminate** rather than raising |

## D26 — a ground is data, and the engine is its only interpreter

The tempting design is a ground that is a Python callable, or a string of Python, or a formula in
some spreadsheet dialect. Each is *executable*; none is **re-executable by anyone else**. A ground
somebody in another language, on another machine, three years later, cannot recompute is a number
with a story attached, and R8's whole point is that the story is checkable.

So a ground is a **closed expression tree, as JSON**, and one deterministic engine is the only
thing that evaluates it. The same argument `09` §2 makes against a free-form predicate in the effect
vocabulary — it turns a proof into a linter — and D23 makes against a `when` clause on a rule: a
thing that can be *compared* or *re-run* must be data with a fixed meaning, not code with an
environment.

Three consequences that are each a design decision:

1. **No loops, no recursion, no user functions.** The tree is finite and evaluation is structural,
   so every ground terminates. That is what *total* buys, and it is why the language is small.
2. **Decimal, at a fixed scale, under a pinned context.** Floats cannot represent 0.16 and their
   rounding depends on the host. `Decimal` is exact for every operation but division, and division
   is quantized to **twelve fractional digits, half-even**, under a context the engine owns rather
   than the thread's default — so two machines produce the same digits. Twelve because the worked
   examples are parts-per-hundred over counts in the thousands, and twelve places is six orders past
   anything a person would read; a deployment that needs more says so on its engine, not per ground.
3. **A fingerprint is the ground's identity.** Canonical JSON of the tree plus the table's typed
   rows, hashed. Two grounds with the same fingerprint are the same claim; a ground whose
   fingerprint does not match the number beside it is a claim that does not resolve.

*Rejected:* floats with a tolerance — a tolerance is a confession that two runs disagree.
*Rejected:* `fractions.Fraction` — exact, but denominators grow without bound and a percentage of a
percentage of a percentage becomes unreadable and slow; fixed-point at a stated scale is the honest
compromise and says its precision out loud.
*Rejected:* a formula string — the moment it needs a parser it has a grammar, and the grammar is the
thing nobody else can re-implement bit-for-bit.

*Overturned by:* a deployment that needs a unit system richer than a name — dimensional analysis
with prefixes and conversions. That is a real library and a real dependency, and it would be a
decision about what the engine imports, not about what a ground is.

## Exit criteria

- Adding, multiplying and dividing quantities obeys the algebraic laws fixed-point can obey, as
  **property tests** — a test that checks one value does not check the arithmetic
- A unit mismatch, a division by zero, a missing column and a type mismatch each produce a typed
  `Indeterminate`, and an indeterminate propagates through anything built on it
- A comparison can answer true, false or indeterminate
- Evaluating the same ground over the same table in two fresh engines produces the same digits and
  the same fingerprint, bit-for-bit
- The engine is a component whose output is a `Proposal` carrying the ground beside the number
