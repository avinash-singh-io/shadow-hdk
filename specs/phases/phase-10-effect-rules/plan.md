---
type: Plan
phase: 10-effect-rules
---

# Phase 10 — plan

```
# Sequential: Group 0 → 1 → 2. Each is one of the three claims, and each has its own gate.
```

## Group 0 — rows that compose

- `Rule`: a name, a ceiling, an ask line, and `applies_to` (empty means always) — D23
- `RuleSet`: several rules; `under(selection)` intersects every applicable row
- `RuleGovernance`: a `GovernancePort` over a rule set, whose refusal **names the rule**
- RED: N rows intersect and the result narrows every one; a selection naming nothing falls to the
  always-rules; an unknown name is refused rather than ignored; the refusal names the rule

**Commit:** `feat(adapters): a rule is a row, and rows intersect`

## Group 1 — the check, as a library

- `widens(theirs, ours)` → the rows and fields where a set is wider than what it was given
- RED: an equal set passes; a narrower set passes; a set wider in **each of the six fields**
  separately is caught, and the message names the field and the rule
- RED: a set with a rule the constitution does not have is judged on its own merits, not waved
  through — a new row still has to narrow

**Commit:** `feat(adapters): a team rule that widens is refused before it runs`

## Group 2 — rules as files, and the record

- `load_rules(path)` — TOML, per D17
- A bad file refused by name: unknown key, missing ceiling, unknown effect field
- The loader runs the Group 1 check when given a constitution to check against
- RED: each of the above; and a shipped example a team can copy
- `[~]` anything that needs the owner, with the command that would settle it
- tasks, history, status, roadmap, board

**Commit:** `feat(adapters): rules a team writes, checked when they are read`
