---
type: Phase
status: in-progress
tags: [lease, token-ceiling, compaction, context-window]
---

# Phase 70 — the token ceiling

Releases **0.51.0**. Closes ENH-052, the audit's H33/H34.

## Why

A lease caps steps, seconds and cents. It does not cap tokens — so a product that budgets in tokens
cannot cap a run at all, and a long key-backed thread walks into the model's context window with
nothing to stop it. The failure today is a provider error at the window, which is a poor way to
learn where the limit was.

Phase 65 carried a transcript from turn to turn, which is what every chat interface does and what a
product expects, and recorded at the moment it was introduced that it grows without limit. This is
that debt.

## Scope

A token ceiling on the lease, enforced the way the cost ceiling already is — one predicate extended
rather than a second rule beside it — and compaction that fires on it, so a thread folds its own
history instead of failing at the window.

The meter already counts input, output and cache tokens and already knows when a provider's numbers
are unreliable. That last part decides the design: a ceiling enforced on unknown numbers would stop
runs for arithmetic nobody did.

## Not in scope

Per-fragment token counts or priorities, which is the rest of H33. What a provider charges.

## Acceptance

- A run over its token ceiling stops, with the same vocabulary a run out of money stops with.
- A ceiling is not enforced against numbers a provider did not give: unknown is unknown.
- `remaining()` reports the tokens left, and a carve cannot hand a child more than the parent holds.
- Compaction fires on the ceiling before the window does.
- Every assertion mutation-checked; full gate and exact-head CI green.
