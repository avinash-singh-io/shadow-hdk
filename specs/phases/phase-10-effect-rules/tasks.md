---
type: Tasks
phase: 10-effect-rules
---

# Phase 10 — tasks

## Group 0 — rows that compose

- [ ] `Rule` — name, ceiling, ask line, `applies_to` (D23)
- [ ] `RuleSet.under(selection)` — every applicable row, intersected
- [ ] `RuleGovernance`, whose refusal names the rule
- [ ] RED: N rows intersect and the result narrows every one
- [ ] RED: a selection naming nothing still gets the always-rules
- [ ] RED: a name no rule claims is refused, not ignored
- [ ] RED: the refusal names the rule
- [ ] Gate

## Group 1 — the check, as a library

- [ ] `widens(theirs, ours)` → where a set is wider than what it was given
- [ ] RED: equal passes; narrower passes
- [ ] RED: wider in **each of the six fields** separately, each caught and named
- [ ] RED: a rule the constitution does not have still has to narrow
- [ ] Gate

## Group 2 — rules as files, and the record

- [ ] `load_rules(path)` — TOML (D17)
- [ ] a bad file refused by name: unknown key, missing ceiling, unknown effect field
- [ ] the loader runs the check when given something to check against
- [ ] RED: each of the above
- [ ] a shipped example a team can copy
- [ ] records, board, status, roadmap
- [ ] Gate
