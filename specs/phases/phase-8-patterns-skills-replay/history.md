---
type: History
phase: 8-patterns-skills-replay
---

# Phase 8 — history

Append only. Newest at the bottom.

### [DECISION] 2026-09-10 — D17: patterns and skills are TOML, and the check happens before the first turn
Topics: patterns, skills, toml, d17, loader, modes
Affects-phases: phase-9
Affects-specs: specs/architecture/adapters.md, specs/architecture/decisions.md

**TOML**, for two reasons rather than taste. A role file is multi-line prose, which JSON cannot hold
without escaping it into unreadability; and `tomllib` has been in the standard library since 3.11,
so the format costs no dependency. YAML would cost one and buy ambiguity — a version string that
parses as a float is not a hypothetical.

The second half matters more. `10` §306 says a skill declares its components *so skill and mode can
be checked against each other*. The check is the point, so it happens **before the first turn**,
against `RunContext.visible()`. A skill needing a component the deployment's mode forbids is refused
with the names of what is missing, rather than discovered three steps in when a tool call fails.

That is the same move as `visible()`: what the policy would refuse is **absent**, not greyed out
(`09` §4). A skill is simply the first thing that can say what it wants in advance.

*Rejected:* checking lazily, when the skill first calls a tool. It costs a model turn to learn what
a file could have said, and the failure arrives mid-work rather than as a refusal to start.

*Rejected:* a Python entry point per pattern. It makes the framework's patterns a different kind of
thing from a team's, which is exactly what `09` §5 says they must not be.

*Overturned by:* a pattern needing to compute something — a role varying with the deployment. That
would mean patterns want a template language, and the honest answer is then a template in the file
rather than a callable behind it.

---
