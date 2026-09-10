---
type: Tasks
phase: 10-effect-rules
---

# Phase 10 — tasks

## Group 0 — rows that compose

- [x] `Rule` — name, ceiling, ask line, `applies_to` (D23)
- [x] `RuleSet.under(selection)` — every applicable row, intersected
- [x] `RuleGovernance`, whose refusal names the rule
- [x] RED: N rows intersect and the result narrows every one
- [x] RED: a selection naming nothing still gets the always-rules
- [x] RED: a name no rule claims is refused, not ignored
- [x] **a real bug found by mutation**: governance over an empty rule set *allowed* a step —
      the refusal logic looked for a row to blame, found none, and let it through. Fail-closed
      was open at N=0. Fixed: the composed ceiling is checked first, and a set granting nothing
      refuses and says so
- [x] RED: the refusal names the rule
- [x] Gate

## Group 1 — the check, as a library

- [x] `widens(theirs, ours)` → where a set is wider than what it was given
- [x] RED: equal passes; narrower passes
- [x] RED: wider in **each of the six fields** separately, each caught and named
- [x] a guard that fails the moment the kernel grows a seventh field the check has not caught
      up with, and a second proving each named field is actually compared
- [x] RED: a rule the constitution does not have still has to narrow
- [x] Gate

## Group 2 — rules as files, and the record

- [x] `load_rules(path)` — TOML (D17)
- [x] a bad file refused by name: unknown key, missing ceiling, unknown effect field
- [x] the loader runs the check when given something to check against
- [x] RED: each of the above
- [x] a shipped example a team can copy
- [x] records, board, status, roadmap
- [x] Gate
